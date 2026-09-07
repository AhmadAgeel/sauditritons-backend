from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db


router = APIRouter(
    prefix="/internal/workspace-users",
    tags=["Internal Workspace Users"],
)

@router.put(
    "/{workspace_user_id}",
    response_model=schemas.WorkspaceUserResponse,
)
def upsert_workspace_user(
    workspace_user_id: int,
    update: schemas.WorkspaceUserUpsert,
    db: Session = Depends(get_db),
):
    workspace_user = db.get(
        models.WorkspaceUser,
        workspace_user_id,
    )

    if workspace_user is None:
        workspace_user = models.WorkspaceUser(
            workspace_user_id=workspace_user_id,
            display_name=update.display_name,
        )
        db.add(workspace_user)
    else:
        workspace_user.display_name = update.display_name

    db.commit()
    db.refresh(workspace_user)

    return workspace_user

