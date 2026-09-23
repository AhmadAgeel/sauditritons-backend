"""Public event availability includes guest seats and RSVP time windows."""

from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models
from app.database import Base, get_db
from app.routers.event import occupied_seats_by_event, public_event_response, router


def event_at(now: datetime, **changes) -> models.Event:
    values = dict(
        id=7,
        title="Community dinner",
        description=None,
        location="Campus",
        location_url=None,
        category="Gathering",
        image_url=None,
        capacity=4,
        starts_at=now + timedelta(days=1),
        ends_at=None,
        rsvp_opens_at=None,
        rsvp_closes_at=now + timedelta(hours=1),
        show_rsvp_deadline=False,
        is_paid=False,
        requires_check_in=False,
        is_published=True,
        created_at=now,
    )
    values.update(changes)
    return models.Event(**values)


class PublicEventAvailabilityTests(TestCase):
    def test_counts_members_and_guests_with_companions(self) -> None:
        db = Mock()
        db.execute.side_effect = [
            [(7, ["Member guest"])],
            [(7, ["Guest one"]), (8, [])],
        ]
        self.assertEqual(occupied_seats_by_event(db, [7, 8]), {7: 4, 8: 1})

    def test_empty_event_list_does_not_query_rsvps(self) -> None:
        db = Mock()
        self.assertEqual(occupied_seats_by_event(db, []), {})
        db.execute.assert_not_called()

    def test_status_and_remaining_seats(self) -> None:
        now = datetime.now(timezone.utc)
        event = event_at(now)
        self.assertEqual(public_event_response(event, 3, now)["registration_status"], "open")
        self.assertEqual(public_event_response(event, 3, now)["remaining_seats"], 1)
        self.assertEqual(public_event_response(event, 4, now)["registration_status"], "full")
        self.assertEqual(public_event_response(event, 5, now)["remaining_seats"], 0)
        self.assertEqual(public_event_response(event_at(now, rsvp_closes_at=now), 0, now)["registration_status"], "closed")
        self.assertEqual(public_event_response(event_at(now, rsvp_opens_at=now + timedelta(minutes=1)), 0, now)["registration_status"], "not_open")

    def test_unlimited_event_has_no_remaining_seat_count(self) -> None:
        now = datetime.now(timezone.utc)
        response = public_event_response(event_at(now, capacity=None), 100, now)
        self.assertIsNone(response["remaining_seats"])
        self.assertEqual(response["registration_status"], "open")

    def test_public_routes_report_full_event_with_guest_seats(self) -> None:
        engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(engine)
        session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        now = datetime.now(timezone.utc)
        with session_factory() as db:
            db.add(event_at(now, capacity=3))
            db.add(models.GuestEventRSVP(
                event_id=7,
                ticket_code="QA1234567890",
                attendee_name="Test attendee",
                attendee_email="test@example.com",
                companion_names=["Guest one", "Guest two"],
                answers={},
            ))
            db.commit()
            app = FastAPI()
            app.include_router(router)

            def override_db():
                yield db

            app.dependency_overrides[get_db] = override_db
            with TestClient(app) as client:
                listed = client.get("/events/")
                detail = client.get("/events/7")
            self.assertEqual(listed.status_code, 200, listed.text)
            self.assertEqual(detail.status_code, 200, detail.text)
            self.assertEqual(listed.json()[0]["registration_status"], "full")
            self.assertEqual(listed.json()[0]["remaining_seats"], 0)
            self.assertEqual(detail.json()["registration_status"], "full")
        engine.dispose()
