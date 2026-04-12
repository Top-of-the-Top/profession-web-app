from django.core.cache import caches
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

from .models import CartItem
from .api.views import cart_hot_cache_key
    
@receiver((pre_save, pre_delete), sender=CartItem)
def invalidate_cart_cache_oт_event(sender, instance: CartItem, **kwargs):
    user_id = getattr(instance.cart, "user_id", None)
    if not user_id:
        return
    caches["hot"].delete(cart_hot_cache_key(int(user_id)))
 