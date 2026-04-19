import os
import time
import logging
import jwt
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

KINESCOPE_API_BASE = 'https://api.kinescope.io/v1'
KINESCOPE_UPLOADER_BASE = 'https://uploader.kinescope.io/v2'


def _get_auth_header():
    token = os.getenv('KINESCOPE_API_TOKEN', '')
    return f'Bearer {token}'

def create_folder(name, project_id=None):
    if project_id is None:
        project_id = os.getenv('KINESCOPE_PROJECT_ID', '')

    response = requests.post(
        f'{KINESCOPE_API_BASE}/projects/{project_id}/folders',
        headers={
            'Authorization': _get_auth_header(),
            'Content-Type': 'application/json',
        },
        json={'name': name},
    )
    response.raise_for_status()
    return response.json().get('data', {}).get('id', '')

def upload_video_by_url(video_url, title, parent_id=None):
    if parent_id is None:
        parent_id = os.getenv('KINESCOPE_PROJECT_ID', '')

    response = requests.post(
        f'{KINESCOPE_UPLOADER_BASE}/video',
        headers={
            'Authorization': _get_auth_header(),
            'X-Parent-ID': parent_id,
            'X-Video-Title': title,
            'X-Video-URL': video_url,
        },
    )
    response.raise_for_status()
    return response.json().get('data', {})

def get_video_status(video_id):
    response = requests.get(
        f'{KINESCOPE_API_BASE}/videos/{video_id}',
        headers={'Authorization': _get_auth_header()},
    )
    response.raise_for_status()
    return response.json().get('data', {})

def generate_drm_token(user_id, video_id, lifetime_seconds=3600):
    payload = {
        'user_id': str(user_id),
        'video_id': video_id,
        'exp': int(time.time()) + lifetime_seconds,
        'token_type': 'kinescope_drm',
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def setup_drm_auth(callback_url, username, password, strict=True):
    response = requests.put(
        f'{KINESCOPE_API_BASE}/drm/auth',
        headers={
            'Authorization': _get_auth_header(),
            'Content-Type': 'application/json',
        },
        json={
            'url': callback_url,
            'username': username,
            'password': password,
            'strict': strict,
        }
    )
    response.raise_for_status()
    return response.json()
