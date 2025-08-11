from django.shortcuts import render
from django.views.generic import ListView, DetailView, TemplateView, FormView

from moderation.models import Advert


# Create your views here.
class AdvertView(ListView):
    template_name = 'site/useraccount/adverts.html'
    context_object_name = 'adverts'
    model = Advert
    paginate_by = 16

