"""Populate GuideMe with demo accounts, experts, reviews and bookings.

Usage::

    python manage.py seed_demo

The command is idempotent: running it twice will not duplicate records.  It is
safe to run against the committed SQLite database before a demo.
"""

from datetime import timedelta
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import Booking, Expert, Review

EXPERT_SEED = [
    {
        "name": "Vikash",
        "profession": "Doctor",
        "category": "Health",
        "bio": "General physician focused on preventive care, sleep and stress-related symptoms.",
        "experience": 5,
        "phone": "+91 98200 11001",
        "email": "vikash@guideme.ai",
        "languages": "English, Hindi",
        "hourly_rate": 800,
        "availability": "Mon–Fri, 5–8 PM",
    },
    {
        "name": "Vidhi",
        "profession": "Fashion & Grooming Expert",
        "category": "Beauty",
        "bio": "Personal styling, haircut recommendations and occasion looks.",
        "experience": 5,
        "phone": "+91 98200 11002",
        "email": "vidhi@guideme.ai",
        "languages": "English, Hindi, Bengali",
        "hourly_rate": 600,
        "availability": "Weekends, 10 AM–4 PM",
    },
    {
        "name": "Varun",
        "profession": "Therapist",
        "category": "Wellness",
        "bio": "Talk therapy for burnout, anxiety, relationships and life transitions.",
        "experience": 3,
        "phone": "+91 98200 11003",
        "email": "varun@guideme.ai",
        "languages": "English, Hindi, Dogri, Punjabi",
        "hourly_rate": 700,
        "availability": "Tue–Sat, 11 AM–7 PM",
    },
    {
        "name": "Yashaswi",
        "profession": "Artist & Creative Mentor",
        "category": "Other",
        "bio": "Portfolio reviews and creative career guidance for young artists.",
        "experience": 2,
        "phone": "+91 98200 11004",
        "email": "yashaswi@guideme.ai",
        "languages": "Hindi, English",
        "hourly_rate": 400,
        "availability": "Flexible",
    },
    {
        "name": "Dr. Ananya Sharma",
        "profession": "Dermatologist",
        "category": "Health",
        "bio": "Skin, hair and scalp concerns with evidence-based treatment plans.",
        "experience": 12,
        "phone": "+91 98200 11005",
        "email": "ananya@guideme.ai",
        "languages": "English, Hindi, Marathi",
        "hourly_rate": 1200,
        "availability": "Mon, Wed, Fri, 6–9 PM",
    },
    {
        "name": "Rohan Mehta",
        "profession": "Financial Advisor",
        "category": "Finance",
        "bio": "Budgeting, mutual funds and tax planning for early-career professionals.",
        "experience": 8,
        "phone": "+91 98200 11006",
        "email": "rohan@guideme.ai",
        "languages": "English, Hindi, Gujarati",
        "hourly_rate": 900,
        "availability": "Tue–Thu, 4–8 PM",
    },
    {
        "name": "Neha Kapoor",
        "profession": "Education Counsellor",
        "category": "Education",
        "bio": "Course selection, exam strategy and overseas admission guidance.",
        "experience": 6,
        "phone": "+91 98200 11007",
        "email": "neha@guideme.ai",
        "languages": "English, Hindi",
        "hourly_rate": 500,
        "availability": "Mon–Sat, 3–6 PM",
    },
    {
        "name": "Arjun Verma",
        "profession": "Software Engineer & Mentor",
        "category": "Technology",
        "bio": "Career switches into tech, interview prep and full-stack project reviews.",
        "experience": 9,
        "phone": "+91 98200 11008",
        "email": "arjun@guideme.ai",
        "languages": "English, Hindi, Tamil",
        "hourly_rate": 1000,
        "availability": "Weekends, 11 AM–5 PM",
    },
    {
        "name": "Meera Joshi",
        "profession": "Career Coach",
        "category": "Career",
        "bio": "Resume rewrites, interview practice and salary negotiation for mid-career professionals.",
        "experience": 7,
        "phone": "+91 98200 11009",
        "email": "meera@guideme.ai",
        "languages": "English, Hindi, Marathi",
        "hourly_rate": 750,
        "availability": "Mon–Fri, 10 AM–1 PM",
    },
    {
        "name": "Priya Nair",
        "profession": "Fitness Coach",
        "category": "Fitness",
        "bio": "Beginner-friendly strength training, fat loss and home workout plans.",
        "experience": 7,
        "phone": "+91 98200 11010",
        "email": "priya@guideme.ai",
        "languages": "English, Hindi, Malayalam",
        "hourly_rate": 550,
        "availability": "Mon–Sat, 6–9 AM",
    },
    {
        "name": "Adv. Kabir Rao",
        "profession": "Legal Advisor",
        "category": "Legal",
        "bio": "Tenant rights, contracts, employment disputes and consumer complaints.",
        "experience": 11,
        "phone": "+91 98200 11011",
        "email": "kabir@guideme.ai",
        "languages": "English, Hindi, Kannada",
        "hourly_rate": 1400,
        "availability": "Tue–Fri, 5–8 PM",
    },
]

