"""
ZeroTrace Application Configuration
"""

from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
REPO_DIR = BASE_DIR.parent

ENV_FILES = [
    str(BASE_DIR / ".env"),
    str(REPO_DIR / ".env"),
    ".env"
]


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    SUPABASE_URL: str = "https://placeholder.supabase.co"
    SUPABASE_KEY: str = "placeholder-key"
    SUPABASE_SERVICE_KEY: str = "placeholder-service-key"

    SIGNING_PRIVATE_KEY_PEM: str = ""
    SIGNING_PUBLIC_KEY_PEM: str = ""

    SUPABASE_STORAGE_BUCKET: str = "certificates"
    SIGNING_KEY_ID: str = "zerotrace-authoritative-p256-v1"
    POLICY_VERSION: str = "1.0.0"

    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    def get_private_key_pem(self) -> str:
        return self.SIGNING_PRIVATE_KEY_PEM.replace("\\n", "\n").strip('"')

    def get_public_key_pem(self) -> str:
        return self.SIGNING_PUBLIC_KEY_PEM.replace("\\n", "\n").strip('"')


settings = Settings()
