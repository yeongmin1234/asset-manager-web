"""Raw recall target upload and listing APIs."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routers.recall_preview import _read_xlsx, require_recall_preview_access
from app.db.database import get_db
from app.models.user import User
from app.services.audit_log_service import record_audit_log
from app.services.recall_target_service import (
    commit_targets, list_target_batches, list_targets, preview_targets, target_summary,
)


router = APIRouter(prefix="/online/recall/targets", tags=["online-recall-targets"])


@router.post("/preview")
async def preview_target_excel(request: Request, file: UploadFile = File(...),
                               user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    try:
        content = await _read_xlsx(file)
        try:
            result = preview_targets(db, content)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        counts = result["summary"]
        record_audit_log(db, request, user, action_type="preview", menu_key="online_recall",
                         menu_name="온라인 TEAM > 리콜 관리", target_type="recall_target_upload",
                         target_id=None, target_name="리콜 대상 Excel 미리보기",
                         action_summary="리콜 대상 Excel 미리보기: 전체 {}건 중복 {}건 확인 필요 {}건 제외 {}건".format(
                             counts["total_rows"], counts["duplicate"], counts["review"], counts["excluded"]),
                         after_data={key: counts[key] for key in counts})
        return jsonable_encoder(result)
    finally:
        await file.close()


@router.post("/commit")
async def commit_target_excel(request: Request, file: UploadFile = File(...),
                              user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    try:
        content = await _read_xlsx(file)
        try:
            result = commit_targets(db, content, file.filename or "recall-targets.xlsx", user.id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except SQLAlchemyError as exc:
            raise HTTPException(status_code=500, detail="리콜 대상을 등록하지 못했습니다.") from exc
        record_audit_log(db, request, user, action_type="excel_import", menu_key="online_recall",
                         menu_name="온라인 TEAM > 리콜 관리", target_type="recall_target_upload_batch",
                         target_id=result["batch_id"], target_name="리콜 대상 Excel 등록",
                         action_summary="리콜 대상 Excel 등록: batch_id={} 전체 {}건 정상 {}건 중복 {}건 확인 필요 {}건 제외 {}건".format(
                             result["batch_id"], result["total"], result["normal"], result["duplicate"], result["review"], result["excluded"]),
                         after_data=result)
        return result
    finally:
        await file.close()


@router.get("/summary")
def read_target_summary(_user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    return target_summary(db)


@router.get("/batches")
def read_target_batches(_user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    return jsonable_encoder(list_target_batches(db))


@router.get("")
def read_targets(keyword: str = Query("", max_length=100), status: str = Query("", max_length=20),
                 page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                 _user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    try:
        return jsonable_encoder(list_targets(db, keyword=keyword, status=status, page=page, page_size=page_size))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