REVIEW_SEED = [
    ("Vikash", "Priya", 5, "Patient, clear and explained every step."),
    ("Vikash", "Aman", 4, "Helpful advice, slightly rushed at the end."),
    ("Vidhi", "Sneha", 5, "Loved the styling suggestions for my wedding."),
    ("Vidhi", "Ritika", 4, "Great ideas and easy to follow."),
    ("Varun", "Karan", 5, "Felt heard for the first time in months."),
    ("Varun", "Meera", 5, "Practical techniques that actually helped my anxiety."),
    ("Yashaswi", "Dev", 4, "Honest portfolio feedback."),
    ("Dr. Ananya Sharma", "Nisha", 5, "Finally found a routine that cleared my skin."),
    ("Dr. Ananya Sharma", "Rahul", 4, "Very thorough consultation."),
    ("Rohan Mehta", "Sahil", 5, "Simplified my investments in one call."),
    ("Neha Kapoor", "Isha", 4, "Clear roadmap for my master's applications."),
    ("Arjun Verma", "Tanmay", 5, "Mock interviews were spot on."),
    ("Meera Joshi", "Ankit", 5, "Rewrote my resume and I got two callbacks in a week."),
    ("Priya Nair", "Sara", 5, "The home plan was realistic and easy to stick to."),
    ("Priya Nair", "Vikram", 4, "Good form corrections."),
    ("Adv. Kabir Rao", "Farah", 5, "Explained my tenancy options clearly."),
]


class Command(BaseCommand):
    help = "Seed GuideMe AI with demo users, experts, reviews and bookings."

    def handle(self, *args, **options):
        # Normalise legacy records such as "Vidhi " (trailing whitespace) before
        # seeding so we never create a duplicate expert.
        for expert in Expert.objects.all():
            stripped = (expert.name or "").strip()
            if stripped == expert.name:
                continue
            existing = Expert.objects.filter(name=stripped).exclude(pk=expert.pk).first()
            if existing:
                expert.bookings.update(expert=existing)
                expert.reviews.update(expert=existing)
                expert.delete()
            else:
                expert.name = stripped
                expert.save()

        demo, created = User.objects.get_or_create(
            username="demo@guideme.ai",
            defaults={
                "email": "demo@guideme.ai",
                "first_name": "Demo Admin",
                "is_staff": True,
            },
        )
        if created:
            self.stdout.write("Created demo account demo@guideme.ai / demo12345")
        else:
            self.stdout.write("Demo account already exists.")
        # Keep the documented demo credentials working on every seed run.
        demo.set_password("demo12345")
        demo.is_staff = True
        demo.save()

        experts = {}
        for payload in EXPERT_SEED:
            expert, was_created = Expert.objects.get_or_create(
                name=payload["name"], defaults=payload
            )
            if not was_created:
                # Keep existing records but fill in the new fields.
                for field, value in payload.items():
                    setattr(expert, field, value)
                expert.save()
            experts[expert.name] = expert

        for expert_name, user_name, rating, comment in REVIEW_SEED:
            expert = experts.get(expert_name)
            if not expert:
                continue
            Review.objects.get_or_create(
                expert=expert,
                user_name=user_name,
                defaults={"rating": rating, "comment": comment},
            )

        now = timezone.now()
        demo_bookings = [
            {
                "expertName": "Vikash",
                "expert": experts.get("Vikash"),
                "userName": "Demo User",
                "contact": "demo@guideme.ai",
                "problem": "Trouble sleeping for the last three weeks.",
                "method": "Video Call",
                "urgency": "Medium",
                "status": "confirmed",
                "scheduled_at": now + timedelta(days=2, hours=3),
            },
            {
                "expertName": "Rohan Mehta",
                "expert": experts.get("Rohan Mehta"),
                "userName": "Demo User",
                "contact": "demo@guideme.ai",
                "problem": "How should I split my monthly savings?",
                "method": "Chat",
                "urgency": "Low",
                "status": "pending",
                "scheduled_at": now + timedelta(days=5),
            },
        ]
        for payload in demo_bookings:
            reference = payload.pop("reference", None)
            if reference:
                Booking.objects.get_or_create(reference=reference, defaults=payload)
            elif not Booking.objects.filter(
                expertName=payload["expertName"], problem=payload["problem"]
            ).exists():
                Booking.objects.create(**payload)

        self.stdout.write(
            self.style.SUCCESS(
                "Seeded %d experts, %d reviews, %d bookings."
                % (
                    Expert.objects.count(),
                    Review.objects.count(),
                    Booking.objects.count(),
                )
            )
        )
