# Generated manually for meta_management (MediaAsset / AssetUsage)

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('contenttypes', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaAsset',
            fields=[
                (
                    'asset_id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        primary_key=True,
                        serialize=False,
                        verbose_name='id',
                    ),
                ),
                (
                    'storage_backend',
                    models.CharField(
                        choices=[
                            ('s3', 'Yandex Object Storage'),
                            ('kinescope', 'Kinescope'),
                            ('external', 'Внешний URL'),
                        ],
                        max_length=20,
                        verbose_name='Хранилище',
                    ),
                ),
                (
                    'storage_key',
                    models.CharField(max_length=512, unique=True, verbose_name='Ключ в хранилище'),
                ),
                (
                    'original_filename',
                    models.CharField(blank=True, max_length=512, verbose_name='Исходное имя файла'),
                ),
                (
                    'mime_type',
                    models.CharField(blank=True, max_length=128, verbose_name='MIME-тип'),
                ),
                (
                    'size_bytes',
                    models.BigIntegerField(default=0, verbose_name='Размер (байт)'),
                ),
                (
                    'status',
                    models.CharField(
                        choices=[
                            ('pending', 'Выдан presigned URL, загрузка не подтверждена'),
                            ('ready', 'Готов к выдаче'),
                            ('deleted', 'Физически удалён из хранилища'),
                        ],
                        default='pending',
                        max_length=20,
                        verbose_name='Статус',
                    ),
                ),
                (
                    'visibility',
                    models.CharField(
                        choices=[
                            ('private', 'Только владельцу / явным использованиям'),
                            ('course_paid', 'Только купившим курс'),
                            ('public', 'Публичный доступ'),
                        ],
                        default='private',
                        max_length=20,
                        verbose_name='Видимость',
                    ),
                ),
                (
                    'ref_count',
                    models.PositiveIntegerField(default=0, verbose_name='Счётчик использований'),
                ),
                (
                    'unreferenced_since',
                    models.DateTimeField(blank=True, null=True, verbose_name='Без использований с'),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создан')),
                (
                    'committed_at',
                    models.DateTimeField(blank=True, null=True, verbose_name='Подтверждён'),
                ),
                (
                    'deleted_at',
                    models.DateTimeField(blank=True, null=True, verbose_name='Физически удалён'),
                ),
                (
                    'storage_meta',
                    models.JSONField(blank=True, default=dict, verbose_name='Метаданные хранилища'),
                ),
                (
                    'owner',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='owned_assets',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Владелец',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Медиа-ассет',
                'verbose_name_plural': 'Медиа-ассеты',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AssetUsage',
            fields=[
                (
                    'usage_id',
                    models.UUIDField(
                        default=uuid.uuid4,
                        primary_key=True,
                        serialize=False,
                        verbose_name='id',
                    ),
                ),
                ('object_id', models.CharField(max_length=64, verbose_name='ID сущности')),
                (
                    'role',
                    models.CharField(
                        choices=[
                            ('task_attachment', 'Прикрепление к ответу на задание'),
                            ('homework_material', 'Материал к домашке от автора'),
                            ('lesson_block', 'Ассет внутри блока урока'),
                            ('course_cover', 'Обложка курса'),
                            ('webinar_recording', 'Запись вебинара'),
                            ('user_avatar', 'Аватар пользователя'),
                            ('whiteboard_pdf', 'PDF вебинарной доски'),
                        ],
                        max_length=32,
                        verbose_name='Роль',
                    ),
                ),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                (
                    'asset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='usages',
                        to='core.mediaasset',
                        verbose_name='Ассет',
                    ),
                ),
                (
                    'content_type',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to='contenttypes.contenttype',
                        verbose_name='Тип сущности',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Использование ассета',
                'verbose_name_plural': 'Использования ассетов',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='mediaasset',
            constraint=models.CheckConstraint(
                condition=models.Q(size_bytes__gte=0),
                name='asset_size_non_negative',
            ),
        ),
        migrations.AddConstraint(
            model_name='assetusage',
            constraint=models.UniqueConstraint(
                fields=('asset', 'content_type', 'object_id', 'role'),
                name='uniq_asset_usage',
            ),
        ),
        migrations.AddIndex(
            model_name='mediaasset',
            index=models.Index(fields=['status', 'created_at'], name='core_mediaa_status_0b5c0e_idx'),
        ),
        migrations.AddIndex(
            model_name='mediaasset',
            index=models.Index(fields=['owner', 'status'], name='core_mediaa_owner_i_8f1a2d_idx'),
        ),
        migrations.AddIndex(
            model_name='mediaasset',
            index=models.Index(fields=['ref_count', 'status'], name='core_mediaa_ref_cou_9e3b1a_idx'),
        ),
        migrations.AddIndex(
            model_name='mediaasset',
            index=models.Index(fields=['storage_backend', 'status'], name='core_mediaa_storage_7c2d4e_idx'),
        ),
        migrations.AddIndex(
            model_name='mediaasset',
            index=models.Index(fields=['status', 'unreferenced_since'], name='core_mediaa_status_2a1f8b_idx'),
        ),
        migrations.AddIndex(
            model_name='assetusage',
            index=models.Index(fields=['content_type', 'object_id'], name='core_assetu_content_3d4e5f_idx'),
        ),
        migrations.AddIndex(
            model_name='assetusage',
            index=models.Index(fields=['asset', 'role'], name='core_assetu_asset_i_6a7b8c_idx'),
        ),
        migrations.AddIndex(
            model_name='assetusage',
            index=models.Index(fields=['role'], name='core_assetu_role_9d0e1f_idx'),
        ),
    ]
