from django.contrib import admin

from .models import AuthToken, Booking, Expert, Review


@admin.register(Expert)
class ExpertAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "profession",
        "category",
        "experience",
        "languages",
        "rating_display",
        "availability",
    )
    list_filter = ("category", "availability")
    search_fields = ("name", "profession", "email", "languages", "bio")
    ordering = ("name",)

    @admin.display(description="Rating")
    def rating_display(self, obj):
        rating = obj.rating
        return f"{rating}/5 ({obj.review_count})" if rating is not None else "—"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("expert", "user_name", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("user_name", "comment", "expert__name")
    ordering = ("-created_at",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "expertName",
        "userName",
        "method",
        "urgency",
        "status",
        "scheduled_at",
        "created_at",
    )
    list_filter = ("status", "method", "urgency")
    search_fields = ("reference", "expertName", "userName", "contact", "problem")
    ordering = ("-created_at",)
    readonly_fields = ("reference", "created_at")


@admin.register(AuthToken)
class AuthTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("key", "created_at")
