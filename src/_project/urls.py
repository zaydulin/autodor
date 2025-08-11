from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('ckeditor/', include('ckeditor_uploader.urls')),
    #path("__debug__/", include("debug_toolbar.urls")),
    path("_nested_admin/", include("nested_admin.urls")),
    path('developer_management/', admin.site.urls),
    path('', include('webmain.urls', namespace='webmain')),
    path('', include('moderation.urls', namespace='moderation')),
    path('', include('useraccount.urls', namespace='useraccount')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)