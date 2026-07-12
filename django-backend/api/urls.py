from django.urls import path
from .views import experts, bookings, delete_expert, recommend

urlpatterns = [
    path("experts/", experts),
    path("bookings/", bookings),
    path("experts/<int:id>/", delete_expert),
    path("recommend/", recommend),
]