# Database/portfolio.py
from Database.db import session_scope
#from Database.models import Portfolio  # модель портфеля пользователя

async def get_portfolio_for_user(user_id: int, session_factory):

    """
    MOCK function — возвращает тестовый портфель для пользователя
    """
    # Пример тестовых данных
    return [
        {"symbol": "BTC", "amount": 0.5},
        {"symbol": "ETH", "amount": 2.0},
        {"symbol": "USDT", "amount": 1000},
    ]


    """async with session_scope(session_factory) as session:
        result = await session.execute(
            "SELECT * FROM portfolio WHERE user_id = :uid", {"uid": user_id}
        )
        # Преобразуем в список словарей
        return [dict(row._mapping) for row in result.fetchall()]
        """