"""Utilitários para criação de logs de auditoria."""
from __future__ import annotations
from typing import Optional
from fastapi import Request
from sqlalchemy.orm import Session
from app.models import AuditLog


def registrar_auditoria(
    db: Session,
    *,
    user_id: Optional[int],
    tenant_id: Optional[int],
    action: str,
    resource: str,
    resource_id: Optional[int] = None,
    details: Optional[str] = None,
    request: Optional[Request] = None,
) -> AuditLog:
    """Registra um log de auditoria reutilizável em vários módulos."""
    audit = AuditLog(
        user_id=user_id,
        tenant_id=tenant_id,
        action=action,
        resource=resource,
        resource_id=resource_id,
        details=details,
        ip_address=request.client.host if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
    )
    db.add(audit)
    return audit
