from rest_framework import status


class PaymentError(Exception):
    code = "PAYMENT_ERROR"
    message = "Ошибка операции с платежом."
    status = status.HTTP_400_BAD_REQUEST

    def __init__(self, status=None, message=None, details=None):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.details = details or {}
        self.status = status or self.status


class CartEmpty(PaymentError):
    code = "CART_EMPTY"
    message = "Корзина пуста. Добавьте курсы перед оплатой."
    status = status.HTTP_400_BAD_REQUEST


class SpecialCourseInCart(PaymentError):
    code = "SPECIAL_COURSE_IN_CART"
    message = "Специальные курсы нельзя купить через корзину."
    status = status.HTTP_400_BAD_REQUEST


class CoursesAlreadyPurchased(PaymentError):
    code = "COURSES_ALREADY_PURCHASED"
    message = "Некоторые курсы из корзины уже куплены."
    status = status.HTTP_400_BAD_REQUEST


class PaymentNotFound(PaymentError):
    code = "PAYMENT_NOT_FOUND"
    message = "Платёж не найден."
    status = status.HTTP_404_NOT_FOUND
