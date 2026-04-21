# Exchange/binance.py
import logging
from typing import List

logger = logging.getLogger(__name__)


async def get_symbols(config: dict) -> List[dict]:
    """Заглушка для Binance - получение символов"""
    logger.warning("Binance get_symbols не реализован")
    return []


async def get_pairs(config: dict) -> List[dict]:
    """Заглушка для Binance - получение пар"""
    logger.warning("Binance get_pairs не реализован")
    return [] 
