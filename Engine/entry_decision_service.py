class EntryDecisionService:
    """Простые правила входа для первой версии fake-trading."""

    def __init__(self, min_buy_score: float = 0.0):
        self.min_buy_score = min_buy_score

    def should_buy(self, ranking, free_usd: float, min_free_usd: float) -> bool:
        try:
            total_score = float(ranking.total_score)
            drawdown_score = float(ranking.drawdown_score)
            momentum_score = float(ranking.momentum_score)
        except (TypeError, ValueError):
            return False

        return (
            free_usd >= min_free_usd
            and total_score >= self.min_buy_score
            and drawdown_score > 0
            and momentum_score > 0
        )