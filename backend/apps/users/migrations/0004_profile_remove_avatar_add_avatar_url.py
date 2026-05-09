# Generated manually: модель перешла на avatar_url (S3/MediaAsset), в БД оставался avatar.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_alter_profile_gender_alter_user_first_name_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="avatar",
        ),
        migrations.AddField(
            model_name="profile",
            name="avatar_url",
            field=models.CharField(
                blank=True,
                default="",
                max_length=500,
                verbose_name="URL аватара (legacy)",
            ),
        ),
    ]
