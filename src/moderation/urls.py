from django.urls import path
app_name = 'moderation'
from . import views


urlpatterns = [
    path("faqs-information/", views.FaqsModerView.as_view(), name="faqs_moder"),
    path("adverts/", views.AdvertView.as_view(), name="adverts"),
    path("adverts/<int:pk>/", views.AdvertDetailView.as_view(), name="advert_detail"),
    path("my-applications/", views.AdvertAplicationListView.as_view(), name="my_applications"),
    path("my-applications/<uuid:pk>/", views.AdvertAplicationDetailView.as_view(), name="application_detail"),

]