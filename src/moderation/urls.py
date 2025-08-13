from django.urls import path
app_name = 'moderation'
from . import views


urlpatterns = [
    path("faqs-information/", views.FaqsModerView.as_view(), name="faqs_moder"),
    path("adverts/", views.AdvertView.as_view(), name="adverts"),
    path("adverts/<int:pk>/", views.AdvertDetailView.as_view(), name="advert_detail"),
    path('create-application/<int:advert_id>/', views.create_application, name='create_application'),
    path("my-applications/", views.AdvertAplicationListView.as_view(), name="my_applications"),
    path("my-applications/<uuid:pk>/", views.AdvertAplicationDetailView.as_view(), name="application_detail"),
    path('chat/<uuid:app_id>/send/', views.send_message, name='send_message'),
    path('chat/<uuid:app_id>/get_new_messages/', views.get_new_messages, name='get_new_messages'),
    path('start_call/<uuid:application_id>/', views.start_call, name='start_call'),
    path('application/<uuid:application_id>/update/', views.update_application, name='update_application')
]