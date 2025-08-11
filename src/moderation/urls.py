from django.urls import path
app_name = 'moderation'
from . import views


urlpatterns = [
    path("adverts/", views.AdvertView.as_view(), name="adverts"),
    path("adverts/<int:pk>/", views.AdvertDetailView.as_view(), name="advert_detail"),

]