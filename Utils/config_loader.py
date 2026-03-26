"""Load YAML config with `.env` support and environment variable overrides."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

logger = logging.getLogger("cryptotrader.config")


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        msg = "config root must be a mapping"
        raise ValueError(msg)
    return data


def resolve_config_path(project_root: Path) -> Path:
    """Resolve config file: env override, then `config.yaml`, then example file."""
    env_path = os.getenv("CRYPTOTRADER_CONFIG_PATH")
    if env_path:
        p = Path(env_path).expanduser()
        if not p.is_file():
            msg = f"CRYPTOTRADER_CONFIG_PATH does not exist: {p}"
            raise FileNotFoundError(msg)
        return p

    local = project_root / "config.yaml"
    if local.is_file():
        return local

    example = project_root / "config.yaml.example"
    if example.is_file():
        logger.warning(
            "using_config_example",
            extra={
                "structured": {
                    "path": str(example),
                    "hint": "Copy config.yaml.example to config.yaml for local overrides.",
                }
            },
        )
        return example

    msg = "No config.yaml or config.yaml.example found in project root."
    raise FileNotFoundError(msg)


def apply_env_overrides(cfg: dict[str, Any]) -> None:
    """Merge `CRYPTOTRADER_DB_*` and related env vars into the loaded mapping (in place)."""
    db = cfg.setdefault("database", {})
    if not isinstance(db, dict):
        return

    mapping = {
        "CRYPTOTRADER_DB_HOST": "host",
        "CRYPTOTRADER_DB_PORT": "port",
        "CRYPTOTRADER_DB_USER": "user",
        "CRYPTOTRADER_DB_PASSWORD": "password",
        "CRYPTOTRADER_DB_NAME": "name",
    }
    for env_key, yaml_key in mapping.items():
        val = os.getenv(env_key)
        if val is None or val == "":
            continue
        if yaml_key == "port":
            db[yaml_key] = int(val)
        else:
            db[yaml_key] = val

    ex = os.getenv("CRYPTOTRADER_EXCHANGE")
    if ex:
        cfg["exchange"] = ex.strip().lower()

    paper = os.getenv("CRYPTOTRADER_PAPER")
    if paper is not None:
        cfg["paper"] = paper.strip().lower() in ("1", "true", "yes", "on")


def load_app_config(project_root: Path | None = None) -> dict[str, Any]:
    """Load dotenv from project root, read YAML, apply env overrides."""
    root = project_root or Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")
    path = resolve_config_path(root)
    cfg = _read_yaml(path)
    apply_env_overrides(cfg)
    logger.info("config_loaded", extra={"structured": {"path": str(path)}})
    return cfg
