
from django.contrib import admin
from django.urls import path, include
from django.conf import settings

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from drf_spectacular.renderers import JSONRenderer
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('app/', include("app.urls")),

    # API Docs — available in all environments
    path('schema/', SpectacularAPIView.as_view(renderer_classes=[JSONRenderer]), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
