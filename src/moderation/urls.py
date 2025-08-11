from django.urls import path
app_name = 'webmain'
from . import views


urlpatterns = [
    path("adverts/", views.AdvertView.as_view(), name="adverts"),

]