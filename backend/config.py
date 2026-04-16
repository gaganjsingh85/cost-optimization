"""Configuration management - loads from config.json or .env / environment variables."""

import json
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

CONFIG_FILE = Path(__file__).parent / "config.json"


class Config:
    def __init__(
        self,
        azure_tenant_id: Optional[str] = None,
        azure_client_id: Optional[str] = None,
        azure_client_secret: Optional[str] = None,
        azure_subscription_id: Optional[str] = None,
        m365_tenant_id: Optional[str] = None,
        m365_client_id: Optional[str] = None,
        m365_client_secret: Optional[str] = None,
        anthropic_api_key: Optional[str] = None,
    ):
        self.azure_tenant_id = azure_tenant_id
        self.azure_client_id = azure_client_id
        self.azure_client_secret = azure_client_secret
        self.azure_subscription_id = azure_subscription_id
        self.m365_tenant_id = m365_tenant_id
        self.m365_client_id = m365_client_id
        self.m365_client_secret = m365_client_secret
        self.anthropic_api_key = anthropic_api_key

    def has_azure_config(self) -> bool:
        return all([
            self.azure_tenant_id,
            self.azure_client_id,
            self.azure_client_secret,
            self.azure_subscription_id,
        ])

    def has_m365_config(self) -> bool:
        return all([self.m365_tenant_id, self.m365_client_id, self.m365_client_secret])

    def has_anthropic_config(self) -> bool:
        return bool(self.anthropic_api_key)

    def save_to_file(self) -> None:
        data = {
            "azure_tenant_id": self.azure_tenant_id,
            "azure_client_id": self.azure_client_id,
            "azure_client_secret": self.azure_client_secret,
            "azure_subscription_id": self.azure_subscription_id,
            "m365_tenant_id": self.m365_tenant_id,
            "m365_client_id": self.m365_client_id,
            "m365_client_secret": self.m365_client_secret,
            "anthropic_api_key": self.anthropic_api_key,
        }
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def to_dict(self) -> dict:
        return {
            "azure_tenant_id": self.azure_tenant_id,
            "azure_client_id": self.azure_client_id,
            "azure_client_secret": self.azure_client_secret,
            "azure_subscription_id": self.azure_subscription_id,
            "m365_tenant_id": self.m365_tenant_id,
            "m365_client_id": self.m365_client_id,
            "m365_client_secret": self.m365_client_secret,
            "anthropic_api_key": self.anthropic_api_key,
        }


def _load_from_file() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def _get(key: str, file_data: dict, env_key: str) -> Optional[str]:
    val = file_data.get(key)
    if val:
        return val
    return os.environ.get(env_key) or None


def load_config() -> Config:
    file_data = _load_from_file()
    return Config(
        azure_tenant_id=_get("azure_tenant_id", file_data, "AZURE_TENANT_ID"),
        azure_client_id=_get("azure_client_id", file_data, "AZURE_CLIENT_ID"),
        azure_client_secret=_get("azure_client_secret", file_data, "AZURE_CLIENT_SECRET"),
        azure_subscription_id=_get("azure_subscription_id", file_data, "AZURE_SUBSCRIPTION_ID"),
        m365_tenant_id=_get("m365_tenant_id", file_data, "M365_TENANT_ID"),
        m365_client_id=_get("m365_client_id", file_data, "M365_CLIENT_ID"),
        m365_client_secret=_get("m365_client_secret", file_data, "M365_CLIENT_SECRET"),
        anthropic_api_key=_get("anthropic_api_key", file_data, "ANTHROPIC_API_KEY"),
    )


def delete_config_file() -> bool:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
        return True
    return False