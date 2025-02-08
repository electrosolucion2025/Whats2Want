from django.urls import path
from .views import assistant_dashboard

urlpatterns = [
    path("dashboard/", assistant_dashboard, name="assistant_dashboard"),
]