from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/controle_cozinha"
    
    # Security
    SECRET_KEY: str = "sua-chave-secreta-super-segura-aqui"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Domain
    BASE_DOMAIN: str = "wlsolucoes.eti.br"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "https://painelfood.wlsolucoes.eti.br",
        "https://app.wlsolucoes.eti.br",
        "https://cozinha.wlsolucoes.eti.br",
    ]
    
    # Rate limiting
    RATE_LIMIT_LOGIN: str = "20/minute"
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"


settings = Settings()
