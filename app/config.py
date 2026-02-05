from pydantic_settings import BaseSettings
from typing import List, Optional
import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ==================== BANCO DE DADOS ====================
    DATABASE_URL: str
    
    # ==================== SEGURANÇA - OBRIGATÓRIAS ====================
    # SECRET_KEY é obrigatória e não pode ser a padrão
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    
    # ==================== AUTENTICAÇÃO ====================
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # ==================== DOMÍNIO ====================
    BASE_DOMAIN: str
    
    # ==================== CORS ====================
    ALLOWED_ORIGINS: str = "https://painelfood.wlsolucoes.eti.br,https://cozinha.wlsolucoes.eti.br,https://admin.wlsolucoes.eti.br"
    
    # ==================== COOKIES ====================
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "strict"
    
    # ==================== RATE LIMITING ====================
    RATE_LIMIT_LOGIN: str = "20/minute"
    
    # ==================== LOGGING ====================
    LOG_LEVEL: str = "INFO"
    
    # ==================== REDIS ====================
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # ==================== DADOS ADICIONAIS ====================
    ENABLE_HTTPS_REDIRECT: bool = True
    HISTORY_RETENTION_DAYS: int = 90
    
    class Config:
        env_file = ".env"
        case_sensitive = True
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Converte string de origens para lista"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self.ALLOWED_ORIGINS
    
    def validate_settings(self):
        """Valida configurações críticas de segurança"""
        errors = []
        
        # 1. Verificar se SECRET_KEY está presente
        if not self.SECRET_KEY:
            errors.append("❌ SECRET_KEY não está definida em .env")
        
        # 2. Verificar se SECRET_KEY é a padrão (segurança)
        default_keys = [
            "sua-chave-secreta-super-segura-aqui",
            "change-me",
            "secret",
            "key",
        ]
        
        if any(self.SECRET_KEY.lower() == key.lower() for key in default_keys):
            errors.append("❌ SECRET_KEY está usando valor padrão! Gere uma nova com: python -c \"import secrets; print(secrets.token_urlsafe(64))\"")
        
        # 3. Verificar se DATABASE_URL está presente
        if not self.DATABASE_URL or "postgresql://" not in self.DATABASE_URL:
            errors.append("❌ DATABASE_URL inválida ou não definida")
        
        # 4. Verificar comprimento da SECRET_KEY
        if len(self.SECRET_KEY) < 32:
            errors.append("⚠️  SECRET_KEY muito curta (recomendado: 64+ caracteres)")
        
        # 5. Avisar se em modo desenvolvimento (COOKIE_SECURE=false)
        if not self.COOKIE_SECURE:
            logger.warning("⚠️  COOKIE_SECURE=false - Modo DESENVOLVIMENTO apenas!")
        
        # 6. Avisar se HTTPS redirect desativado
        if not self.ENABLE_HTTPS_REDIRECT:
            logger.warning("⚠️  ENABLE_HTTPS_REDIRECT=false - Use apenas em desenvolvimento!")
        
        if errors:
            for error in errors:
                logger.error(error)
            raise ValueError("\n".join(errors))
        
        logger.info("✅ Todas as configurações de segurança validadas com sucesso")


# Carregar configurações
def load_settings() -> Settings:
    """Carrega e valida as configurações"""
    # Verificar se .env existe
    env_file = Path(".env")
    if not env_file.exists():
        raise FileNotFoundError(
            "❌ Arquivo .env não encontrado!\n"
            "   Execute: cp .env.example .env\n"
            "   E edite o arquivo .env com suas variáveis"
        )
    
    # Carregar settings
    settings = Settings()
    
    # Validar settings
    settings.validate_settings()
    
    return settings


# Instância global
try:
    settings = load_settings()
except (FileNotFoundError, ValueError) as e:
    logger.error(str(e))
    raise
