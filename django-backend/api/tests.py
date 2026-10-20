import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from .models import AuthToken, Booking, Expert, Review


class GuideMeApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.expert = Expert.objects.create(
            name="Test Doctor",
            profession="Doctor",
            category="Health",
            bio="General physician who helps with sleep and stress.",
            experience=10,
            phone="12345",
            email="doctor@example.com",
            languages="English, Hindi",
            hourly_rate=500,
        )
        cls.other_expert = Expert.objects.create(
            name="Test Coach",
            profession="Career Coach",
            category="Career",
            bio="Resume reviews and interview preparation.",
            experience=4,
            phone="67890",
            email="coach@example.com",
            languages="English",
            hourly_rate=300,
        )
        cls.user = User.objects.create_user(
            username="user@example.com", email="user@example.com", password="secret123"
        )
        cls.other_user = User.objects.create_user(
            username="other@example.com", email="other@example.com", password="secret123"
        )
        cls.staff = User.objects.create_user(
            username="staff@example.com",
            email="staff@example.com",
            password="secret123",
            is_staff=True,
        )
        cls.user_token = AuthToken.objects.create(key="usertoken", user=cls.user)
        cls.other_token = AuthToken.objects.create(key="othertoken", user=cls.other_user)
        cls.staff_token = AuthToken.objects.create(key="stafftoken", user=cls.staff)

    def setUp(self):
        self.client = Client()

    def post(self, path, payload, token=None):
        headers = {}
        if token:
            headers["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        return self.client.post(
            path,
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    # -- auth -------------------------------------------------------------

    def test_register_and_login(self):
        response = self.post(
            "/api/auth/register/",
            {"name": "New User", "email": "New@Example.com", "password": "longpassword"},
        )
        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertIn("token", payload)
        self.assertEqual(payload["user"]["email"], "new@example.com")

        login = self.post(
            "/api/auth/login/",
            {"email": "new@example.com", "password": "longpassword"},
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["token"]

        me = self.client.get(
            "/api/auth/me/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user"]["name"], "New User")

    def test_register_rejects_duplicate_and_weak_password(self):
        duplicate = self.post(
            "/api/auth/register/",
            {"name": "Dup", "email": "user@example.com", "password": "longpassword"},
        )
        self.assertEqual(duplicate.status_code, 409)

        weak = self.post(
            "/api/auth/register/",
            {"name": "Weak", "email": "weak@example.com", "password": "short"},
        )
        self.assertEqual(weak.status_code, 400)

    def test_me_requires_auth(self):
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    # -- experts ----------------------------------------------------------

    def test_list_experts_includes_rating_fields(self):
        Review.objects.create(
            expert=self.expert, user_name="A", rating=5, comment="Great"
        )
        response = self.client.get("/api/experts/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["count"], 2)
        doctor = next(item for item in payload["experts"] if item["id"] == self.expert.id)
        self.assertEqual(doctor["rating"], 5.0)
        self.assertEqual(doctor["review_count"], 1)
        self.assertIn("can_manage", doctor)

    def test_create_expert_requires_auth(self):
        response = self.post(
            "/api/experts/",
            {
                "name": "No Auth",
                "profession": "Doctor",
                "experience": 2,
                "phone": "1",
                "email": "no@example.com",
                "languages": "English",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_create_expert_and_delete_permissions(self):
        payload = {
            "name": "Owned Expert",
            "profession": "Career Coach",
            "experience": 3,
            "phone": "999",
            "email": "owned@example.com",
            "languages": "English",
        }
        created = self.post("/api/experts/", payload, token=self.user_token.key)
        self.assertEqual(created.status_code, 201)
        expert_id = created.json()["expert"]["id"]

        forbidden = self.client.delete(
            f"/api/experts/{expert_id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.other_token.key}",
        )
        self.assertEqual(forbidden.status_code, 403)

        allowed = self.client.delete(
            f"/api/experts/{expert_id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token.key}",
        )
        self.assertEqual(allowed.status_code, 200)

    def test_staff_can_delete_seed_expert(self):
        response = self.client.delete(
            f"/api/experts/{self.other_expert.id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.staff_token.key}",
        )
        self.assertEqual(response.status_code, 200)

    # -- reviews ----------------------------------------------------------

    def test_review_create_and_aggregate(self):
        response = self.post(
            f"/api/experts/{self.expert.id}/reviews/",
            {"user_name": "Priya", "rating": 4, "comment": "Helpful"},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["rating"], 4.0)

        self.post(
            f"/api/experts/{self.expert.id}/reviews/",
            {"user_name": "Aman", "stars": 2, "comment": "Not for me"},
        )

        listing = self.client.get(f"/api/experts/{self.expert.id}/reviews/")
        self.assertEqual(listing.status_code, 200)
        body = listing.json()
        self.assertEqual(body["review_count"], 2)
        self.assertEqual(body["rating"], 3.0)
        self.assertEqual(body["distribution"]["4"], 1)
        self.assertEqual(body["distribution"]["2"], 1)

    def test_review_rejects_invalid_rating(self):
        response = self.post(
            f"/api/experts/{self.expert.id}/reviews/",
            {"user_name": "Bad", "rating": 9},
        )
        self.assertEqual(response.status_code, 400)

    def test_authenticated_review_can_be_updated(self):
        first = self.post(
            f"/api/experts/{self.expert.id}/reviews/",
            {"rating": 3},
            token=self.user_token.key,
        )
        self.assertEqual(first.status_code, 201)
        second = self.post(
            f"/api/experts/{self.expert.id}/reviews/",
            {"rating": 5, "comment": "Changed my mind"},
            token=self.user_token.key,
        )
        self.assertEqual(second.status_code, 200)
        self.assertEqual(Review.objects.filter(expert=self.expert).count(), 1)
        self.assertEqual(Review.objects.get(expert=self.expert).rating, 5)

    # -- recommendations --------------------------------------------------

    @patch("api.ai._load_embedder", return_value=None)
    def test_recommend_returns_scores_and_reasons(self, _embedder):
        response = self.post(
            "/api/recommend/",
            {"question": "I keep waking up at night and feel anxious"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("experts", body)
        self.assertIn("meta", body)
        self.assertEqual(body["meta"]["ai_mode"], "keyword-category")
        self.assertGreater(len(body["experts"]), 0)
        top = body["experts"][0]
        self.assertIn("match_score", top)
        self.assertIn("match_reason", top)
        self.assertEqual(top["id"], self.expert.id)

    def test_recommend_requires_question(self):
        response = self.post("/api/recommend/", {"question": "  "})
        self.assertEqual(response.status_code, 400)

    @patch("api.ai._load_embedder", return_value=None)
    def test_assistant_returns_suggestions(self, _embedder):
        response = self.post(
            "/api/assistant/", {"message": "I need help preparing my resume"}
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["category"], "Career")
        self.assertTrue(body["reply"])
        self.assertGreater(len(body["suggestions"]), 0)

    # -- bookings ---------------------------------------------------------

    def test_guest_booking_returns_reference(self):
        response = self.post(
            "/api/bookings/",
            {
                "expertName": self.expert.name,
                "expert_id": self.expert.id,
                "userName": "Guest",
                "contact": "guest@example.com",
                "problem": "Need advice",
                "method": "Call",
                "urgency": "High",
                "scheduled_at": "2030-01-01T10:00:00",
            },
        )
        self.assertEqual(response.status_code, 201)
        booking = response.json()["booking"]
        self.assertTrue(booking["reference"].startswith("GM-"))
        self.assertEqual(booking["status"], "pending")
        self.assertIsNotNone(booking["scheduled_at"])

    def test_booking_list_requires_auth(self):
        self.assertEqual(self.client.get("/api/bookings/").status_code, 401)

    def test_booking_status_permissions(self):
        booking = Booking.objects.create(
            expertName=self.expert.name,
            expert=self.expert,
            user=self.user,
            userName="User",
            contact=self.user.email,
            problem="x",
            method="Chat",
            urgency="Low",
        )
        # A regular user may cancel but not confirm.
        cancel = self.client.patch(
            f"/api/bookings/{booking.id}/",
            data=json.dumps({"status": "cancelled"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token.key}",
        )
        self.assertEqual(cancel.status_code, 200)
        self.assertEqual(cancel.json()["booking"]["status"], "cancelled")

        confirm = self.client.patch(
            f"/api/bookings/{booking.id}/",
            data=json.dumps({"status": "confirmed"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token.key}",
        )
        self.assertEqual(confirm.status_code, 403)

        staff_confirm = self.client.patch(
            f"/api/bookings/{booking.id}/",
            data=json.dumps({"status": "confirmed"}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.staff_token.key}",
        )
        self.assertEqual(staff_confirm.status_code, 200)

    # -- analytics --------------------------------------------------------

    def test_analytics_shape(self):
        Review.objects.create(
            expert=self.expert, user_name="A", rating=5, comment=""
        )
        response = self.client.get("/api/analytics/")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["totals"]["experts"], 2)
        self.assertEqual(body["totals"]["reviews"], 1)
        self.assertEqual(body["average_rating"], 5.0)
        self.assertEqual(len(body["bookings_last_7_days"]), 7)
        self.assertEqual(body["top_experts"][0]["name"], self.expert.name)
