import json
import secrets
from datetime import timedelta

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt

from .ai import detect_category, rank_experts, semantic_available, tokenize
from .models import (
    AuthToken,
    Booking,
    BOOKING_STATUS_CHOICES,
    COMMUNICATION_METHODS,
    Expert,
    Review,
    URGENCY_CHOICES,
)

ALLOWED_ORIGIN = "*"
ALLOWED_HEADERS = "Content-Type, Authorization, X-Auth-Token"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _json(data, status=200):
    response = JsonResponse(data, status=status, safe=False)
    response["Access-Control-Allow-Origin"] = ALLOWED_ORIGIN
    response["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    response["Access-Control-Allow-Headers"] = ALLOWED_HEADERS
    response["Access-Control-Max-Age"] = "86400"
    return response


def _ok(data=None, status=200):
    return _json(data if data is not None else {}, status)


def _error(message, status=400, **extra):
    payload = {"error": message}
    payload.update(extra)
    return _json(payload, status)


def _body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body)
    except (ValueError, TypeError):
        return None


def _token_from_request(request):
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    token = request.headers.get("X-Auth-Token")
    if token:
        return token.strip()
    return request.GET.get("token")


def _current_user(request):
    token = _token_from_request(request)
    if not token:
        return None
    try:
        return AuthToken.objects.select_related("user").get(key=token).user
    except AuthToken.DoesNotExist:
        return None


def _require_user(request):
    user = _current_user(request)
    if user is None:
        return None, _error("Authentication required.", 401)
    return user, None


def _annotated_experts():
    return Expert.objects.annotate(
        avg_rating=Avg("reviews__rating"),
        total_reviews=Count("reviews", distinct=True),
    )


def _rating_of(expert):
    if hasattr(expert, "avg_rating"):
        value = expert.avg_rating
        return round(value, 1) if value is not None else None
    return expert.rating


def _review_count_of(expert):
    if hasattr(expert, "total_reviews"):
        return expert.total_reviews
    return expert.review_count


def _can_manage(expert, user):
    if user is None:
        return False
    return bool(user.is_staff or (expert.owner_id and expert.owner_id == user.id))


def serialize_expert(expert, user=None):
    return {
        "id": expert.id,
        "_id": str(expert.id),
        "name": expert.name,
        "profession": expert.profession,
        "category": expert.category,
        "bio": expert.bio,
        "experience": expert.experience,
        "phone": expert.phone,
        "email": expert.email,
        "languages": expert.languages,
        "hourly_rate": expert.hourly_rate,
        "availability": expert.availability,
        "rating": _rating_of(expert),
        "review_count": _review_count_of(expert),
        "can_manage": _can_manage(expert, user),
        "created_at": expert.created_at.isoformat() if expert.created_at else None,
    }


def serialize_review(review):
    return {
        "id": review.id,
        "expert": review.expert_id,
        "user_name": review.user_name,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat(),
    }


def serialize_booking(booking):
    return {
        "id": booking.id,
        "reference": booking.reference,
        "expertName": booking.expertName,
        "expert_id": booking.expert_id,
        "userName": booking.userName,
        "contact": booking.contact,
        "problem": booking.problem,
        "method": booking.method,
        "urgency": booking.urgency,
        "status": booking.status,
        "scheduled_at": booking.scheduled_at.isoformat()
        if booking.scheduled_at
        else None,
        "created_at": booking.created_at.isoformat() if booking.created_at else None,
    }


