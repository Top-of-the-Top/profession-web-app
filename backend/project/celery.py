import os
from celery import Celery
from celery.signals import worker_process_init, worker_process_shutdown

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')

app = Celery('project')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

app.autodiscover_tasks(['apps.core.meta_management'], related_name='tasks', force=True)


@worker_process_init.connect
def init_worker_db(**kwargs):
    from django.db import connections
    for conn in connections.all():
        conn.close()


@worker_process_shutdown.connect
def shutdown_worker_db(**kwargs):
    from django.db import connections
    for conn in connections.all():
        conn.close()
