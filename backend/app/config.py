"""Configuración por variables de entorno. Nunca hardcodear secretos.

Los valores por defecto apuntan a un Supabase LOCAL (supabase start). Para conectar
un proyecto de desarrollo remoto, setear DATABASE_URL en un `.env` NO versionado
(ver .env.example). Las claves privilegiadas sólo viven en el backend.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- Base de datos (Supabase Postgres) ---
    # Default: puerto de Postgres de `supabase start` (local).
    database_url: str = "postgresql://postgres:postgres@127.0.0.1:54322/postgres"
    app_env: str = "local"

    # Empresa por defecto del simulador (Empresa A sintética del seed).
    demo_default_tenant: str = "0000000a-0000-0000-0000-00000000000a"

    # --- LLM (intercambiable). Sin api key => modo mock explícito. ---
    llm_provider: str = "mock"           # "mock" | "openai"
    llm_model: str = "gpt-6-luna"
    llm_api_key: str | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_timeout_s: float = 20.0
    llm_max_output_tokens: int = 500

    @property
    def llm_is_live(self) -> bool:
        return self.llm_provider == "openai" and bool(self.llm_api_key)


settings = Settings()
