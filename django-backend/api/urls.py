from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    # Auth
    path("auth/register/", views.register, name="register"),
    path("auth/login/", views.login, name="login"),
    path("auth/logout/", views.logout, name="logout"),
    path("auth/me/", views.me, name="me"),
    # Experts
    path("experts/", views.experts, name="experts"),
    path("experts/<int:id>/", views.expert_detail, name="expert-detail"),
    path("experts/<int:id>/reviews/", views.expert_reviews, name="expert-reviews"),
    # AI
    path("recommend/", views.recommend, name="recommend"),
    path("assistant/", views.assistant, name="assistant"),
    # Bookings
    path("bookings/", views.bookings, name="bookings"),
    path("bookings/<int:id>/", views.booking_detail, name="booking-detail"),
    # Insights
    path("analytics/", views.analytics, name="analytics"),
]
