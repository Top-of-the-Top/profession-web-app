import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0015_add_course_admin_fields"),
        ("payments", "0002_add_users"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name="PurchasedCourse",
            new_name="CourseEnrollment",
        ),
        migrations.AlterModelTable(
            name="courseenrollment",
            table="course_enrollments",
        ),
        migrations.AddField(
            model_name="courseenrollment",
            name="source",
            field=models.CharField(
                choices=[("payment", "Оплата"), ("application", "Заявка")],
                default="payment",
                max_length=20,
                verbose_name="Источник доступа",
            ),
        ),
        migrations.AddField(
            model_name="courseenrollment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AlterField(
            model_name="courseenrollment",
            name="payment",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="enrollments",
                to="payments.payment",
            ),
        ),
        migrations.AlterField(
            model_name="courseenrollment",
            name="user",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="enrollments",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name="courseenrollment",
            name="course",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="enrollments",
                to="courses.course",
            ),
        ),
        migrations.AlterModelOptions(
            name="courseenrollment",
            options={
                "verbose_name": "Запись на курс",
                "verbose_name_plural": "Записи на курсы",
            },
        ),
        migrations.RunSQL(
            sql="UPDATE course_enrollments SET created_at = NOW() WHERE created_at IS NULL;",
            reverse_sql=migrations.RunSQL.noop,
        ),
        migrations.AlterField(
            model_name="courseenrollment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True),
        ),
    ]
