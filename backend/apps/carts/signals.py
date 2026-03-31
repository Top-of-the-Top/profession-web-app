from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Cart, CartItem

@receiver(m2m_changed, sender=Cart.courses.through)
def invalidate_cart_cache_on_m2m_change(sender, instance, **kwargs):
    """Инвалидация кэша при добавлении/удалении элемента корзины"""

    try:
        if instance and instance.user:
            user_id = instance.user.id
            cache_key = f'cart_user_{user_id}'
            cache.delete(cache_key)
    except Exception as e:
        pass