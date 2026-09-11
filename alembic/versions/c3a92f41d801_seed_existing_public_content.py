"""seed existing public content

Revision ID: c3a92f41d801
Revises: 91c0a3d54be2
Create Date: 2026-09-08 09:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3a92f41d801"
down_revision: Union[str, Sequence[str], None] = "91c0a3d54be2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    announcements = sa.table("announcements", sa.column("title"), sa.column("body"), sa.column("is_published"), sa.column("is_pinned"))
    op.bulk_insert(announcements, [{"title": "Membership is open", "body": "Join SSA to receive member updates, help shape events, and optionally appear in the student and alumni directory.", "is_published": True, "is_pinned": True}])

    resources = sa.table("resources", sa.column("title"), sa.column("description"), sa.column("category"), sa.column("kind"), sa.column("source"), sa.column("href"), sa.column("featured"), sa.column("is_published"))
    op.bulk_insert(resources, [
        {"title": "Food & Housing Resource Guide", "description": "A downloadable UC San Diego guide to housing and basic needs.", "category": "New Student", "kind": "pdf", "source": "UC San Diego Basic Needs", "href": "/resources/ucsd-food-housing-guide.pdf", "featured": True, "is_published": True},
        {"title": "Off-Campus Housing", "description": "Listings, renter guidance, roommate search, and legal support.", "category": "Housing", "kind": "official_site", "source": "UC San Diego", "href": "https://students.ucsd.edu/campus-services/housing/offcampus/", "featured": True, "is_published": True},
        {"title": "Academic Advising", "description": "Find college, major, and department advising contacts.", "category": "Academics", "kind": "official_site", "source": "UC San Diego Students", "href": "https://students.ucsd.edu/academics/advising/", "featured": True, "is_published": True},
        {"title": "Career Center", "description": "Appointments, job search tools, workshops, and recruiting events.", "category": "Career", "kind": "official_site", "source": "UC San Diego", "href": "https://career.ucsd.edu/", "featured": True, "is_published": True},
        {"title": "Scholarships", "description": "Scholarship opportunities, application guidance, and financial aid information.", "category": "Academics", "kind": "official_site", "source": "Financial Aid & Scholarships", "href": "https://fas.ucsd.edu/types/scholarships/", "featured": False, "is_published": True},
        {"title": "Visa & Status Advising", "description": "Immigration advising and resources for international students.", "category": "New Student", "kind": "official_site", "source": "UC San Diego ISEO", "href": "https://iseo.ucsd.edu/student-services/advising-services/index.html", "featured": False, "is_published": True},
        {"title": "Counseling & Psychological Services", "description": "Confidential mental health support and counseling for students.", "category": "Health & Wellbeing", "kind": "official_site", "source": "UC San Diego CAPS", "href": "https://caps.ucsd.edu/", "featured": False, "is_published": True},
        {"title": "Student Health Services", "description": "Appointments, urgent care, pharmacy, and student health information.", "category": "Health & Wellbeing", "kind": "official_site", "source": "UC San Diego", "href": "https://studenthealth.ucsd.edu/", "featured": False, "is_published": True},
    ])

    board = sa.table("board_members", sa.column("name"), sa.column("role"), sa.column("group_name"), sa.column("sort_order"), sa.column("is_published"))
    rows = [
        ("Fawaz Al-Senayin", "President", "executive"), ("Ahmed Turkistani", "VP External", "executive"),
        ("Nawar Kidwai", "VP Internal", "executive"), ("Ranya Tashkandy", "Events Lead", "executive"),
        ("Mariya Alsaiari", "Media Lead", "executive"), ("Almontaha Alsonbul", "Treasurer", "executive"),
        ("Abdulrahman Alghamdi", "Secretary", "executive"), ("Ahmad Ageel", "Events", "board"),
        ("Khalil Alshanqiti", "Events", "board"), ("Nooran Basheer", "Events", "board"),
        ("Anas Almalki", "Content", "board"), ("Faris Al Salem", "Media / Sports", "board"),
        ("Akbar Alhashim", "Photographer", "board"), ("Fatimah Alhumrani", "Photographer", "board"),
        ("Faisal Al Dossary", "IT", "board"), ("Fahad Aljehani", "Website", "board"),
    ]
    op.bulk_insert(board, [{"name": name, "role": role, "group_name": group, "sort_order": index, "is_published": True} for index, (name, role, group) in enumerate(rows)])


def downgrade() -> None:
    op.execute("DELETE FROM board_members")
    op.execute("DELETE FROM resources")
    op.execute("DELETE FROM announcements WHERE title = 'Membership is open'")
