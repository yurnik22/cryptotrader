# Exchange/factory.py
from typing import Callable, Awaitable
import logging
import importlib

logger = logging.getLogger(__name__)


class ExchangeFactory:
    """Универсальная фабрика для бирж"""

    _modules = {}  # кэш загруженных модулей

    @classmethod
    def get_module(cls, provider: str):
        provider = provider.lower().strip()

        if provider in cls._modules:
            return cls._modules[provider]

        if provider in ["revolut", "revx"]:
            module_name = "Exchange.revolut"
        elif provider == "binance":
            module_name = "Exchange.binance"
        else:
            raise ValueError(f"Неподдерживаемый провайдер: {provider}")

        try:
            module = importlib.import_module(module_name)
            cls._modules[provider] = module
            logger.info(f"Загружен модуль биржи: {module_name}")
            return module
        except Exception as e:
            logger.error(f"Ошибка загрузки модуля {module_name}: {e}")
            raise

    @classmethod
    def get_function(cls, provider: str, func_name: str) -> Callable:
        """Возвращает нужную функцию из модуля биржи"""
        module = cls.get_module(provider)

        if not hasattr(module, func_name):
            raise AttributeError(f"Функция '{func_name}' не найдена в модуле биржи '{provider}'")

        func = getattr(module, func_name)
        logger.debug(f"Получена функция: {provider}.{func_name}()")
        return func


# ==================== Удобные обёртки ====================

def get_symbols_fetcher(provider: str) -> Callable[[dict], Awaitable[list[str]]]:
    """Возвращает функцию get_symbols для указанного провайдера"""
    return ExchangeFactory.get_function(provider, "get_symbols")


def get_pairs_fetcher(provider: str) -> Callable[[dict], Awaitable[list[str]]]:
    """Возвращает функцию get_pairs для указанного провайдера"""
    return ExchangeFactory.get_function(provider, "get_pairs")


def get_tickers_fetcher(provider: str):
    """Пример для будущих функций"""
    return ExchangeFactory.get_function(provider, "get_tickers")


# Универсальная функция (если понадобится)
def get_exchange_function(provider: str, func_name: str) -> Callable:
    """Универсальный доступ к любой функции биржи"""
    return ExchangeFactory.get_function(provider, func_name)