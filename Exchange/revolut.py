# Exchange/revolut.py
import logging
import time
import base64
from pathlib import Path
from typing import Any, List

import httpx
from cryptography.hazmat.primitives import serialization

logger = logging.getLogger(__name__)


async def request(
    url: str,
    method: str = "GET",
    api_key: str = "",
    private_key_path: str = "",
    timeout: float = 20.0,
) -> httpx.Response:
    """Общая функция для подписанных запросов к Revolut X API"""
    # Извлекаем endpoint для подписи
    endpoint = "/" + "/".join(url.split("/")[3:]) if len(url.split("/")) > 3 else url

    timestamp = int(time.time() * 1000)
    message_to_sign = f"{timestamp}{method}{endpoint}"

    # Загрузка и подпись приватным ключом
    pem_data = Path(private_key_path).read_text(encoding="utf-8")
    private_key = serialization.load_pem_private_key(
        pem_data.encode("utf-8"), password=None
    )

    signature_bytes = private_key.sign(message_to_sign.encode("utf-8"))
    signature = base64.b64encode(signature_bytes).decode("utf-8")

    headers = {
        "Accept": "application/json",
        "X-Revx-API-Key": api_key,
        "X-Revx-Timestamp": str(timestamp),
        "X-Revx-Signature": signature,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        return await client.request(method, url, headers=headers)


async def get_symbols(config: dict) -> List[dict]:
    """
    Получает список торговых символов с Revolut.
    Подготавливает запрос → вызывает request() → обрабатывает ответ.
    """
    api = config.get("api", {}).get("revolut", {})

    api_key = api.get("api_key")
    base_url = api.get("base_url", "https://revx.revolut.com/api/")
    endpoint = api.get("currencies_endpoint", "/1.0/configuration/currencies")
    private_key_path = api.get("private_key_path")

    if not api_key:
        raise ValueError("Revolut: api_key не указан в конфиге")
    if not private_key_path:
        raise ValueError("Revolut: private_key_path не указан в конфиге")

    # Подготовка пути к ключу
    key_path = Path(private_key_path).expanduser().resolve()
    if not key_path.exists():
        raise FileNotFoundError(f"Private key not found: {key_path}")

    # Формируем полный URL
    url = f"{base_url.rstrip('/')}{endpoint if endpoint.startswith('/') else '/' + endpoint}"

    try:
        logger.info(f"Запрос символов к Revolut: {url}")

        response = await request(
            url=url,
            method="GET",
            api_key=api_key,
            private_key_path=str(key_path),
        )

        response.raise_for_status()
        data: Any = response.json()
        
        return data

    except httpx.HTTPStatusError as e:
        logger.error(f"Revolut API вернул ошибку {e.response.status_code}: {e.response.text[:400]}")
        raise
    except Exception:
        logger.exception("Ошибка при получении символов от Revolut")
        raise



async def get_pairs(config: dict) -> List[str]:
    """
    Получает список торговых пар с Revolut (BTC/USDT, ETH/EUR и т.д.)
    """
    api = config.get("api", {}).get("revolut", {})

    api_key = api.get("api_key")
    base_url = api.get("base_url", "https://revx.revolut.com/api/")
    private_key_path = api.get("private_key_path")

    if not api_key:
        raise ValueError("Revolut: api_key не указан в конфиге")
    if not private_key_path:
        raise ValueError("Revolut: private_key_path не указан в конфиге")

    # Формируем URL для пар
    url = f"{base_url.rstrip('/')}/1.0/configuration/pairs"

    try:
        logger.info(f"Запрос торговых пар к Revolut: {url}")

        response = await request(
            url=url,
            method="GET",
            api_key=api_key,
            private_key_path=private_key_path,
        )

        response.raise_for_status()
        data: Any = response.json()
        
        #logger.info(f"data 5 strings: {str(data)[:500]}")  # Логируем первые 500 символов ответа для отладки

        return data

    except Exception:
        logger.exception("Ошибка при получении торговых пар от Revolut")
        raise


