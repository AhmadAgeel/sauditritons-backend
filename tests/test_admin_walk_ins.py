"""Officer-only door admission never loosens public RSVP limits."""

from datetime import datetime, timedelta, timezone
from unittest import TestCase

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import models, oauth2
from app.database import Base, get_db
from app.routers.admin import router as admin_router
from app.routers.event import router as event_router


class AdminWalkInTests(TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.db = self.session_factory()
        now = datetime.now(timezone.utc)
        self.officer = models.User(id=1, email="officer@example.com", first_name="Door", last_name="Officer", role="officer")
        self.member = models.User(id=2, email="member@example.com", first_name="Local", last_name="Member", role="member")
        self.db.add_all([self.officer, self.member, models.Event(
            id=7, title="Full event", category="Gathering", capacity=1,
            starts_at=now - timedelta(hours=1), rsvp_closes_at=now + timedelta(hours=1),
            is_published=True, is_paid=False, requires_check_in=True,
        ), models.Event(
            id=8, title="Paid event", category="Gathering", capacity=1,
            starts_at=now - timedelta(hours=1), rsvp_closes_at=now + timedelta(hours=1),
            is_published=True, is_paid=True, requires_check_in=True,
        ), models.Event(
            id=9, title="Closed RSVP", category="Gathering", capacity=1,
            starts_at=now - timedelta(hours=2), rsvp_closes_at=now - timedelta(minutes=1),
            is_published=True, is_paid=False, requires_check_in=True,
        ), models.GuestEventRSVP(
            event_id=7, ticket_code="QA1234567890", attendee_name="Registered Guest",
            attendee_email="registered@example.com", companion_names=[], answers={},
        )])
        self.db.commit()
        self.app = FastAPI()
        self.app.include_router(admin_router)
        self.app.include_router(event_router)
        self.app.dependency_overrides[get_db] = lambda: self.db
        self.app.dependency_overrides[oauth2.get_current_user] = lambda: self.officer
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.client.close()
        self.db.close()
        self.engine.dispose()

    def test_full_event_allows_ticket_free_walk_in_and_keeps_public_limit(self) -> None:
        before = self.client.get("/events/7")
        self.assertEqual(before.json()["registration_status"], "full")
        response = self.client.post("/admin/events/7/walk-ins", json={"attendee_name": "  Door Arrival  "})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["attendee_name"], "Door Arrival")
        self.assertIsNone(response.json()["attendee_email"])
        self.assertIn("checked_in_at", response.json())
        self.assertNotIn("ticket_code", response.json())
        self.assertEqual(self.db.scalar(select(func.count()).select_from(models.GuestEventRSVP)), 1)
        self.assertEqual(self.client.get("/events/7").json()["registration_status"], "full")

        attendees = self.client.get("/admin/events/7/attendees")
        self.assertEqual(attendees.status_code, 200, attendees.text)
        self.assertEqual({row["source"] for row in attendees.json()}, {"guest", "walk_in"})
        self.assertTrue(all(row["registered_at"] for row in attendees.json()))
        walk_in = next(row for row in attendees.json() if row["source"] == "walk_in")
        self.assertIsNone(walk_in["ticket_code"])
        self.assertIsNotNone(walk_in["checked_in_at"])

        removed = self.client.delete(f"/admin/events/7/walk-ins/{response.json()['id']}")
        self.assertEqual(removed.status_code, 204, removed.text)
        self.assertEqual(len(self.client.get("/admin/events/7/attendees").json()), 1)
        actions = self.db.scalars(select(models.AdminAuditLog.action)).all()
        self.assertIn("walk_in.admitted", actions)
        self.assertIn("walk_in.removed", actions)

    def test_paid_event_requires_confirmed_payment(self) -> None:
        denied = self.client.post("/admin/events/8/walk-ins", json={"attendee_name": "Paid Arrival"})
        self.assertEqual(denied.status_code, 409)
        admitted = self.client.post("/admin/events/8/walk-ins", json={"attendee_name": "Paid Arrival", "mark_paid": True})
        self.assertEqual(admitted.status_code, 201, admitted.text)
        self.assertTrue(admitted.json()["has_paid"])

    def test_closed_public_rsvp_still_allows_door_admission(self) -> None:
        self.assertEqual(self.client.get("/events/9").json()["registration_status"], "closed")
        response = self.client.post("/admin/events/9/walk-ins", json={"attendee_name": "Late Arrival"})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(self.client.get("/events/9").json()["registration_status"], "closed")

    def test_member_cannot_read_or_admit_walk_ins(self) -> None:
        self.app.dependency_overrides[oauth2.get_current_user] = lambda: self.member
        self.assertEqual(self.client.get("/admin/events/7/attendees").status_code, 403)
        self.assertEqual(self.client.post("/admin/events/7/walk-ins", json={"attendee_name": "Rejected"}).status_code, 403)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(models.EventWalkIn)), 0)
        self.member.role = "content_editor"
        self.assertEqual(self.client.post("/admin/events/7/walk-ins", json={"attendee_name": "Rejected"}).status_code, 403)

    def test_rejects_blank_name(self) -> None:
        response = self.client.post("/admin/events/7/walk-ins", json={"attendee_name": "   "})
        self.assertEqual(response.status_code, 422)
