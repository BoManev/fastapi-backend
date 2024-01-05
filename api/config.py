import os
from fastapi import Depends
from pydantic import Field
from typing import Annotated, Optional
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    PROJECT_NAME: str = f"SiteSync API [{os.getenv('ENV', 'dev').capitalize()}]"
    DESCRIPTION: str = "trash"
    VERSION: str = "0.1.0"

    ENV: str = Field(default=False)
    DEBUG: bool = Field(default=False)
    ROOT_PATH: str = Field(default=False)

    MOCK_DB: Optional[bool] = Field(default=False)

    JWT_SECRET: str
    JWT_ALGO: str
    JWT_TOKEN_EXPIRE_SECONDS: int

    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int
    POSTGRES_HOST: str

    API_PORT: int

    LOGGER_FILE: str = Field(default="logs/backend.log")
    DATE_FORMAT: str = Field(default="%d %b %Y | %H:%M:%S")
    LOGGER_FORMAT: str = Field(default="%(asctime)s | %(message)s")

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


# only used during startup, for routes use SessionConfig
@lru_cache()
def get_config():
    return Config()


SessionConfig = Annotated[Config, Depends(get_config)]
