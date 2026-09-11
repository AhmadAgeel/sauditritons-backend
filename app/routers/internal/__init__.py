from fastapi import APIRouter, Depends

from . import student_profile, event, workspace_user
from app import oauth2

router = APIRouter(dependencies=[Depends(oauth2.get_current_officer)])

# router.include_router(student_profile.router)
router.include_router(event.router)
router.include_router(workspace_user.router)
