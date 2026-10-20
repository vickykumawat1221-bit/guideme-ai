from django.contrib.auth.models import User
from django.db import models
from django.db.models import Avg
from django.utils import timezone


CATEGORY_CHOICES = [
    ("Health", "Health"),
    ("Career", "Career"),
    ("Fitness", "Fitness"),
    ("Beauty", "Beauty"),
    ("Education", "Education"),
    ("Finance", "Finance"),
    ("Legal", "Legal"),
    ("Technology", "Technology"),
    ("Wellness", "Wellness"),
    ("Other", "Other"),
]

BOOKING_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("confirmed", "Confirmed"),
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
]

COMMUNICATION_METHODS = [
    ("Chat", "Chat"),
    ("Call", "Call"),
    ("Video Call", "Video Call"),
    ("In Person", "In Person"),
]

URGENCY_CHOICES = [
    ("Low", "Low"),
    ("Medium", "Medium"),
    ("High", "High"),
]


class Expert(models.Model):
    name = models.CharField(max_length=100)
    profession = models.CharField(max_length=100)
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, blank=True, default="Other"
    )
    bio = models.TextField(blank=True, default="")
    experience = models.IntegerField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    languages = models.CharField(max_length=200)
    hourly_rate = models.PositiveIntegerField(default=0, help_text="Rate in INR per session")
    availability = models.CharField(max_length=100, default="Available on request")
    owner = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="experts",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at", "id"]

    def __str__(self):
        return f"{self.name} ({self.profession})"

    @property
    def rating(self):
        """Average review rating, rounded to one decimal, or None."""
        value = self.reviews.aggregate(avg=Avg("rating"))["avg"]
        return round(value, 1) if value is not None else None

    @property
    def review_count(self):
        return self.reviews.count()

    def matches_query(self, query):
        haystack = " ".join(
            [
                self.name or "",
                self.profession or "",
                self.category or "",
                self.bio or "",
                self.languages or "",
                self.availability or "",
            ]
        ).lower()
        return query.lower() in haystack


class Review(models.Model):
    expert = models.ForeignKey(
        Expert, related_name="reviews", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="reviews"
    )
    user_name = models.CharField(max_length=100)
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5),
                name="review_rating_between_1_and_5",
            )
        ]

    def __str__(self):
        return f"{self.user_name} -> {self.expert.name}: {self.rating}/5"


class Booking(models.Model):
    expertName = models.CharField(max_length=100)
    expert = models.ForeignKey(
        Expert,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="bookings",
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings"
    )
    userName = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)
    problem = models.TextField()
    method = models.CharField(max_length=50, choices=COMMUNICATION_METHODS)
    urgency = models.CharField(max_length=50, choices=URGENCY_CHOICES)
    status = models.CharField(
        max_length=20, choices=BOOKING_STATUS_CHOICES, default="pending"
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    reference = models.CharField(max_length=24, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.reference or self.id}: {self.userName} -> {self.expertName}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._generate_reference()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_reference():
        import secrets

        stamp = timezone.now().strftime("%y%m%d")
        return f"GM-{stamp}-{secrets.token_hex(2).upper()}"


class AuthToken(models.Model):
    """Simple bearer token used by the lightweight login flow."""

    key = models.CharField(max_length=64, unique=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="auth_token"
    )
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"token for {self.user.username}"
