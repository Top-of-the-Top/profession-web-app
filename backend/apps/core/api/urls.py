from django.urls import path

from .views import AssetUploadCommitView, AssetUploadInitiateView, AssetUploadStatusView


app_name = 'core'


urlpatterns = [
    path(
        'uploads/initiate',
        AssetUploadInitiateView.as_view(),
        name='upload-initiate',
    ),
    path(
        'uploads/<uuid:asset_id>/status',
        AssetUploadStatusView.as_view(),
        name='upload-status',
    ),
    path(
        'uploads/<uuid:asset_id>/commit',
        AssetUploadCommitView.as_view(),
        name='upload-commit',
    ),
]
