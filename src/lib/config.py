import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    myride_username: Optional[str] = None
    myride_password: Optional[str] = None
    myride_refresh_token: Optional[str] = None
    myride_ignore_schedule: bool = False
    
    # Defaults discovered from HAR
    cognito_client_id: str = "3c5382gsq7g13djnejo98p2d98"
    cognito_domain: str = "login.myridek12.tylerapp.com"
    api_base_url: str = "https://myridek12.tylerapi.com"
    ws_base_url: str = "wss://myridek12.tylerapi.com"
    
    db_url: str = "sqlite+aiosqlite:///data/myride.db"
    log_level: str = "INFO"
    web_host: str = "0.0.0.0"
    web_port: int = 8080

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
