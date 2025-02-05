from django.urls import path
from .views import MenuUploadView

urlpatterns = [
    path('upload-menu/', MenuUploadView.as_view(), name='upload_menu'),
]
