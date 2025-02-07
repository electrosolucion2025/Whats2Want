from django.urls import path
from .views import get_tickets_for_printing, mark_ticket_as_printed

urlpatterns = [
    path('get_tickets/', get_tickets_for_printing, name="get_tickets"),
    path('mark_printed/', mark_ticket_as_printed, name="mark_printed"),
]
