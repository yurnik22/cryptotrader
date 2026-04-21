# config.py
from pathlib import Path
import yaml
import os
import logging
from datetime import datetime
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

    return config


def setup_logging(config: dict) -> None:
    """
    Настраивает логирование: вывод в консоль + запись в файл Logs/дд-мм-гггг.log
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

    # Добавляем файловый handler
    file_handler = logging.FileHandler(log_filename, encoding="utf-8", mode="a")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(logging.Formatter(log_format, date_format))

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
    logging.info(f"Лог-файл: {log_filename}")