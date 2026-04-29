import logging
from datetime import datetime, timezone, timedelta
from django.conf import settings
from django.core.files.storage import default_storage
from botocore.exceptions import ClientError

class PresignedUrlService:

  def __init__(self):
    self.s3_client = default_storage.connection.meta.client# Это единственный s3 клиент у нас в приложении
    self.max_size = 1024 * 1024 * 10
    self.lifespan = 60 * 5
    self.fields = None
    self.method = "POST"
    self.conditions = [["content-length-range", 1, self.max_size]]

  def add_max_size(self, max_size):
    self.max_size = max_size
    return self

  def add_lifespan(self, lifespan):
    self.lifespan = lifespan  
    return self

  def add_fields(self, fields):
    self.fields = fields
    return self

  def add_conditions(self, conditions):
    self.conditions = conditions
    return self
  
  def add_method(self, method):
    self.method = method
    return self

  def get_presigned_url_response(self, file_path):
    response = self._create_presigned_url(file_path)

    if response is None:
      return None

    expiry_date = datetime.now(timezone.utc) + timedelta(seconds=self.lifespan)

    response['expires_at'] = expiry_date.isoformat()
    response['method'] = self.method

    return response 

  def _create_presigned_url(self, file_path):
    
      try:
          response = self.s3_client.generate_presigned_post(
              settings.AWS_S3_BUCKET_NAME,
              file_path,
              Fields=self.fields,
              Conditions=self.conditions,
              ExpiresIn=self.lifespan,
          )
      except ClientError as e:
          logging.error(e)
          return None 

      
      return response
