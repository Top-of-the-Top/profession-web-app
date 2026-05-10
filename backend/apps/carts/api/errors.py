from rest_framework import status


class CartError(Exception):
    code = "CART_ERROR"
    message = "Ошибка операции с корзиной."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class CourseAlreadyInCart(CartError):
    code = "COURSE_ALREADY_IN_CART"
    message = "Этот курс уже добавлен в корзину."
    status = status.HTTP_400_BAD_REQUEST


class CourseNotInCart(CartError):
    code = "COURSE_NOT_IN_CART"
    message = "Этот курс не найден в корзине."
    status = status.HTTP_404_NOT_FOUND


class CourseNotAvailable(CartError):
    code = "COURSE_NOT_AVAILABLE"
    message = "Курс недоступен для покупки."
    status = status.HTTP_404_NOT_FOUND
