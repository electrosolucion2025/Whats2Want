from django.urls import path

from apps.payments.views import redsys_failure, redsys_notify, redsys_payment_redirect, redsys_success

urlpatterns = [
    path('redsys/redirect/<uuid:order_id>/', redsys_payment_redirect, name='redsys_redirect'),
    path('redsys/notify/', redsys_notify, name='redsys_notify'),
    path('success/<uuid:order_id>/', redsys_success, name='redsys_success'),
    path('failure/<uuid:order_id>/', redsys_failure, name='redsys_failure'),
]
