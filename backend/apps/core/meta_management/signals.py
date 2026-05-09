from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils import timezone

from ..models import AssetUsage, MediaAsset


@receiver(post_save, sender=AssetUsage)
def increment_ref_count(sender, instance, created, **kwargs):
    if not created:
        return

    def _apply():
        MediaAsset.objects.filter(pk=instance.asset_id).update(
            ref_count=F("ref_count") + 1,
            unreferenced_since=None,
        )

    transaction.on_commit(_apply)


@receiver(post_delete, sender=AssetUsage)
def decrement_ref_count(sender, instance, **kwargs):
    asset_id = instance.asset_id

    def _apply():
        MediaAsset.objects.filter(pk=asset_id, ref_count__gt=0).update(
            ref_count=F("ref_count") - 1,
        )
        MediaAsset.objects.filter(pk=asset_id, ref_count=0, unreferenced_since__isnull=True).update(
            unreferenced_since=timezone.now(),
        )

    transaction.on_commit(_apply)
