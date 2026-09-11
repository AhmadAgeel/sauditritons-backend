import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, joinedload

from app import models, oauth2, schemas
from app.database import get_db
from app.redis import redis_client


router = APIRouter(prefix="/admin", tags=["Admin"])


def audit(db: Session, actor: models.User, action: str, target_type: str, target_id: object, details: dict | None = None):
    db.add(models.AdminAuditLog(actor_user_id=actor.id, action=action, target_type=target_type, target_id=str(target_id), details=details or {}))


def apply_updates(record, update):
    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(record, field, value)


def require_record(db: Session, model, record_id: int):
    record = db.get(model, record_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Record not found")
    return record


def validate_event_schedule(record: models.Event):
    if record.ends_at is not None and record.ends_at <= record.starts_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Event end time must be after its start time")
    if record.rsvp_opens_at is not None and record.rsvp_closes_at <= record.rsvp_opens_at:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="RSVP close time must be after its open time")


@router.get("/overview")
def overview(_: models.User = Depends(oauth2.get_current_staff), db: Session = Depends(get_db)):
    return {
        "events": db.scalar(select(func.count()).select_from(models.Event)),
        "members": db.scalar(select(func.count()).select_from(models.User)),
        "pending_profiles": db.scalar(select(func.count()).select_from(models.StudentProfile).where(~models.StudentProfile.is_approved)),
        "rsvps": (db.scalar(select(func.count()).select_from(models.EventRSVP)) or 0) + (db.scalar(select(func.count()).select_from(models.GuestEventRSVP)) or 0),
    }


@router.get("/events", response_model=list[schemas.EventResponse])
def list_events(_: models.User = Depends(oauth2.get_current_staff), db: Session = Depends(get_db)):
    return db.scalars(select(models.Event).order_by(models.Event.starts_at.desc())).all()


