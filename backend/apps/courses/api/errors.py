from rest_framework import status


class CourseError(Exception):
    code = "COURSE_ERROR"
    message = "Ошибка операции с курсом."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class CourseNotFound(CourseError):
    code = "COURSE_NOT_FOUND"
    message = "Курс не найден."
    status = status.HTTP_404_NOT_FOUND


class CourseAccessDenied(CourseError):
    code = "COURSE_ACCESS_DENIED"
    message = "У вас нет доступа к этому курсу."
    status = status.HTTP_403_FORBIDDEN


class NotEnrolled(CourseError):
    code = "NOT_ENROLLED"
    message = "Вы не записаны на этот курс."
    status = status.HTTP_403_FORBIDDEN


class NotCourseAuthor(CourseError):
    code = "NOT_COURSE_AUTHOR"
    message = "Вы не являетесь автором этого курса."
    status = status.HTTP_403_FORBIDDEN


class SectionNotFound(CourseError):
    code = "SECTION_NOT_FOUND"
    message = "Секция не найдена."
    status = status.HTTP_404_NOT_FOUND


class SectionBelongsToDifferentCourse(CourseError):
    code = "SECTION_WRONG_COURSE"
    message = "Секция не принадлежит данному курсу."
    status = status.HTTP_400_BAD_REQUEST


class LessonNotFound(CourseError):
    code = "LESSON_NOT_FOUND"
    message = "Урок не найден."
    status = status.HTTP_404_NOT_FOUND


class LessonContentInvalid(CourseError):
    code = "LESSON_CONTENT_INVALID"
    message = "Невалидный JSON в поле content."
    status = status.HTTP_400_BAD_REQUEST


class HomeworkNotFound(CourseError):
    code = "HOMEWORK_NOT_FOUND"
    message = "Домашнее задание не найдено."
    status = status.HTTP_404_NOT_FOUND
