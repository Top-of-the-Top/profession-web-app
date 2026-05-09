from django.conf import settings
from django.core.cache import caches
from django.db import connection
from django.http import JsonResponse
from django.views import View


class HealthLiveView(View):

    def get(self, request, *args, **kwargs):
        return JsonResponse({"status": "ok", "check": "live"})


class HealthReadyView(View):

    def get(self, request, *args, **kwargs):
        try:
            connection.ensure_connection()
        except Exception as exc:
            payload = {"status": "unavailable", "check": "ready", "reason": "database"}
            if settings.DEBUG:
                payload["detail"] = str(exc)
            return JsonResponse(payload, status=503)

        try:
            cache = caches["hot"]
            key = "__healthcheck__"
            cache.set(key, "1", timeout=10)
            if cache.get(key) != "1":
                raise RuntimeError("cache read/write mismatch")
        except Exception as exc:
            payload = {"status": "unavailable", "check": "ready", "reason": "cache"}
            if settings.DEBUG:
                payload["detail"] = str(exc)
            return JsonResponse(payload, status=503)

        return JsonResponse({"status": "ok", "check": "ready"})