def _parse_scheduled(value):
    if not value:
        return None
    parsed = parse_datetime(str(value).replace("Z", "+00:00"))
    if parsed is None:
        try:
            parsed = timezone.datetime.fromisoformat(str(value))
        except ValueError:
            return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed)
    return parsed


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@csrf_exempt
def health(request):
    if request.method == "OPTIONS":
        return _ok({})
    return _ok(
        {
            "status": "ok",
            "service": "GuideMe AI",
            "ai_mode": "hybrid-semantic" if semantic_available() else "keyword-category",
        }
    )


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@csrf_exempt
def register(request):
    if request.method == "OPTIONS":
        return _ok({})
    if request.method != "POST":
        return _error("Method not allowed.", 405)

    data = _body(request)
    if data is None:
        return _error("Invalid JSON body.")

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = (data.get("role") or "user").strip().lower()

    if not name or not email or not password:
        return _error("Name, email and password are required.")
    if "@" not in email or "." not in email.split("@")[-1]:
        return _error("Please enter a valid email address.")
    if len(password) < 8:
        return _error("Password must be at least 8 characters.")
    if User.objects.filter(username=email).exists():
        return _error("An account with this email already exists.", 409)

    user = User.objects.create_user(
        username=email,
        email=email,
        password=password,
        first_name=name[:150],
        is_staff=role == "admin",
    )

    token = AuthToken.objects.create(key=secrets.token_hex(24), user=user)
    return _ok(
        {
            "token": token.key,
            "user": {
                "id": user.id,
                "name": user.first_name or user.username,
                "email": user.email,
                "is_staff": user.is_staff,
            },
        },
        201,
    )


@csrf_exempt
def login(request):
    if request.method == "OPTIONS":
        return _ok({})
    if request.method != "POST":
        return _error("Method not allowed.", 405)

    data = _body(request)
    if data is None:
        return _error("Invalid JSON body.")

    identity = (data.get("email") or data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    user = authenticate(request, username=identity, password=password)
    if user is None:
        return _error("Invalid email or password.", 401)

    token, _ = AuthToken.objects.get_or_create(
        user=user, defaults={"key": secrets.token_hex(24)}
    )
    return _ok(
        {
            "token": token.key,
            "user": {
                "id": user.id,
                "name": user.first_name or user.username,
                "email": user.email,
                "is_staff": user.is_staff,
            },
        }
    )


@csrf_exempt
def me(request):
    if request.method == "OPTIONS":
        return _ok({})
    user, error = _require_user(request)
    if error:
        return error

    return _ok(
        {
            "user": {
                "id": user.id,
                "name": user.first_name or user.username,
                "email": user.email,
                "is_staff": user.is_staff,
            },
            "expert_profiles": user.experts.count(),
            "bookings": user.bookings.count(),
            "reviews": user.reviews.count(),
        }
    )


@csrf_exempt
def logout(request):
    if request.method == "OPTIONS":
        return _ok({})
    token = _token_from_request(request)
    if token:
        AuthToken.objects.filter(key=token).delete()
    return _ok({"message": "Signed out."})


# ---------------------------------------------------------------------------
# Experts
# ---------------------------------------------------------------------------

EXPERT_FIELDS = {
    "name",
    "profession",
    "category",
    "bio",
    "experience",
    "phone",
    "email",
    "languages",
    "hourly_rate",
    "availability",
}


@csrf_exempt
def experts(request):
    if request.method == "OPTIONS":
        return _ok({})

    user = _current_user(request)

    if request.method == "GET":
        queryset = _annotated_experts()

        query = (request.GET.get("q") or "").strip()
        category = (request.GET.get("category") or "").strip()
        sort = (request.GET.get("sort") or "newest").strip().lower()

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(profession__icontains=query)
                | Q(category__icontains=query)
                | Q(bio__icontains=query)
                | Q(languages__icontains=query)
            )
        if category and category.lower() not in {"all", "any"}:
            queryset = queryset.filter(category__iexact=category)

        ordering = {
            "rating": ["-avg_rating", "-total_reviews", "name"],
            "experience": ["-experience", "name"],
            "name": ["name"],
            "rate_low": ["hourly_rate", "name"],
            "rate_high": ["-hourly_rate", "name"],
            "newest": ["-created_at", "id"],
        }.get(sort, ["-created_at", "id"])

        queryset = queryset.order_by(*ordering)
        payload = [serialize_expert(expert, user) for expert in queryset]
        return _ok(
            {
                "experts": payload,
                "count": len(payload),
                "categories": _category_counts(),
            }
        )

    if request.method == "POST":
        user, error = _require_user(request)
        if error:
            return error

        data = _body(request)
        if data is None:
            return _error("Invalid JSON body.")

        required = ["name", "profession", "experience", "phone", "email", "languages"]
        missing = [field for field in required if not str(data.get(field, "")).strip()]
        if missing:
            return _error(f"Missing required field(s): {', '.join(missing)}.")

        try:
            experience = int(data.get("experience"))
            if experience < 0:
                raise ValueError
        except (TypeError, ValueError):
            return _error("Experience must be a non-negative number.")

        profession = str(data.get("profession", "")).strip()
        bio = str(data.get("bio", "")).strip()
        category = str(data.get("category", "")).strip() or detect_category(
            f"{profession} {bio}"
        ) or "Other"

        expert = Expert.objects.create(
            name=str(data.get("name", "")).strip(),
            profession=profession,
            category=category,
            bio=bio,
            experience=experience,
            phone=str(data.get("phone", "")).strip(),
            email=str(data.get("email", "")).strip(),
            languages=str(data.get("languages", "")).strip(),
            hourly_rate=max(0, int(data.get("hourly_rate") or 0)),
            availability=str(
                data.get("availability") or "Available on request"
            ).strip(),
            owner=user,
        )
        return _ok({"message": "Expert created.", "expert": serialize_expert(expert, user)}, 201)

    return _error("Method not allowed.", 405)


