import os
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.models import User, Report
from app.repositories.repositories import ReportRepository
from app.middleware.auth import RoleChecker, get_current_user
from app.schemas.schemas import ReportResponse
from app.utils.async_runner import trigger_background_job
from app.services.tasks import generate_pdf_report_task
from app.utils.report_generator import ReportGenerator
from typing import List

router = APIRouter(prefix="/reports", tags=["Reports"])

# RBAC dependencies
require_auditor = RoleChecker(["Admin", "Auditor"])

@router.post("", response_model=ReportResponse, status_code=status.HTTP_202_ACCEPTED)
def create_report(
    title: str,
    format_type: str = "PDF",  # PDF, CSV, JSON
    background_tasks: BackgroundTasks = None,
    current_user: User = Depends(require_auditor),
    db: Session = Depends(get_db)
):
    format_type = format_type.upper()
    if format_type not in ["PDF", "CSV", "JSON"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported report format. Supported: PDF, CSV, JSON"
        )
        
    report = ReportRepository.create(db, {
        "title": title,
        "type": format_type,
        "status": "Pending",
        "created_by": current_user.id
    })
    
    # Trigger generation
    if format_type == "PDF":
        trigger_background_job(background_tasks, generate_pdf_report_task, report.id)
    else:
        # For CSV and JSON, generate synchronously as they are extremely lightweight
        from app.config.config import settings
        file_ext = format_type.lower()
        file_name = f"compliance_report_{report.id}.{file_ext}"
        file_path = os.path.join(settings.UPLOAD_DIR, "reports", file_name)
        
        if format_type == "CSV":
            ReportGenerator.generate_csv_report(db, file_path)
        else:
            ReportGenerator.generate_json_report(db, file_path)
            
        summary_str = f"Exported {format_type} report successfully."
        ReportRepository.update_status(db, report.id, "Completed", file_path=file_path, summary=summary_str)
        
    # Re-fetch
    report = ReportRepository.get_by_id(db, report.id)
    return report

@router.get("", response_model=List[ReportResponse])
def list_reports(db: Session = Depends(get_db)):
    return ReportRepository.list(db)

@router.get("/{report_id}", response_model=ReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    report = ReportRepository.get_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    return report

@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)):
    report = ReportRepository.get_by_id(db, report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
        
    if report.status != "Completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Report generation is not complete. Current status: {report.status}"
        )
        
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report file not found on disk."
        )
        
    filename = os.path.basename(report.file_path)
    # Return file response
    return FileResponse(
        path=report.file_path,
        filename=filename,
        media_type="application/octet-stream"
    )
