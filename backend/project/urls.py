from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.health import HealthLiveView, HealthReadyView

urlpatterns = [
    path("health/live/", HealthLiveView.as_view(), name="health-live"),
    path("health/ready/", HealthReadyView.as_view(), name="health-ready"),
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.users.api.urls")),
    path("api/v1/", include("apps.courses.api.urls")),
    path("api/v1/", include("apps.webinars.api.urls")),
    path("api/v1/", include("apps.carts.api.urls")),
    path("api/v1/", include("apps.payments.api.urls")),
    path("api/v1/", include("apps.notifications.api.urls")),
    path("api/v1/", include("apps.homeworks.api.urls")),
    path("api/v1/", include("apps.applications.api.urls")),
    path("api/v1/", include("apps.core.api.urls")),
    path("api/v1/", include("apps.admin_panel.api.url")),
    path("api/v1/statistics/", include("apps.stats.api.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/swagger",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
]

if settings.DEBUG and not settings.USE_S3:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [path("orbit/", include("orbit.urls"))]
