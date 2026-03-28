from __future__ import annotations
from abc import ABC, abstractmethod
from Engine.models import BotContext, Decision, MarketSnapshot
#from Engine.bot_manager import is_buying_allowed

class BaseBot(ABC):
    def __init__(self, *, bot_id: int, name: str) -> None:
        self.bot_id = bot_id
        self.name = name

    @abstractmethod
    async def decide(self, context: BotContext, snapshot: MarketSnapshot) -> Decision:
        """Возвращает следующее решение бота"""
    
    async def maybe_buy(self) -> bool:
        """
        Проверка глобального флага покупки.
        Возвращает False, если покупки на данный момент запрещены.
        """
        if not is_buying_allowed():
            print(f"{self.name}: Buying paused globally")
            return False
        return True