@csrf_exempt
def expert_detail(request, id):
    if request.method == "OPTIONS":
        return _ok({})

    user = _current_user(request)

    try:
        expert = _annotated_experts().get(pk=id)
    except Expert.DoesNotExist:
        return _error("Expert not found.", 404)

    if request.method == "GET":
        payload = serialize_expert(expert, user)
        payload["reviews"] = [
            serialize_review(review) for review in expert.reviews.all()[:20]
        ]
        return _ok(payload)

    if request.method in {"PATCH", "PUT"}:
        if not _can_manage(expert, user):
            return _error("You do not have permission to edit this expert.", 403)

        data = _body(request)
        if data is None:
            return _error("Invalid JSON body.")

        for field in EXPERT_FIELDS & set(data):
            value = data[field]
            if field == "experience":
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    return _error("Experience must be a number.")
            elif field == "hourly_rate":
                try:
                    value = max(0, int(value))
                except (TypeError, ValueError):
                    return _error("Hourly rate must be a number.")
            elif field == "category" and not value:
                value = "Other"
            setattr(expert, field, value)

        expert.save()
        return _ok(
            {"message": "Expert updated.", "expert": serialize_expert(expert, user)}
        )

    if request.method == "DELETE":
        if not _can_manage(expert, user):
            return _error("You do not have permission to delete this expert.", 403)
        expert.delete()
        return _ok({"message": "Expert deleted successfully."})

    return _error("Method not allowed.", 405)


def _category_counts():
    counts = dict(
        Expert.objects.values_list("category")
        .annotate(total=Count("id"))
        .values_list("category", "total")
    )
    return [{"category": name, "count": total} for name, total in sorted(counts.items())]


