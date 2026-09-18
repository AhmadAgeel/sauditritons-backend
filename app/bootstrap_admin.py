from sqlalchemy import func, select

from app.config import settings
from app.database import SessionLocal
from app.models import User


def main() -> None:
    """Promote the configured first administrator without exposing it in code."""
    email = settings.bootstrap_admin_email.strip().lower()
    if not email:
        return

    with SessionLocal() as db:
        admin_exists = db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == "admin")
        )
        if admin_exists:
            return

        user = db.scalar(
            select(User).where(func.lower(User.email) == email)
        )
        if user is None:
            print("Bootstrap administrator account does not exist yet.")
            return

        user.role = "admin"
        db.commit()
        print("Bootstrap administrator promoted.")


if __name__ == "__main__":
    main()
