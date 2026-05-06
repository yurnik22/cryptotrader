class ExitDecisionService:
    """Простые правила выхода для первой версии fake-trading."""

    def __init__(self, stop_loss_pct: float = 0.01):
        self.stop_loss_pct = stop_loss_pct

    def should_sell(self, *, pnl_pct: float, momentum_score: float) -> bool:
        return pnl_pct <= -self.stop_loss_pct or momentum_score < 0