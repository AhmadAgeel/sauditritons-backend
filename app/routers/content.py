from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(prefix="/content", tags=["Public Content"])


@router.get("/announcements", response_model=list[schemas.AnnouncementResponse])
def announcements(db: Session = Depends(get_db)):
    return db.scalars(select(models.Announcement).where(models.Announcement.is_published).order_by(models.Announcement.is_pinned.desc(), models.Announcement.created_at.desc())).all()


@router.get("/resources", response_model=list[schemas.ResourceResponse])
def resources(db: Session = Depends(get_db)):
    return db.scalars(select(models.Resource).where(models.Resource.is_published).order_by(models.Resource.featured.desc(), models.Resource.title)).all()


@router.get("/board", response_model=list[schemas.BoardMemberResponse])
def board(db: Session = Depends(get_db)):
    return db.scalars(select(models.BoardMember).where(models.BoardMember.is_published).order_by(models.BoardMember.sort_order, models.BoardMember.name)).all()
