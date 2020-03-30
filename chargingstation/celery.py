#-*-coding:utf-8-*-
from __future__ import absolute_import, unicode_literals
import os
from datetime import timedelta

from celery import Celery
from celery.schedules import crontab
from django.conf import settings

import logging.config

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chargingstation.settings')

app = Celery('chargingstation', broker=settings.BROKER_URL)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.

app.autodiscover_tasks()

app.conf.update(
    CELERYBEAT_SCHEDULE={
        # 'notification_equip_charge_status_task': {
        #     'task': 'echargenet.tasks.notification_equip_charge_status',
        #     'schedule':  timedelta(seconds=50),
        # },
        # 'notification_charge_order_info_for_bonus_task': {
        #     'task': 'echargenet.tasks.notification_charge_order_info_for_bonus',
        #     'schedule': timedelta(seconds=50),
        # },
        # 'notification_connector_status_task': {
        #     'task': 'echargenet.tasks.notification_connector_status',
        #     'schedule': crontab(minute=30, hour='1,4,7,10,13,16,19,22'),
        # },
        # 'check_charge_orders_task': {
        #     'task': 'echargenet.tasks.check_charge_orders',
        #     'schedule': crontab(minute=0, hour='1'),
        #     # 'schedule': timedelta(seconds=15),
        # },
        'update_pile_status_overtime_task': {
            'task': 'chargingorder.tasks.update_pile_status_overtime',
            'schedule': timedelta(seconds=10),
        },
        'send_start_stop_cmd_overtime_task': {
            'task': 'chargingorder.tasks.send_start_stop_cmd_overtime',
            'schedule': timedelta(seconds=5),
        },
        'charging_status_overtime_task': {
            'task': 'chargingorder.tasks.charging_status_overtime',
            'schedule': timedelta(seconds=5),
        },
        'order_charging_detail_remove_task': {
            'task': 'chargingorder.tasks.order_charging_detail_remove',
            'schedule': crontab(minute=30, hour='3'),
        },
        'charging_yesterday_data_task': {
            'task': 'statistic.tasks.charging_yesterday_data',
            'schedule': crontab(minute='0', hour='0'),
        },
        'charging_accumulative_total_stats_task': {
            'task': 'statistic.tasks.charging_accumulative_total_stats',
            'schedule': crontab(minute='1', hour='0'),
        },
        'current_month_year_accumlative_stats_task': {
            'task': 'statistic.tasks.current_month_year_accumlative_stats',
            'schedule': crontab(minute='0', hour='6'),
        },
        'charging_device_stats_task': {
            'task': 'statistic.tasks.charging_device_stats',
            'schedule': crontab(minute='0', hour='17'),
        },
        'real_time_power_stats_task': {
            'task': 'statistic.tasks.real_time_power_stats',
            'schedule': timedelta(seconds=60),
        },
        'charging_today_data_task': {
            'task': 'statistic.tasks.charging_today_data',
            'schedule': timedelta(seconds=60),
        },
    }
)

#
# LOG_CONFIG = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'standard': '%(asctime)s-%(levelname)s-[%(name)s:%(lineno)s]--%(message)s',
#         'datefmt':'%Y-%m-%d %H:%M:%S'
#     },
#     'handlers': {
#         'chargingorder.tasks.update_pile_status_overtime': {
#             'level': 'INFO',
#             'filters': None,
#             'class': 'logging.FileHandler',
#             'filename': 'update_pile_status_overtime.log'
#         },
#         'chargingorder.tasks.reply_send_charging_cmd_overtime': {
#             'level': 'INFO',
#             'filters': None,
#             'class': 'logging.FileHandler',
#             'filename': 'send_charging_cmd_overtime.log'
#         },
#         'charging_status_overtime': {
#             'level': 'INFO',
#             'filters': None,
#             'class': 'logging.FileHandler',
#             'filename': 'charging_status_overtime.log'
#         },
#     },
#     'loggers': {
#          'chargingorder.tasks.update_pile_status_overtime': {
#             'handlers': ['chargingorder.tasks.update_pile_status_overtime'],
#             'level': 'INFO',
#             'propagate': True,
#         },
#         'chargingorder.tasks.reply_send_charging_cmd_overtime': {
#             'handlers': ['chargingorder.tasks.reply_send_charging_cmd_overtime'],
#             'level': 'INFO',
#             'propagate': True,
#         },
#         'charging_status_overtime':{
#             'handlers': ['charging_status_overtime'],
#             'level': 'INFO',
#             'propagate': True,
#         },
#     }
# }
#
# logging.config.dictConfig(LOG_CONFIG)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))