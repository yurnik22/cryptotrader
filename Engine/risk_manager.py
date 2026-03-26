"""Pre-trade validation: liquidity, sizing, drawdown, daily loss, circuit breaker."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from Engine.models import Action, BotContext, Decision, MarketSnapshot
from Engine.risk_limits import RiskLimits

logger = logging.getLogger("cryptotrader.risk")


@dataclass
class _BotRiskState:
    peak_equity: Decimal = Decimal("0")
    session_date: date | None = None
    session_start_equity: Decimal = Decimal("0")
    reject_streak: int = 0
    circuit_open_until_cycle: int | None = None


class RiskManager:
    """Stateful per-bot risk: peak / session equity, drawdown, streaks, circuit breaker."""

    def __init__(self, limits: RiskLimits) -> None:
        self._limits = limits
        self._by_bot: dict[int, _BotRiskState] = {}

    def note_mark_equity(self, bot_id: int, equity: Decimal, cycle_index: int) -> None:
        """Call once per bot per cycle before `validate` (mark-to-market equity)."""
        st = self._by_bot.setdefault(bot_id, _BotRiskState())
        today = datetime.now(UTC).date()
        if st.session_date != today:
            st.session_date = today
            st.session_start_equity = equity
        if equity > st.peak_equity:
            st.peak_equity = equity
        if st.circuit_open_until_cycle is not None and cycle_index >= st.circuit_open_until_cycle:
            logger.info(
                "risk_circuit_cleared",
                extra={"structured": {"bot_id": bot_id, "cycle": cycle_index}},
            )
            st.circuit_open_until_cycle = None
            st.reject_streak = 0

    def validate(
        self,
        decision: Decision,
        context: BotContext,
        snapshot: MarketSnapshot,
        *,
        mark_equity: Decimal,
        cycle_index: int,
    ) -> Decision:
        if decision.action == Action.HOLD:
            return decision

        st = self._by_bot.setdefault(context.bot_id, _BotRiskState())
        sym = decision.currency.upper()

        if st.circuit_open_until_cycle is not None and cycle_index < st.circuit_open_until_cycle:
            logger.info(
                "risk_reject_circuit_breaker",
                extra={
                    "structured": {"bot_id": context.bot_id, "until": st.circuit_open_until_cycle}
                },
            )
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))

        quote = snapshot.quotes.get(sym)
        if quote is None:
            logger.info(
                "risk_reject_missing_quote",
                extra={"structured": {"bot_id": context.bot_id, "symbol": sym}},
            )
            return self._reject(decision, sym, context.bot_id, cycle_index, st)

        if decision.amount <= 0:
            return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))

        # Drawdown vs peak (blocks new BUY exposure)
        if (
            decision.action == Action.BUY
            and st.peak_equity > 0
            and mark_equity < st.peak_equity * (Decimal("1") - self._limits.max_drawdown_fraction)
        ):
            logger.info(
                "risk_reject_max_drawdown",
                extra={
                    "structured": {
                        "bot_id": context.bot_id,
                        "equity": str(mark_equity),
                        "peak": str(st.peak_equity),
                    }
                },
            )
            return self._reject(decision, sym, context.bot_id, cycle_index, st)

        # Daily loss vs session-start equity
        if st.session_start_equity > 0 and decision.action == Action.BUY:
            floor = st.session_start_equity * (
                Decimal("1") - self._limits.daily_loss_limit_fraction
            )
            if mark_equity < floor:
                logger.info(
                    "risk_reject_daily_loss_limit",
                    extra={
                        "structured": {
                            "bot_id": context.bot_id,
                            "equity": str(mark_equity),
                            "floor": str(floor),
                        }
                    },
                )
                return self._reject(decision, sym, context.bot_id, cycle_index, st)

        if decision.action == Action.BUY:
            notional = (decision.amount * quote.price).quantize(Decimal("0.00000001"))
            usd = context.balances.get("USD", Decimal("0"))
            if usd < notional:
                logger.info(
                    "risk_reject_insufficient_usd",
                    extra={
                        "structured": {
                            "bot_id": context.bot_id,
                            "need": str(notional),
                            "have": str(usd),
                        }
                    },
                )
                return self._reject(decision, sym, context.bot_id, cycle_index, st)
            if notional < self._limits.min_order_usd:
                return self._reject(decision, sym, context.bot_id, cycle_index, st)

            current_sym_notional = Decimal("0")
            pos = next((p for p in context.positions if p.symbol == sym), None)
            if pos is not None:
                current_sym_notional = (pos.quantity * quote.price).quantize(Decimal("0.00000001"))
            projected = current_sym_notional + notional
            max_allowed = (mark_equity * self._limits.max_position_notional_fraction).quantize(
                Decimal("0.00000001")
            )
            if mark_equity > 0 and projected > max_allowed:
                logger.info(
                    "risk_reject_position_limit",
                    extra={
                        "structured": {
                            "bot_id": context.bot_id,
                            "symbol": sym,
                            "projected": str(projected),
                            "max": str(max_allowed),
                        }
                    },
                )
                return self._reject(decision, sym, context.bot_id, cycle_index, st)

        if decision.action == Action.SELL:
            pos = next((p for p in context.positions if p.symbol == sym), None)
            if pos is None or pos.quantity < decision.amount:
                logger.info(
                    "risk_reject_insufficient_position",
                    extra={
                        "structured": {
                            "bot_id": context.bot_id,
                            "symbol": sym,
                            "want": str(decision.amount),
                            "have": str(pos.quantity if pos else Decimal("0")),
                        }
                    },
                )
                return self._reject(decision, sym, context.bot_id, cycle_index, st)
            if (decision.amount * quote.price) < self._limits.min_order_usd:
                return self._reject(decision, sym, context.bot_id, cycle_index, st)

        st.reject_streak = 0
        return decision

    def _reject(
        self,
        decision: Decision,
        sym: str,
        bot_id: int,
        cycle_index: int,
        st: _BotRiskState,
    ) -> Decision:
        if decision.action in (Action.BUY, Action.SELL) and decision.amount > 0:
            st.reject_streak += 1
            if st.reject_streak >= self._limits.circuit_breaker_reject_streak:
                until = cycle_index + self._limits.circuit_breaker_pause_cycles
                st.circuit_open_until_cycle = until
                logger.warning(
                    "risk_circuit_breaker_tripped",
                    extra={
                        "structured": {
                            "bot_id": bot_id,
                            "streak": st.reject_streak,
                            "open_until_cycle": until,
                        }
                    },
                )
                st.reject_streak = 0
        return Decision(action=Action.HOLD, currency=sym, amount=Decimal("0"))
