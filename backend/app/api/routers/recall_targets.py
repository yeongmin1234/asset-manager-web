"""Raw recall target upload and listing APIs."""

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.routers.recall_preview import _read_xlsx, require_recall_preview_access
from app.db.database import get_db
from app.models.recall_application import RecallApplication
from app.models.recall_target import RecallTarget
from app.models.user import User
from app.services.audit_log_service import record_audit_log
from app.services.recall_target_service import (
    commit_targets, list_target_batches, list_targets, preview_targets, target_summary,
)
from app.services.recall_target_matching import (
    channel_summary, manual_match, matching_summary, run_auto_matching, unmatch,
)


router = APIRouter(prefix="/online/recall/targets", tags=["online-recall-targets"])


class ManualMatchRequest(BaseModel):
    application_id: int


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
        record_audit_log(db, request, user, action_type="auto_match", menu_key="online_recall",
                         menu_name="온라인 TEAM > 리콜 관리", target_type="recall_target_upload_batch",
                         target_id=result["batch_id"], target_name="신규 리콜 대상 자동 매칭",
                         action_summary="신규 리콜 대상 자동 매칭: batch_id={} 결과={}".format(result["batch_id"], result["matching"]),
                         after_data={"batch_id": result["batch_id"], **result["matching"]})
        return result
    finally:
        await file.close()


@router.get("/summary")
def read_target_summary(_user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    return target_summary(db)


@router.get("/batches")
def read_target_batches(_user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    return jsonable_encoder(list_target_batches(db))


@router.get("/matching/summary")
def read_matching_summary(_user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    return matching_summary(db)


@router.get("/matching/channels")
def read_channel_summary(_user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    return channel_summary(db)


@router.post("/matching/run")
def rerun_matching(request: Request, user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    try:
        result = run_auto_matching(db, user_id=user.id)
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail="리콜 대상 매칭을 실행하지 못했습니다.") from exc
    record_audit_log(db, request, user, action_type="auto_match", menu_key="online_recall",
                     menu_name="온라인 TEAM > 리콜 관리", target_type="recall_targets",
                     target_id=None, target_name="기존 데이터 매칭 다시 실행",
                     action_summary="리콜 대상 매칭 다시 실행: 결과={} user_id={}".format(result, user.id), after_data=result)
    return result


@router.get("")
def read_targets(keyword: str = Query("", max_length=100), status: str = Query("", max_length=20),
                 match_status: str = Query("", max_length=20),
                 page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                 _user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    try:
        return jsonable_encoder(list_targets(db, keyword=keyword, status=status, match_status=match_status,
                                             page=page, page_size=page_size))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{target_id}")
def read_target_detail(target_id: int, _user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    target = db.scalar(select(RecallTarget).where(RecallTarget.id == target_id, RecallTarget.is_deleted.is_(False)))
    if target is None:
        raise HTTPException(status_code=404, detail="리콜 대상을 찾을 수 없습니다.")
    application = db.get(RecallApplication, target.matched_application_id) if target.matched_application_id else None
    return jsonable_encoder({"target": {column.name: getattr(target, column.name) for column in RecallTarget.__table__.columns},
                             "application": {"id": application.id, "application_date": application.application_date,
                                             "current_status": application.current_status} if application else None})


@router.post("/{target_id}/match")
def confirm_manual_match(target_id: int, payload: ManualMatchRequest, request: Request,
                         user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    try:
        result = manual_match(db, target_id=target_id, application_id=payload.application_id, user_id=user.id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail="수동 매칭을 확정하지 못했습니다.") from exc
    record_audit_log(db, request, user, action_type="update", menu_key="online_recall",
                     menu_name="온라인 TEAM > 리콜 관리", target_type="recall_target", target_id=target_id,
                     target_name="리콜 신청 수동 매칭", action_summary="수동 매칭: target_id={} application_id={} user_id={}".format(
                         target_id, payload.application_id, user.id), after_data=result)
    return result


@router.post("/{target_id}/unmatch")
def release_manual_match(target_id: int, request: Request,
                         user: User = Depends(require_recall_preview_access), db: Session = Depends(get_db)):
    try:
        result = unmatch(db, target_id=target_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit_log(db, request, user, action_type="update", menu_key="online_recall",
                     menu_name="온라인 TEAM > 리콜 관리", target_type="recall_target", target_id=target_id,
                     target_name="리콜 신청 매칭 해제", action_summary="매칭 해제: target_id={} application_id={} user_id={}".format(
                         target_id, result["application_id"], user.id), after_data=result)
    return result
