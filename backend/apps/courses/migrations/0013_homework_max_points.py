from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0012_merge_20260425_1246'),
    ]

    operations = [
        migrations.AddField(
            model_name='homework',
            name='max_points',
            field=models.PositiveIntegerField(default=0, verbose_name='Максимальный балл за домашку'),
        ),
    ]
