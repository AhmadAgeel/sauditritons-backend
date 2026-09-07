from fastapi import APIRouter

from . import student_profile, event, workspace_user

router = APIRouter()

# router.include_router(student_profile.router)
router.include_router(event.router)
router.include_router(workspace_user.router)