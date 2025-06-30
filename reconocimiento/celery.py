# reconocimiento/celery.py
from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# 1) le digo a Django dónde están los settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reconocimiento.settings')

# 2) instancio la app de Celery
app = Celery('reconocimiento')

# 3) cargo la configuración desde Django settings (prefijos CELERY_)
app.config_from_object('django.conf:settings', namespace='CELERY')

# 4) autodetecta tasks.py en cada app instalada
app.autodiscover_tasks()
