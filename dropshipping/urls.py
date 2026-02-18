# dropshipping/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    # Admin Panel
    path('admin/', admin.site.urls),

    # Store App URLs
    path('', include('store.urls')),

    # Redirect favicon
    path('favicon.ico', RedirectView.as_view(url='/static/images/favicon.ico')),
]

# Development-only settings
if settings.DEBUG:
    import debug_toolbar

    # Debug Toolbar URLs
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls))
    ] + urlpatterns

    # Serve media and static files in development
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
