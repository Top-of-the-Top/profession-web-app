import os
import time
import requests
import base64
from agora_token_builder import RtcTokenBuilder

ROLE_PUBLISHER = 1 # может отправлять видео и аудио
ROLE_SUBSCRIBER = 2 # может только получать
NETLESS_API_BASE = "https://api.netless.link/v5"
AGORA_RECORDING_API_BASE = "https://api.agora.io/v1/apps"

# Функции для генерации rtc токена
def generate_rtc_token(channel_name, uid, role=ROLE_PUBLISHER):
  app_id = os.getenv('AGORA_APP_ID')
  app_certificate = os.getenv('AGORA_APP_CERTIFICATE')

  token_expiration_is_seconds = 24 * 3600
  privilege_expired_ts = int(time.time()) + token_expiration_is_seconds

  token = RtcTokenBuilder.buildTokenWithUid(app_id, app_certificate, channel_name, uid, role, privilege_expired_ts)
  return token

def user_uid_from_uuid(user_uuid):
  return hash(str(user_uuid)) % (2**31) + 1

# Функции для работы с доской
def _get_whiteboard_sdk_token():
  ak = os.getenv('AGORA_WHITEBOARD_AK')
  sk = os.getenv('AGORA_WHITEBOARD_SK')
  region = os.getenv('AGORA_WHITEBOARD_REGION', 'eu')

  response = requests.post(
    f"{NETLESS_API_BASE}/tokens/teams",
    headers={
      'Content-Type': 'application/json',
      'region': region,
    },
    json={
      'accessKey': ak,
      'secretAccessKey': sk,
      'lifespan': 3600000,
      'role': 'admin',
    },
  )
  response.raise_for_status()
  return response.text.strip('"')

def create_whiteboard_room():
  sdk_token = _get_whiteboard_sdk_token()
  region = os.getenv('AGORA_WHITEBOARD_REGION', 'eu')

  response = requests.post(
    f"{NETLESS_API_BASE}/rooms",
    headers={
      'token': sdk_token,
      'Content-Type': 'application/json',
      'region': region,
    },
    json={
      'isRecord': False,
      'limit': 0,
    },
  )
  response.raise_for_status()
  data = response.json()
  return data['uuid']

def generate_whiteboard_room_token(room_uuid, role='writer'):
  sdk_token = _get_whiteboard_sdk_token()
  region = os.getenv('AGORA_WHITEBOARD_REGION', 'eu')

  response = requests.post(
    f"{NETLESS_API_BASE}/tokens/rooms/{room_uuid}",
    headers={
      'token': sdk_token,
      'Content-Type': 'application/json',
      'region': region,
    },
    json={
      'lifespan': 7200000,
      'role': role,
    },
  )
  response.raise_for_status()
  return response.text.strip('"')

# Функции для работы с записью вебинара
def _get_recording_auth_header():
  customer_id = os.getenv('AGORA_CUSTOMER_ID')
  customer_secret = os.getenv('AGORA_CUSTOMER_SECRET')

  credentials = f"{customer_id}:{customer_secret}"
  encoded = base64.b64encode(credentials.encode()).decode()

  return f"Basic {encoded}"

def recording_acquire(channel_name, uid):
  app_id = os.getenv('AGORA_APP_ID')

  response = requests.post(
    f"{AGORA_RECORDING_API_BASE}/{app_id}/cloud_recording/acquire",
    headers={
      'Content-Type': 'application/json',
      'Authorization': _get_recording_auth_header(),
    },
    json={
      'cname': channel_name,
      'uid': uid,
      'clientRequest': {},
    },
  )
  response.raise_for_status()
  return response.json()['resourceId']

def recording_start(channel_name, uid, resource_id, token):
  app_id = os.getenv('AGORA_APP_ID')

  storage_config = {
    'vendor': 1,
    'region': 3,
    'bucket': os.getenv('AWS_S3_BUCKET_NAME'),
    'accessKey': os.getenv('AWS_ACCESS_KEY_ID'),
    'secretKey': os.getenv('AWS_SECRET_ACCESS_KEY'),
    'fileNamePrefix': ['recordings', 'webinars'],
  }

  response = requests.post(
    f"{AGORA_RECORDING_API_BASE}/{app_id}/cloud_recording/resourceid/{resource_id}/mode/composite/start",
    headers={
      'Content-Type': 'application/json',
      'Authorization': _get_recording_auth_header(),
    },
    json={
      'cname': channel_name,
      'uid': uid,
      'clientRequest': {
        'token': token,
        'recordingConfig': {
          'channelType': 0,
          'maxIdleTime': 300,
        },
        'storageConfig': storage_config,
      },
    },
  )
  response.raise_for_status()
  return response.json()['sid']

def recording_stop(channel_name, uid, resource_id, sid):
  app_id = os.getenv('AGORA_APP_ID')

  response = requests.post(
    f"{AGORA_RECORDING_API_BASE}/{app_id}/cloud_recording/resourceid/{resource_id}/sid/{sid}/mode/composite/stop",
    headers={
      'Content-Type': 'application/json',
      'Authorization': _get_recording_auth_header(),
    },
    json={
      'cname': channel_name,
      'uid': uid,
      'clientRequest': {},
    },
  )
  response.raise_for_status()
  return response.json()
