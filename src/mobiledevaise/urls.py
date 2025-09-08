from django.urls import path
from . import views

urlpatterns = [
    path('update-device-token/', views.UpdateDeviceTokenView.as_view(), name='update_device_token'),
]
#http://127.0.0.1:8000/edit_profile