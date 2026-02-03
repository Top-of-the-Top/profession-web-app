from .models import Course
from rest_framework import serializers
from django.conf import settings


class CourseSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['course_id', 'title', 'price', 'image', 'image_url']

    def get_image_url(self, obj):
        if obj.image:
            if settings.USE_S3:
                return obj.image.url
            else:
                request = self.context.get('request')
                if request:
                    return request.build_absolute_uri(obj.image.url)
                return obj.image.url
        return None