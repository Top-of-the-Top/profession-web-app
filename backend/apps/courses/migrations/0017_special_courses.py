from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0016_rename_purchasedcourse_to_courseenrollment"),
    ]

    operations = [
        migrations.AddField(
            model_name="course",
            name="is_special",
            field=models.BooleanField(default=False, verbose_name="Специальный курс"),
        ),
    ]
