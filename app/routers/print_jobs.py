from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import PrintJob, StatusPrintJob, User
from app.schemas import PrintJobResponse
from app.auth import get_current_user
from app.middleware import get_tenant_id

router = APIRouter(prefix="/api/print-jobs", tags=["Print Jobs - Fila de Impressão"])


@router.get("/pending", response_model=List[PrintJobResponse])
def get_pending_print_jobs(
    request: Request,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retorna jobs de impressão pendentes.
    Usado pelo app desktop para polling.
    """
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    jobs = db.query(PrintJob).filter(
        PrintJob.tenant_id == tenant_id,
        PrintJob.status == StatusPrintJob.PENDING
    ).order_by(PrintJob.created_at).limit(limit).all()
    
    return jobs


@router.get("/", response_model=List[PrintJobResponse])
def list_print_jobs(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lista todos os jobs de impressão (histórico)"""
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    query = db.query(PrintJob).filter(PrintJob.tenant_id == tenant_id)
    
    if status_filter:
        try:
            status_enum = StatusPrintJob(status_filter)
            query = query.filter(PrintJob.status == status_enum)
        except ValueError:
            pass
    
    jobs = query.order_by(PrintJob.created_at.desc()).offset(skip).limit(limit).all()
    
    return jobs


@router.patch("/{job_id}/printing")
def mark_job_printing(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marca job como 'printing' (em impressão).
    Usado pelo app desktop ao iniciar impressão.
    """
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    job = db.query(PrintJob).filter(
        PrintJob.id == job_id,
        PrintJob.tenant_id == tenant_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )
    
    job.status = StatusPrintJob.PRINTING
    job.printed_at = datetime.now()
    job.tentativas += 1
    
    db.commit()
    
    return {"message": "Job marcado como em impressão"}


@router.patch("/{job_id}/completed")
def mark_job_completed(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marca job como concluído.
    Usado pelo app desktop após impressão bem-sucedida.
    """
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    job = db.query(PrintJob).filter(
        PrintJob.id == job_id,
        PrintJob.tenant_id == tenant_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )
    
    job.status = StatusPrintJob.COMPLETED
    job.completed_at = datetime.now()
    
    db.commit()
    
    return {"message": "Job concluído com sucesso"}


@router.patch("/{job_id}/failed")
def mark_job_failed(
    job_id: int,
    error_message: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Marca job como falho.
    Usado pelo app desktop em caso de erro.
    """
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    job = db.query(PrintJob).filter(
        PrintJob.id == job_id,
        PrintJob.tenant_id == tenant_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )
    
    job.status = StatusPrintJob.FAILED
    job.erro_mensagem = error_message
    
    # Se tentou menos de 3 vezes, volta para pending
    if job.tentativas < 3:
        job.status = StatusPrintJob.PENDING
    
    db.commit()
    
    return {"message": "Job marcado como falho", "will_retry": job.tentativas < 3}


@router.get("/{job_id}", response_model=PrintJobResponse)
def get_print_job(
    job_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtém detalhes de um job específico"""
    tenant_id = get_tenant_id(request)
    
    if current_user.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")
    
    job = db.query(PrintJob).filter(
        PrintJob.id == job_id,
        PrintJob.tenant_id == tenant_id
    ).first()
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job não encontrado"
        )
    
    return job
