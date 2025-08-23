from django.urls import path
app_name = 'webmain'
from . import views


urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contacts/', views.ContactView.as_view(), name='contacts'),
    path("faqs/", views.FaqsView.as_view(), name="faqs"),
    path("blogs/", views.BlogView.as_view(), name="blogs"),
    path("blog/<slug:slug>/", views.BlogDetailView.as_view(), name="blog"),
    path("page/<slug:slug>/", views.PageDetailView.as_view(), name="page"),
    path('subscribe/',  views.subscribe, name='subscribe'),
    path('search/', views.MultiModelSearchView.as_view(), name='search'),
    path('my-trainings/', views.NearestOnlineTrainingView.as_view(), name='my_trainings'),

]