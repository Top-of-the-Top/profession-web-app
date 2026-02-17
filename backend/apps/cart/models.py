from django.db import models
from ..users.models import User
from ..courses.models import Course

class Cart(models.Model):
    card_id = models.AutoField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    courses = models.ManyToManyField(Course, through='CartItem')


class CartItem(models.Model):
    cart_id = models.ForeignKey(Cart, on_delete=models.CASCADE)
    course_id = models.ForeignKey(Course, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('cart_id', 'course_id')
        db_table = 'courses_by_cart'



