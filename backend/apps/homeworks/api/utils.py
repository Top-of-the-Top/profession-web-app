import logging
from django.conf import settings
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError


def create_presigned_link(file_path):
    max_size = 1024 * 1024 * 10
    lifespan = 60 * 5
    fields=None
    conditions = [["content-length-range", 1, max_size]]

    s3_client = boto3.client("s3")

    try:
        response = s3_client.generate_presigned_post(
            settings.AWS_S3_BUCKET_NAME,
            file_path,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=lifespan,
        )
    except ClientError as e:
        logging.error(e)
        return None 

    expiry_date = datetime.utcnow() + timedelta(seconds=lifespan)
    response['expires_at'] = expiry_date.isoformat() + 'Z'
    
    return response

