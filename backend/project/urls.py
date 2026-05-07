from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.users.api.urls")),
    path("api/", include("apps.courses.api.urls")),
    path("api/", include("apps.webinars.api.urls")),
    path("api/", include("apps.carts.api.urls")),
    path("api/", include("apps.payments.api.urls")),
    path("api/", include("apps.notifications.api.urls")),
    path("api/", include("apps.homeworks.api.urls")),
    path("api/", include("apps.core.api.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/swagger",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG and not settings.USE_S3:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [path("orbit/", include("orbit.urls"))]
