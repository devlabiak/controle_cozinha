from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Configuração robusta de pool para SaaS de alta demanda
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,              # Número base de conexões no pool
    max_overflow=40,           # Conexões extras permitidas em picos
    pool_pre_ping=True,        # Verifica conexões antes de usar (evita conexões mortas)
    pool_recycle=3600,         # Recicla conexões a cada hora (evita timeout do PG)
    echo_pool=False,           # Não logar eventos do pool (performance)
    connect_args={
        "connect_timeout": 10,          # Timeout de conexão: 10s
        "options": "-c statement_timeout=30000"  # Timeout de query: 30s
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency para injeção de sessão DB - usa automaticamente o pool configurado"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_pool_status():
    """Retorna status do pool de conexões para monitoramento"""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "max_overflow": engine.pool._max_overflow,
    }
