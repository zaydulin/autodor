from django.urls import path
from . import views

urlpatterns = [
    path('update-device-token/', views.UpdateDeviceTokenView.as_view(), name='update_device_token'),
]