@csrf_exempt
def expert_reviews(request, id):
    if request.method == "OPTIONS":
        return _ok({})

    try:
        expert = Expert.objects.get(pk=id)
    except Expert.DoesNotExist:
        return _error("Expert not found.", 404)

    if request.method == "GET":
        reviews = expert.reviews.all()
        return _ok(
            {
                "reviews": [serialize_review(review) for review in reviews],
                "rating": expert.rating,
                "review_count": expert.review_count,
                "distribution": _rating_distribution(expert),
            }
        )

    if request.method != "POST":
        return _error("Method not allowed.", 405)

    data = _body(request)
    if data is None:
        return _error("Invalid JSON body.")

    user = _current_user(request)
    user_name = (data.get("user_name") or data.get("userName") or "").strip()
    if not user_name and user:
        user_name = user.first_name or user.username
    if not user_name:
        return _error("Your name is required to leave a review.")

    rating_value = data.get("rating", data.get("stars"))
    try:
        rating_value = int(rating_value)
    except (TypeError, ValueError):
        return _error("Rating must be a number between 1 and 5.")
    if not 1 <= rating_value <= 5:
        return _error("Rating must be between 1 and 5.")

    comment = str(data.get("comment") or "").strip()

    lookup = {"expert": expert}
    if user:
        lookup["user"] = user
    existing = Review.objects.filter(**lookup).first() if user else None

    if existing:
        existing.rating = rating_value
        existing.comment = comment
        existing.user_name = user_name
        existing.save()
        review = existing
        created = False
    else:
        review = Review.objects.create(
            expert=expert,
            user=user,
            user_name=user_name,
            rating=rating_value,
            comment=comment,
        )
        created = True

    return _ok(
        {
            "message": "Review submitted.",
            "review": serialize_review(review),
            "rating": expert.rating,
            "review_count": expert.review_count,
        },
        201 if created else 200,
    )


def _rating_distribution(expert):
    distribution = {stars: 0 for stars in range(1, 6)}
    for row in expert.reviews.values("rating").annotate(total=Count("id")):
        distribution[row["rating"]] = row["total"]
    return distribution


# ---------------------------------------------------------------------------
# AI recommendations
# ---------------------------------------------------------------------------


@csrf_exempt
def recommend(request):
    if request.method == "OPTIONS":
        return _ok({})

    if request.method != "POST":
        return _error("Method not allowed.", 405)

    data = _body(request)
    if data is None:
        return _error("Invalid JSON body.")

    question = (data.get("question") or "").strip()
    category = (data.get("category") or "").strip() or None
    limit = data.get("limit") or 5
    try:
        limit = max(1, min(int(limit), 20))
    except (TypeError, ValueError):
        limit = 5

    if not question:
        return _error("Please enter a question.")

    user = _current_user(request)
    queryset = _annotated_experts()

    ranked = rank_experts(question, queryset, category=category)[:limit]

    payload = []
    for item in ranked:
        expert_payload = serialize_expert(item["expert"], user)
        expert_payload.update(
            {
                "match_score": item["score"],
                "match_reason": item["reason"],
                "matched_keywords": item["matched"],
            }
        )
        payload.append(expert_payload)

    return _ok(
        {
            "experts": payload,
            "meta": {
                "query": question,
                "detected_category": category or detect_category(question),
                "keywords": sorted(tokenize(question))[:10],
                "count": len(payload),
                "ai_mode": "hybrid-semantic"
                if semantic_available()
                else "keyword-category",
            },
        }
    )


# ---------------------------------------------------------------------------
# Assistant (guided chatbot)
# ---------------------------------------------------------------------------

ASSISTANT_REPLIES = {
    "Health": "It sounds like a health question. I can connect you with a doctor or therapist. "
    "If this is an emergency, please contact local emergency services instead.",
    "Career": "Let's work on your career question. A career mentor can review your goals, "
    "resume and next steps with you.",
    "Fitness": "A fitness coach can build a plan around your routine, goals and any constraints. "
    "Here are the best matches.",
    "Beauty": "A style or grooming expert can help with this. Here are the closest matches.",
    "Education": "A tutor or education counsellor can help you plan this. Here are good matches.",
    "Finance": "A finance advisor can walk you through the options. Here are relevant experts.",
    "Legal": "A legal advisor can explain your options. Here are relevant experts.",
    "Technology": "A tech mentor can help you scope this. Here are relevant experts.",
    "Wellness": "A wellness coach can help you think this through. Here are relevant experts.",
}

