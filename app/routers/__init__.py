from fastapi import APIRouter

from . import user, auth, student_profile, whatsapp, event, ticket, internal

router = APIRouter()

router.include_router(user.router)
router.include_router(auth.router)
router.include_router(student_profile.router)
router.include_router(whatsapp.router)
router.include_router(event.router)
router.include_router(ticket.router)
router.include_router(internal.router)