from django.urls import path
from .views import experts, bookings

urlpatterns = [
    path('experts/', experts),
    path('bookings/', bookings),
]