ASSISTANT_FOLLOW_UPS = {
    "Health": "How long has this been going on, and is it urgent?",
    "Career": "What is your current role and the outcome you want in the next 6 months?",
    "Fitness": "What is your current activity level and how many days a week can you train?",
    "Beauty": "What look are you going for, and do you have a reference photo?",
    "Education": "Which exam, course or admission are you preparing for?",
    "Finance": "What is the goal and your timeline — saving, investing or tax planning?",
    "Legal": "What kind of agreement or dispute is involved?",
    "Technology": "What are you building, and what is blocking you right now?",
    "Wellness": "What would a good outcome look like for you this month?",
}

SUGGESTED_PROMPTS = [
    "I feel burnt out at work",
    "Help me prepare for a job interview",
    "Suggest a beginner workout plan",
    "I want a new hairstyle for a wedding",
]


@csrf_exempt
def assistant(request):
    if request.method == "OPTIONS":
        return _ok({})
    if request.method != "POST":
        return _error("Method not allowed.", 405)

    data = _body(request)
    if data is None:
        return _error("Invalid JSON body.")

    message = (data.get("message") or "").strip()
    if not message:
        return _error("Please type a message.")

    lowered = message.lower()
    if lowered in {"hi", "hello", "hey", "help", "start"} or len(message) < 4:
        return _ok(
            {
                "reply": "Hi! I'm the GuideMe assistant. Tell me what you need help with — "
                "health, career, fitness, beauty, education, finance or something else.",
                "category": None,
                "suggestions": [],
                "follow_up": "What is the main thing you want advice on today?",
                "suggested_prompts": SUGGESTED_PROMPTS,
            }
        )

    category = detect_category(message)
    queryset = _annotated_experts()
    ranked = rank_experts(message, queryset, category=category)[:3]

    reply = ASSISTANT_REPLIES.get(
        category,
        "I can help route you to the right expert. Here are the closest matches I found.",
    )
    follow_up = ASSISTANT_FOLLOW_UPS.get(
        category, "Would you like to book a chat, call or video session?"
    )

    return _ok(
        {
            "reply": reply,
            "category": category,
            "suggestions": [
                {
                    **serialize_expert(item["expert"]),
                    "match_score": item["score"],
                    "match_reason": item["reason"],
                }
                for item in ranked
            ],
            "follow_up": follow_up,
            "suggested_prompts": SUGGESTED_PROMPTS,
        }
    )


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------


@csrf_exempt
def bookings(request):
    if request.method == "OPTIONS":
        return _ok({})

    user = _current_user(request)

    if request.method == "GET":
        if user is None:
            return _error("Sign in to view your bookings.", 401)

        queryset = Booking.objects.all()
        if not user.is_staff:
            queryset = queryset.filter(Q(user=user) | Q(contact__iexact=user.email))

        status = (request.GET.get("status") or "").strip().lower()
        if status:
            queryset = queryset.filter(status=status)

        return _ok(
            {
                "bookings": [serialize_booking(booking) for booking in queryset[:100]],
                "count": queryset.count(),
            }
        )

    if request.method == "POST":
        data = _body(request)
        if data is None:
            return _error("Invalid JSON body.")

        required = ["expertName", "userName", "contact", "problem", "method", "urgency"]
        missing = [field for field in required if not str(data.get(field, "")).strip()]
        if missing:
            return _error(f"Missing required field(s): {', '.join(missing)}.")

        expert = None
        expert_id = data.get("expert_id") or data.get("expertId")
        if expert_id:
            expert = Expert.objects.filter(pk=expert_id).first()

        booking = Booking.objects.create(
            expertName=str(data.get("expertName", "")).strip(),
            expert=expert,
            user=user,
            userName=str(data.get("userName", "")).strip(),
            contact=str(data.get("contact", "")).strip(),
            problem=str(data.get("problem", "")).strip(),
            method=str(data.get("method", "")).strip(),
            urgency=str(data.get("urgency", "")).strip(),
            scheduled_at=_parse_scheduled(data.get("scheduled_at")),
        )
        return _ok(
            {
                "message": "Booking saved.",
                "booking": serialize_booking(booking),
            },
            201,
        )

    return _error("Method not allowed.", 405)


