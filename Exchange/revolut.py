# Exchange/revolut.py
import base64
import logging
import time
from datetime import datetime, timezone
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

    client_timestamp_ms = int(time.time() * 1000)
    client_timestamp_sec = client_timestamp_ms / 1000
    message_to_sign = f"{client_timestamp_ms}{method}{endpoint}"

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
        "X-Revx-Timestamp": str(client_timestamp_ms),
        "X-Revx-Signature": signature,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.request(method, url, headers=headers)
        
        # Логирование времени при ошибке 409 Conflict
        if response.status_code == 409:
            client_dt = datetime.fromtimestamp(client_timestamp_sec, tz=timezone.utc)
            server_date_str = response.headers.get("date", "N/A")
            
            try:
                # Парсим дату из заголовка Date (обычно в RFC 2822 формате)
                from email.utils import parsedate_to_datetime
                server_dt = parsedate_to_datetime(server_date_str)
                time_diff_sec = (client_dt - server_dt.replace(tzinfo=timezone.utc)).total_seconds()
                
                logger.warning(
                    f"409 Conflict detected - Time desynchronization check:\n"
                    f"  Client time: {client_dt.isoformat()} UTC\n"
                    f"  Server time: {server_dt.isoformat()}\n"
                    f"  Difference: {time_diff_sec:.1f} seconds (client ahead if positive)\n"
                    f"  Request timestamp sent: {client_timestamp_ms} ms"
                )
            except Exception as e:
                logger.warning(
                    f"409 Conflict detected - Could not parse server time:\n"
                    f"  Client time: {client_dt.isoformat()} UTC\n"
                    f"  Server Date header: {server_date_str}\n"
                    f"  Parse error: {e}"
                )
        
        return response


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


async def get_tickers(config: dict) -> dict:
    """Получает актуальные тикеры с Revolut."""
    api = config.get("api", {}).get("revolut", {})

    api_key = api.get("api_key")
    base_url = api.get("base_url", "https://revx.revolut.com/api/")
    private_key_path = api.get("private_key_path")

    if not api_key:
        raise ValueError("Revolut: api_key не указан в конфиге")
    if not private_key_path:
        raise ValueError("Revolut: private_key_path не указан в конфиге")

    url = f"{base_url.rstrip('/')}/1.0/tickers"

    try:
        logger.info(f"Запрос тикеров к Revolut: {url}")

        response = await request(
            url=url,
            method="GET",
            api_key=api_key,
            private_key_path=private_key_path,
        )

        response.raise_for_status()
        data: Any = response.json()
        return _extract_tickers(data)

    except httpx.HTTPStatusError as e:
        logger.error(f"Revolut API вернул ошибку {e.response.status_code}: {e.response.text[:400]}")
        raise
    except Exception:
        logger.exception("Ошибка при получении тикеров от Revolut")
        raise


async def get_balances(config: dict) -> list[dict]:
    """Получает балансы аккаунта с Revolut X."""
    api = config.get("api", {}).get("revolut", {})

    api_key = api.get("api_key")
    base_url = api.get("base_url", "https://revx.revolut.com/api/")
    private_key_path = api.get("private_key_path")
    balances_endpoint = api.get("balances_endpoint", "/1.0/balances")

    if not api_key:
        raise ValueError("Revolut: api_key не указан в конфиге")
    if not private_key_path:
        raise ValueError("Revolut: private_key_path не указан в конфиге")

    url = f"{base_url.rstrip('/')}{balances_endpoint if balances_endpoint.startswith('/') else '/' + balances_endpoint}"

    try:
        logger.info(f"Запрос балансов к Revolut: {url}")
        response = await request(
            url=url,
            method="GET",
            api_key=api_key,
            private_key_path=private_key_path,
        )
        response.raise_for_status()
        data: Any = response.json()
        return data if isinstance(data, list) else []
    except httpx.HTTPStatusError as e:
        logger.error(f"Revolut API вернул ошибку {e.response.status_code}: {e.response.text[:400]}")
        raise
    except Exception:
        logger.exception("Ошибка при получении балансов от Revolut")
        raise


def _extract_tickers(payload: Any) -> dict:
    """Нормализует ответ по тикерам к формату для сохранения в БД."""
    rows = payload.get("data", []) if isinstance(payload, dict) else []
    metadata = payload.get("metadata", {}) if isinstance(payload, dict) else {}
    raw_timestamp = metadata.get("timestamp")

    if raw_timestamp:
        snapshot_at = datetime.fromtimestamp(raw_timestamp / 1000, tz=timezone.utc).replace(tzinfo=None)
    else:
        snapshot_at = datetime.utcnow()

    tickers = []
    for item in rows:
        if not isinstance(item, dict) or not item.get("symbol"):
            continue

        tickers.append(
            {
                "symbol": str(item.get("symbol")),
                "bid": str(item.get("bid", "0")),
                "ask": str(item.get("ask", "0")),
                "mid": str(item.get("mid", "0")),
                "last_price": str(item.get("last_price", "0")),
            }
        )

    return {"data": tickers, "timestamp": snapshot_at}




