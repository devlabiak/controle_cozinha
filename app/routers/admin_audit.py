from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models import AuditLog
from app.auth import get_current_admin

router = APIRouter(prefix="/api/admin", tags=["Admin - Auditoria"])

class AuditLogResponse(BaseModel):
    id: int
    user_id: Optional[int]
    tenant_id: Optional[int]
    action: str
    resource: str
    resource_id: Optional[int]
    details: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

@router.get("/audit-logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    tenant_id: Optional[int] = None,
    action: Optional[str] = None,
    resource: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """Lista logs de auditoria (apenas admin SaaS)"""
    query = db.query(AuditLog)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if tenant_id:
        query = query.filter(AuditLog.tenant_id == tenant_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource:
        query = query.filter(AuditLog.resource == resource)
    
    logs = query.order_by(desc(AuditLog.timestamp)).offset(skip).limit(limit).all()
    return logs