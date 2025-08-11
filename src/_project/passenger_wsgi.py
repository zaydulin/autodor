# -*- coding: utf-8 -*-
import os, sys

# sys.path.insert(0, '/home/a/a90212rd/arenda/public_html/src')
sys.path.insert(0, "/home/a/a90212rd/bakhtiiartrucks/public_html/src")
sys.path.insert(
    1, "/home/a/a90212rd/bakhtiiartrucks/public_html/venv/lib/python3.11/site-packages"
)
os.environ["DJANGO_SETTINGS_MODULE"] = "_project.settings"
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
