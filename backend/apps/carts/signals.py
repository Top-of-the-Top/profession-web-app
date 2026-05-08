from django.core.cache import caches
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from .api.views import cart_hot_cache_key
from .models import CartItem


@receiver((pre_save, pre_delete), sender=CartItem)
def invalidate_cart_cache_on_event(sender, instance, **kwargs):
    user_id = getattr(instance.cart, "user_id", None)
    if not user_id:
        return
    caches["hot"].delete(cart_hot_cache_key(int(user_id)))
