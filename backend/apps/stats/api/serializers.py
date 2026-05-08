from rest_framework import serializers


class WebinarAttendanceHeartbeatRequestSerializer(serializers.Serializer):
    """Тело post на heartbeat вебинара. Фронт просто вызывает ручку"""


class WebinarAttendanceHeartbeatResponseSerializer(serializers.Serializer):
    attendance_id = serializers.UUIDField()
    watched_seconds_total = serializers.IntegerField()


class RecordingViewHeartbeatRequestSerializer(serializers.Serializer):
    current_position = serializers.IntegerField(
        min_value=0,
        help_text="Текущая позиция плеера в секундах от начала видео",
    )


class RecordingViewHeartbeatResponseSerializer(serializers.Serializer):
    view_id = serializers.UUIDField()
    watched_seconds = serializers.IntegerField()
    last_position = serializers.IntegerField()


class UserBriefSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    full_name = serializers.CharField()


class WebinarTableRowSerializer(serializers.Serializer):
    webinar_id = serializers.UUIDField()
    course_title = serializers.CharField()
    course_slug = serializers.CharField()
    lesson_title = serializers.CharField()
    started_at = serializers.DateTimeField(allow_null=True)
    ended_at = serializers.DateTimeField(allow_null=True)
    attended_total = serializers.IntegerField()
    attended_any = serializers.IntegerField()
    attended_threshold = serializers.IntegerField()
    homework_submitted_count = serializers.IntegerField()
    attended_any_users = UserBriefSerializer(many=True)
    attended_threshold_users = UserBriefSerializer(many=True)
    homework_submitted_users = UserBriefSerializer(many=True)


class StudentCourseRefSerializer(serializers.Serializer):
    course_id = serializers.CharField()
    course_slug = serializers.CharField()
    title = serializers.CharField()


class StudentRowSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    full_name = serializers.CharField()
    email = serializers.CharField(allow_blank=True)
    phone = serializers.CharField(allow_blank=True)
    courses = StudentCourseRefSerializer(many=True)


class StudentCardWebinarSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["live", "recording", "none"])
    watched_ratio = serializers.FloatField()


class StudentCardHomeworkSerializer(serializers.Serializer):
    homework_id = serializers.CharField()
    title = serializers.CharField()
    status = serializers.CharField()
    grade = serializers.IntegerField(allow_null=True)


class StudentCardLessonSerializer(serializers.Serializer):
    lesson_id = serializers.CharField()
    lesson_title = serializers.CharField()
    webinar = StudentCardWebinarSerializer(allow_null=True)
    homeworks = StudentCardHomeworkSerializer(many=True)
    homeworks_submitted = serializers.IntegerField()
    homeworks_total = serializers.IntegerField()
    is_completed = serializers.BooleanField()


class StudentCardSerializer(serializers.Serializer):
    student_id = serializers.IntegerField()
    course_id = serializers.CharField()
    lessons = StudentCardLessonSerializer(many=True)


class SchoolCourseRowSerializer(serializers.Serializer):
    course_id = serializers.CharField()
    title = serializers.CharField()
    students = serializers.IntegerField()
    avg_progress = serializers.FloatField()
    avg_attendance = serializers.FloatField()
    avg_homework = serializers.FloatField()


class SchoolTeacherRowSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    full_name = serializers.CharField()
    reviewed_7d = serializers.IntegerField()
    reviewed_30d = serializers.IntegerField()
    last_login = serializers.DateTimeField(allow_null=True)
