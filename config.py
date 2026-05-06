# config.py
from pathlib import Path
import yaml
import os
import logging
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from typing import Any


def load_config() -> dict[str, Any]:
    """
    Загружает cfg.yaml и дополняет переменными окружения
    """
    config_path = Path("cfg.yaml")

    if not config_path.exists():
        raise FileNotFoundError(f"Файл cfg.yaml не найден: {config_path.absolute()}")

    with open(config_path, encoding="utf-8") as f:
        config: dict = yaml.safe_load(f) or {}

    # Дополняем из переменных окружения
    api_section = config.setdefault("api", {})
    api_section["provider"] = os.getenv("API_PROVIDER") or api_section.get("provider", "revolut")

    # Revolut
    revolut = api_section.setdefault("revolut", {})
    revolut["api_key"] = os.getenv("REVOLUT_API_KEY") or revolut.get("api_key")
    revolut["private_key_path"] = os.getenv("REVOLUT_PRIVATE_KEY_PATH") or revolut.get("private_key_path")
    revolut["private_key_passphrase"] = os.getenv("REVOLUT_PRIVATE_KEY_PASSPHRASE") or revolut.get("private_key_passphrase", "")
    revolut["balances_endpoint"] = revolut.get("balances_endpoint", "/1.0/balances")

    # Database
    db = config.setdefault("database", {})
    if "url" not in db or not db.get("url"):
        db["url"] = (
            f"mysql+aiomysql://"
            f"{db.get('user', 'cryptotrader')}:"
            f"{db.get('password', 'cryptotrader')}@"
            f"{db.get('host', 'localhost')}:"
            f"{db.get('port', 3306)}/"
            f"{db.get('name', 'cryptotrader')}"
            f"?charset=utf8mb4"
        )

    trading = config.setdefault("trading", {})
    trading.setdefault("enabled", True)
    trading.setdefault("stop_loss_pct", 0.01)
    trading.setdefault("min_buy_score", 0.0)
    trading.setdefault("min_free_usd", 1.0)
    trading.setdefault("position_size_usd", 10.0)
    trading.setdefault("loop_interval_seconds", 30)

    return config


def setup_logging(config: dict) -> None:
    """
    Настраивает логирование: вывод в консоль + запись в файл Logs/дд-мм-гггг.log
    Автоматически создаёт новый файл логов каждый день в полночь
    """
    log_level_str = config.get("logging", {}).get("level", "INFO")
    log_level = getattr(logging, log_level_str.upper(), logging.INFO)

    # Создаём папку для логов
    log_dir = Path("Logs")
    log_dir.mkdir(exist_ok=True)

    # Имя файла лога — текущая дата
    today = datetime.now().strftime("%d-%m-%Y")
    log_filename = log_dir / f"{today}.log"

    # Формат логов
    log_format = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    date_format = "%H:%M:%S"

    # Настраиваем корневой логгер
    logging.basicConfig(
        level=log_level,
        format=log_format,
        datefmt=date_format,
        handlers=[]  # очищаем старые handlers, если были
    )

    # Добавляем TimedRotatingFileHandler (автоматически меняет файл в полночь)
    # midnight - ротация в полночь, interval=1 - каждый день
    file_handler = TimedRotatingFileHandler(
        filename=log_filename,
        when="midnight",
        interval=1,
        encoding="utf-8",
        backupCount=30  # хранить последние 30 дней логов
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))
    
    # Установим правильное имя файла при ротации (дд-мм-гггг.log)
    def namer(default_name):
        # default_name = "Logs/07-05-2026.log.2026-05-07" (YYYY-MM-DD)
        # Нам нужно: "Logs/07-05-2026.log"
        import re
        # Извлекаем дату в формате YYYY-MM-DD из конца
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})$', default_name)
        if match:
            year, month, day = match.groups()
            new_date = f"{day}-{month}-{year}"
            base_path = str(log_filename).replace(today, "")  # "Logs/"
            return f"{base_path}{new_date}.log"
        return default_name
    
    file_handler.namer = namer

    # Добавляем handler
    root_logger = logging.getLogger()
    # Убираем старые handlers, чтобы не дублировались
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    root_logger.addHandler(file_handler)

    # Добавляем консольный вывод (StreamHandler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)

    logging.info(f"Логирование настроено. Уровень: {log_level_str}")
    logging.info(f"Лог-файл: {log_filename} (авторотация в полночь)")