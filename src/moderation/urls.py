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
    path('application/<uuid:application_id>/update/', views.update_application, name='update_application'),
    path('generate_contract/<uuid:application_id>/', views.generate_contract,name='generate_contract'),
    path('call/<uuid:application_id>/<uuid:calle_id>/', views.call_page, name='call_page'),
    path('call_iframe/<uuid:application_id>/<uuid:calle_id>/', views.call_page_iframe, name='call_page_iframe'),
    path('expenses/create/', views.CreateExpenseView.as_view(), name='create_expense'),
    path('call/<int:call_id>/hangup/', views.hangup_call, name='hangup_call'),
    path('applications-list/', views.application_list, name='application_list'),
    path('document_editor/<uuid:document_id>/',views.document_editor,name='document_editor'),
    path('save-document/<uuid:pk>/', views.save_document, name='save_document'),
    path('check_active_call/', views.check_active_call, name='check_active_call'),
    path('path/create/', views.create_path, name='create_path'),
    path('path/update/<int:path_id>/', views.update_path, name='update_path'),
    path('path/delete/<int:path_id>/', views.delete_path, name='delete_path'),
    path('responsibility/create/', views.create_responsibility, name='create_responsibility'),
    path('responsibility/update/<int:responsibility_id>/', views.update_responsibility,
         name='update_responsibility'),
    path('responsibility/delete/<int:responsibility_id>/', views.delete_responsibility,
         name='delete_responsibility'),

]