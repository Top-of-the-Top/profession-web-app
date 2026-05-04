import os
from celery import Celery
from celery.signals import task_postrun

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# meta_management — вложенный модуль внутри core, autodiscover его не находит
app.autodiscover_tasks(['apps.core.meta_management'], related_name='tasks', force=True)


@task_postrun.connect
def close_db_connections(**kwargs):
    """Закрывает DB-соединения после каждой задачи чтобы не исчерпывать пул Odyssey."""
    from django.db import connection
    connection.close()