@csrf_exempt
def booking_detail(request, id):
    if request.method == "OPTIONS":
        return _ok({})

    user, error = _require_user(request)
    if error:
        return error

    try:
        booking = Booking.objects.get(pk=id)
    except Booking.DoesNotExist:
        return _error("Booking not found.", 404)

    if not (
        user.is_staff
        or booking.user_id == user.id
        or (booking.expert and booking.expert.owner_id == user.id)
    ):
        return _error("You do not have permission to change this booking.", 403)

    if request.method in {"PATCH", "PUT"}:
        data = _body(request)
        if data is None:
            return _error("Invalid JSON body.")

        new_status = (data.get("status") or "").strip().lower()
        if new_status:
            valid_statuses = {choice[0] for choice in BOOKING_STATUS_CHOICES}
            if new_status not in valid_statuses:
                return _error(
                    f"Invalid status. Use one of: {', '.join(sorted(valid_statuses))}."
                )
            if not user.is_staff and new_status != "cancelled":
                return _error(
                    "Only an expert or admin can confirm or complete a booking.", 403
                )
            booking.status = new_status

        if data.get("scheduled_at") is not None:
            booking.scheduled_at = _parse_scheduled(data.get("scheduled_at"))

        booking.save()
        return _ok({"message": "Booking updated.", "booking": serialize_booking(booking)})

    if request.method == "DELETE":
        if not user.is_staff and booking.user_id != user.id:
            return _error("You do not have permission to delete this booking.", 403)
        booking.delete()
        return _ok({"message": "Booking deleted."})

    return _error("Method not allowed.", 405)


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


@csrf_exempt
def analytics(request):
    if request.method == "OPTIONS":
        return _ok({})

    if request.method != "GET":
        return _error("Method not allowed.", 405)

    today = timezone.now().date()
    last_week = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        last_week.append(
            {
                "date": day.isoformat(),
                "label": day.strftime("%a"),
                "count": Booking.objects.filter(created_at__date=day).count(),
            }
        )

    overall = Review.objects.aggregate(avg=Avg("rating"))["avg"]
    top_experts = (
        _annotated_experts()
        .filter(total_reviews__gt=0)
        .order_by("-avg_rating", "-total_reviews")[:5]
    )

    return _ok(
        {
            "totals": {
                "experts": Expert.objects.count(),
                "reviews": Review.objects.count(),
                "bookings": Booking.objects.count(),
                "users": User.objects.count(),
            },
            "average_rating": round(overall, 1) if overall is not None else None,
            "bookings_by_status": _group_count(Booking, "status"),
            "bookings_by_urgency": _group_count(Booking, "urgency"),
            "bookings_by_method": _group_count(Booking, "method"),
            "experts_by_category": _category_counts(),
            "rating_distribution": {
                stars: Review.objects.filter(rating=stars).count()
                for stars in range(1, 6)
            },
            "bookings_last_7_days": last_week,
            "top_experts": [
                {
                    "id": expert.id,
                    "name": expert.name,
                    "profession": expert.profession,
                    "category": expert.category,
                    "rating": _rating_of(expert),
                    "review_count": _review_count_of(expert),
                }
                for expert in top_experts
            ],
            "recent_bookings": [
                serialize_booking(booking) for booking in Booking.objects.all()[:5]
            ],
        }
    )


def _group_count(model, field):
    return [
        {"label": row[field], "count": row["total"]}
        for row in model.objects.values(field).annotate(total=Count("id")).order_by("-total")
    ]
