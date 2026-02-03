from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import delete

from app.database import SessionLocal
from app.models import MovimentacaoEstoque

RETENTION_DAYS = 90


def cleanup_history(retention_days: Optional[int] = None) -> int:
    """Remove movimentações anteriores ao período de retenção e retorna o total deletado."""
    days = retention_days or RETENTION_DAYS
    cutoff = datetime.utcnow() - timedelta(days=days)
    session = SessionLocal()
    try:
        stmt = delete(MovimentacaoEstoque).where(MovimentacaoEstoque.created_at < cutoff)
        result = session.execute(stmt)
        session.commit()
        return result.rowcount or 0
    finally:
        session.close()
