import logging
import uuid
from datetime import timedelta

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from django.utils import timezone

from ..dto import ObjectMeta, PresignedUpload
from ..errors import AssetStorageUnavailable
from .base import StorageBackend


logger = logging.getLogger(__name__)


YANDEX_PUBLIC_URL_TEMPLATE = 'https://storage.yandexcloud.net/{bucket}/{key}'
DEFAULT_PRESIGN_TTL_SECONDS = 300 


class S3PresignedUrlService:

    def __init__(self, client, bucket, public_url_template):
        self._client = client
        self._bucket = bucket
        self._public_url_template = public_url_template

    def issue_post(self, storage_key, max_size, expires_in=DEFAULT_PRESIGN_TTL_SECONDS):
        conditions = [['content-length-range', 1, max_size]]

        try:
            response = self._client.generate_presigned_post(
                Bucket=self._bucket,
                Key=storage_key,
                Conditions=conditions,
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            logger.error('S3 presigned post failed: %s', e)
            raise AssetStorageUnavailable()

        expires_at = timezone.now() + timedelta(seconds=expires_in)

        return PresignedUpload(
            method='POST',
            url=response['url'],
            storage_key=storage_key,
            expires_at=expires_at,
            fields=response.get('fields') or {},
            headers={},
        )

    def issue_get(self, storage_key, expires_in=DEFAULT_PRESIGN_TTL_SECONDS):
        try:
            return self._client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self._bucket, 'Key': storage_key},
                ExpiresIn=expires_in,
            )
        except ClientError as e:
            logger.error('S3 generate_presigned_url failed: %s', e)
            raise AssetStorageUnavailable()

    def build_public_url(self, storage_key):
        return self._public_url_template.format(
            bucket=self._bucket,
            key=storage_key,
        )


class S3Backend(StorageBackend):

    name = 's3'

    def __init__(self, bucket, access_key, secret_key, endpoint_url, region_name, public_url_template=YANDEX_PUBLIC_URL_TEMPLATE):
        self._bucket = bucket
        self._endpoint_url = endpoint_url
        self._client = boto3.client(
            's3',
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=Config(signature_version='s3v4'),
        )
        self._urls = S3PresignedUrlService(
            client=self._client,
            bucket=bucket,
            public_url_template=public_url_template,
        )

    def build_storage_key(self, hint):
        owner_part = hint.owner_id or 'anon'
        month = timezone.now().strftime('%Y%m')
        return f'assets/u/{owner_part}/{month}/{uuid.uuid4().hex}'

    def issue_presigned_upload(self, storage_key, policy):
        return self._urls.issue_post(storage_key, policy.max_size)

    def resolve_url(self, asset, viewer=None, ttl_seconds=DEFAULT_PRESIGN_TTL_SECONDS):
        if asset.visibility == 'public':
            return self._urls.build_public_url(asset.storage_key)
        return self._urls.issue_get(asset.storage_key, ttl_seconds)

    def head(self, storage_key):
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=storage_key)
        except ClientError as e:
            code = e.response.get('Error', {}).get('Code', '')
            if code in ('404', 'NoSuchKey', 'NotFound'):
                return None
            logger.error('S3 head_object failed: %s', e)
            raise AssetStorageUnavailable()

        return ObjectMeta(
            key=storage_key,
            size_bytes=response.get('ContentLength', 0),
            etag=(response.get('ETag') or '').strip('"'),
            last_modified=response.get('LastModified') or timezone.now(),
            mime_type=response.get('ContentType') or '',
        )

    def delete(self, storage_key):
        try:
            self._client.delete_object(Bucket=self._bucket, Key=storage_key)
        except ClientError as e:
            logger.error('S3 delete_object failed: %s', e)
            raise AssetStorageUnavailable()

    def put_object(self, storage_key, body, mime_type=''):
        params = {
            'Bucket': self._bucket,
            'Key': storage_key,
            'Body': body,
        }
        if mime_type:
            params['ContentType'] = mime_type
        try:
            self._client.put_object(**params)
        except ClientError as e:
            logger.error('S3 put_object failed: %s', e)
            raise AssetStorageUnavailable()