@router.post("/events", response_model=schemas.EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(payload: schemas.EventCreate, actor: models.User = Depends(oauth2.get_current_staff), db: Session = Depends(get_db)):
    record = models.Event(**payload.model_dump())
    validate_event_schedule(record)
    db.add(record)
    db.flush()
    audit(db, actor, "event.created", "event", record.id, {"title": record.title})
    db.commit(); db.refresh(record)
    return record


@router.patch("/events/{event_id}", response_model=schemas.EventResponse)
def update_event(event_id: int, payload: schemas.EventUpdate, actor: models.User = Depends(oauth2.get_current_staff), db: Session = Depends(get_db)):
    record = require_record(db, models.Event, event_id); apply_updates(record, payload)
    validate_event_schedule(record)
    audit(db, actor, "event.updated", "event", event_id, payload.model_dump(exclude_unset=True))
    db.commit(); db.refresh(record)
    return record


@router.delete("/events/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(event_id: int, actor: models.User = Depends(oauth2.get_current_staff), db: Session = Depends(get_db)):
    record = require_record(db, models.Event, event_id)
    ticket_codes = list(db.scalars(select(models.EventRSVP.ticket_code).where(models.EventRSVP.event_id == event_id)).all())
    ticket_codes.extend(db.scalars(select(models.GuestEventRSVP.ticket_code).where(models.GuestEventRSVP.event_id == event_id)).all())
    if ticket_codes:
        db.execute(delete(models.EventCheckIn).where(models.EventCheckIn.ticket_code.in_(ticket_codes)))
    audit(db, actor, "event.deleted", "event", event_id, {"title": record.title}); db.delete(record); db.commit()


@router.get("/events/{event_id}/rsvps", response_model=list[schemas.AdminRsvpResponse])
def event_rsvps(event_id: int, _: models.User = Depends(oauth2.get_current_officer), db: Session = Depends(get_db)):
    require_record(db, models.Event, event_id)
    member_rows = db.scalars(select(models.EventRSVP).options(joinedload(models.EventRSVP.user), joinedload(models.EventRSVP.check_in)).where(models.EventRSVP.event_id == event_id)).all()
    guest_rows = db.scalars(select(models.GuestEventRSVP).options(joinedload(models.GuestEventRSVP.check_in)).where(models.GuestEventRSVP.event_id == event_id)).all()
    return [schemas.AdminRsvpResponse(ticket_code=row.ticket_code, attendee_name=f"{row.user.first_name} {row.user.last_name}", attendee_email=row.user.email, companion_count=0, has_paid=row.has_paid, checked_in_at=row.check_in.checked_in_at if row.check_in else None, created_at=row.created_at) for row in member_rows] + [schemas.AdminRsvpResponse(ticket_code=row.ticket_code, attendee_name=row.attendee_name, attendee_email=row.attendee_email, companion_count=len(row.companion_names), has_paid=row.has_paid, checked_in_at=row.check_in.checked_in_at if row.check_in else None, created_at=row.created_at) for row in guest_rows]


def event_registration(db: Session, event_id: int, ticket_code: str):
    normalized = ticket_code.replace("-", "").upper()
    registration = db.scalar(select(models.EventRSVP).where(models.EventRSVP.ticket_code == normalized))
    if registration is None:
        registration = db.get(models.GuestEventRSVP, normalized)
    if registration is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")
    if registration.event_id != event_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ticket is not for this event")
    return normalized, registration


@router.post("/events/{event_id}/rsvps/{ticket_code}/check-in", response_model=schemas.EventCheckInResponse)
def check_in_rsvp(event_id: int, ticket_code: str, payload: schemas.AdminCheckInCreate, actor: models.User = Depends(oauth2.get_current_officer), db: Session = Depends(get_db)):
    normalized, registration = event_registration(db, event_id, ticket_code)
    if registration.check_in is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ticket already checked in")
    event = require_record(db, models.Event, event_id)
    if event.is_paid and not registration.has_paid and not payload.mark_paid:
        return {"status": "payment_required", "ticket_code": normalized, "has_paid": False}
    if payload.mark_paid:
        registration.has_paid = True
    scanner = db.get(models.WorkspaceUser, actor.id)
    display_name = f"{actor.first_name} {actor.last_name}".strip()
    if scanner is None:
        scanner = models.WorkspaceUser(workspace_user_id=actor.id, display_name=display_name)
        db.add(scanner)
    else:
        scanner.display_name = display_name
    check_in = models.EventCheckIn(ticket_code=normalized, workspace_user_id=actor.id, method="manual")
    db.add(check_in)
    audit(db, actor, "rsvp.checked_in", "ticket", normalized, {"event_id": event_id, "marked_paid": payload.mark_paid})
    db.commit(); db.refresh(check_in)
    redis_client.publish(f"ticket:{normalized}", json.dumps({"checked_in_at": check_in.checked_in_at.isoformat(), "scanned_by": display_name}))
    return {"status": "checked_in", "ticket_code": normalized, "has_paid": registration.has_paid}


@router.delete("/events/{event_id}/rsvps/{ticket_code}/check-in", status_code=status.HTTP_204_NO_CONTENT)
def undo_check_in(event_id: int, ticket_code: str, actor: models.User = Depends(oauth2.get_current_officer), db: Session = Depends(get_db)):
    normalized, registration = event_registration(db, event_id, ticket_code)
    check_in = registration.check_in
    if check_in is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check-in not found")
    db.delete(check_in)
    audit(db, actor, "rsvp.check_in_undone", "ticket", normalized, {"event_id": event_id})
    db.commit()


@router.get("/users", response_model=list[schemas.AdminUserResponse])
def users(_: models.User = Depends(oauth2.get_current_admin), db: Session = Depends(get_db)):
    return db.scalars(select(models.User).options(joinedload(models.User.student_profile)).order_by(models.User.created_at.desc())).unique().all()


@router.patch("/users/{user_id}/role", response_model=schemas.UserResponse)
def update_role(user_id: int, payload: schemas.UserRoleUpdate, actor: models.User = Depends(oauth2.get_current_admin), db: Session = Depends(get_db)):
    user = require_record(db, models.User, user_id)
    if user.role == "admin" and payload.role != "admin":
        admins = db.scalar(select(func.count()).select_from(models.User).where(models.User.role == "admin")) or 0
        if admins <= 1:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="The last admin cannot be demoted")
    previous = user.role; user.role = payload.role
    audit(db, actor, "user.role_changed", "user", user_id, {"from": previous, "to": payload.role}); db.commit(); db.refresh(user)
    return user


@router.patch("/profiles/{user_id}", response_model=schemas.StudentProfileResponse)
def moderate_profile(user_id: int, payload: schemas.ProfileModerationUpdate, actor: models.User = Depends(oauth2.get_current_admin), db: Session = Depends(get_db)):
    profile = require_record(db, models.StudentProfile, user_id); apply_updates(profile, payload)
    audit(db, actor, "profile.moderated", "profile", user_id, payload.model_dump(exclude_unset=True)); db.commit(); db.refresh(profile)
    return profile


def content_routes(path, model, create_schema, update_schema, response_schema):
    @router.get(f"/{path}", response_model=list[response_schema])
    def list_records(_: models.User = Depends(oauth2.get_current_staff), db: Session = Depends(get_db)):
        return db.scalars(select(model).order_by(model.created_at.desc())).all()

    @router.post(f"/{path}", response_model=response_schema, status_code=status.HTTP_201_CREATED)
    def create_record(payload: create_schema, actor: models.User = Depends(oauth2.get_current_staff), db: Session = Depends(get_db)):
        record = model(**payload.model_dump()); db.add(record); db.flush()
        audit(db, actor, f"{path}.created", path, record.id); db.commit(); db.refresh(record); return record

    @router.patch(f"/{path}/{{record_id}}", response_model=response_schema)
    def update_record(record_id: int, payload: update_schema, actor: models.User = Depends(oauth2.get_current_staff), db: Session = Depends(get_db)):
        record = require_record(db, model, record_id); apply_updates(record, payload)
        audit(db, actor, f"{path}.updated", path, record_id, payload.model_dump(exclude_unset=True)); db.commit(); db.refresh(record); return record

    @router.delete(f"/{path}/{{record_id}}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_record(record_id: int, actor: models.User = Depends(oauth2.get_current_staff), db: Session = Depends(get_db)):
        record = require_record(db, model, record_id); audit(db, actor, f"{path}.deleted", path, record_id); db.delete(record); db.commit()


content_routes("announcements", models.Announcement, schemas.AnnouncementCreate, schemas.AnnouncementUpdate, schemas.AnnouncementResponse)
content_routes("resources", models.Resource, schemas.ResourceCreate, schemas.ResourceUpdate, schemas.ResourceResponse)
content_routes("board", models.BoardMember, schemas.BoardMemberCreate, schemas.BoardMemberUpdate, schemas.BoardMemberResponse)


@router.get("/audit", response_model=list[schemas.AuditLogResponse])
def audit_log(_: models.User = Depends(oauth2.get_current_admin), db: Session = Depends(get_db)):
    return db.scalars(select(models.AdminAuditLog).order_by(models.AdminAuditLog.created_at.desc()).limit(200)).all()
