from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, contains_eager, joinedload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select

from app import models, schemas, oauth2
from app.database import get_db


router = APIRouter(
    prefix="/student-profiles",
    tags=["Student Profiles"],
)


@router.get("/", response_model=list[schemas.StudentProfileResponse])
def get_student_profiles(db: Session = Depends(get_db)):
    stmt = (
        select(models.StudentProfile)
        .join(models.StudentProfile.user)
        .options(contains_eager(models.StudentProfile.user))
        .where(
            models.StudentProfile.is_approved,
            models.StudentProfile.is_visible,
        )
        .order_by(models.User.activity_recency_at.desc())
    )
    return db.scalars(stmt).all()


@router.post("/", response_model=schemas.StudentProfileResponse, status_code=status.HTTP_201_CREATED)
def create_student_profile(
    profile: schemas.StudentProfileCreate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    new_profile = models.StudentProfile(
        user_id=current_user.id,
        **profile.model_dump(),
    )

    db.add(new_profile)
    try:
      db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student profile already exists",
        )
    db.refresh(new_profile)
    return new_profile


@router.get("/me", response_model=schemas.StudentProfileResponse)
def get_my_student_profile(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    stmt = (
        select(models.StudentProfile)
        .options(joinedload(models.StudentProfile.user))
        .where(models.StudentProfile.user_id == current_user.id)
    )

    profile = db.scalars(stmt).one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )

    return profile

@router.patch("/me", response_model=schemas.StudentProfileResponse)
def update_my_student_profile(
    updates: schemas.StudentProfileUpdate,
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(models.StudentProfile, current_user.id)

    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_student_profile(
    current_user: models.User = Depends(oauth2.get_current_user),
    db: Session = Depends(get_db),
):
    profile = db.get(models.StudentProfile, current_user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student profile not found",
        )
    db.delete(profile)
    db.commit()


