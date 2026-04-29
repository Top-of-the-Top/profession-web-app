import logging
import uuid
import requests as http_requests
from sms.backends.base import BaseSmsBackend
from django.conf import settings

logger = logging.getLogger(__name__)


class NotificoreSmsBackend(BaseSmsBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, 'NOTIFICORE_API_KEY', '')
        self.api_url = getattr(settings, 'NOTIFICORE_API_URL', '') or 'https://api.notificore.ru/rest/sms/create'

    def send_messages(self, messages):
        num_sent = 0
        for message in messages:
            for recipient in message.recipients:
                if self._send_one(message, recipient):
                    num_sent += 1
        return num_sent

    def _send_one(self, message, recipient):
        payload = self._build_payload(message, recipient)
        try:
            response = http_requests.post(
                self.api_url,
                headers={'X-API-KEY': self.api_key, 'Content-Type': 'application/json'},
                json=payload,
                timeout=10,
            )
            response.raise_for_status()
            logger.info(
                'СМС отправлено на %s, ref=%s, ответ=%s',
                recipient, payload['reference'], response.text[:200],
            )
            return True
        except http_requests.exceptions.HTTPError as exc:
            self._log_http_error(recipient, exc)
            if not self.fail_silently:
                raise
            return False
        except Exception as exc:
            logger.error('Ошибка отправки СМС на %s: %s', recipient, exc)
            if not self.fail_silently:
                raise
            return False

    def _build_payload(self, message, recipient):
        return {
            'destination': 'phone',
            'originator': message.originator,
            'body': message.body,
            'msisdn': recipient.lstrip('+'),
            'reference': uuid.uuid4().hex[:16],
            'validity': '1',
            'tariff': '0',
        }

    @staticmethod
    def _log_http_error(recipient, exc):
        status_code = exc.response.status_code if exc.response is not None else 'N/A'
        body = exc.response.text[:500] if exc.response is not None else str(exc)
        logger.error('Не удалось отправить СМС на %s: HTTP %s — %s', recipient, status_code, body)
    