from django.db import migrations
from django.db.models import Sum


def recalc_max_points(apps, schema_editor):
    Homework = apps.get_model('courses', 'Homework')
    for homework in Homework.objects.all():
        questions_total = homework.question_set.aggregate(total=Sum('max_points'))['total'] or 0
        tasks_total = homework.task_set.aggregate(total=Sum('max_points'))['total'] or 0
        homework.max_points = questions_total + tasks_total
        homework.save(update_fields=['max_points'])


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0013_homework_max_points'),
    ]

    operations = [
        migrations.RunPython(recalc_max_points, migrations.RunPython.noop),
    ]
