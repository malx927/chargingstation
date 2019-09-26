# coding=utf8
import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'x33xu+_9sgoetjwrxk)-_v(s$z=kw_82^76d48=a4(+n^kp$8@'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'xadmin',
    'rest_framework',
    'rest_framework.authtoken',
    'channels',
    'users',
    'crispy_forms',
    'reversion',
    'stationmanager',
    'chargingorder',
    'codingmanager',
    'wxchat',
    'echargenet',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'chargingstation.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')]
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'chargingstation.wsgi.application'
ASGI_APPLICATION = "chargingstation.routing.application"

# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'chargingstation',
        'USER': 'root',
        'PASSWORD': '',
        'HOST': '127.0.0.1',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        }
    }
}

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'users.UserProfile'
# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_L10N = True

USE_TZ = False




# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'global_static'),
)

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

SITE_TITLE = u'测试'
SITE_FOOTER = u'测试'

# 账号资金阀值()元
ACCOUNT_BALANCE = 1.1

# 比例因子
FACTOR_SINGLE_VOLTAGE = 0.01
FACTOR_CURRENT = 0.1
FACTOR_VOLTAGE = 0.1
FACTOR_TEMPERATURE = 0.1
FACTOR_BATTERY_SOC = 1
FACTOR_READINGS = 0.01


WEB_URL = 'haotian.natapp1.cc'

# mqtt
MQTT_HOST = "iot.canage.com.cn"
DEVICENAME_RECV = 'server_recv2'
DEVICENAME_SEND = 'server_send2'
USERNAME = 'mqtt'
PASSWORD = 'yd1q2w3e4r'

# redis 超时判断
MQTT_REDIS_URL = '127.0.0.1'
MQTT_REDIS_PORT = 6379

CHARGING_SEND_CMD_INTERVAL = 5
FREQUENCY = 3

CHARG_STATUS_OVER_TIME = 30     # 直流
CHARG_AC_STATUS_OVER_TIME = 30 * 60     # 交流
PILE_STATUS_OVER_TIME = 2 * 60  # 直流
PILE_AC_STATUS_OVER_TIME = 30 * 60  # 交流
REPLY_TO_WORK_OVERTIME = 60 * 3

CHARING_PILE_STATUS = 'charing_pile_status'             # 电桩桩状态上报超时
CHARG_SEND_CMD_OVERTIME = 'charg_send_cmd_overtime'     # 发送充电命令后，判断是否超时
CHARGING_STATUS_OVERTIME = 'charging_status_overtime'   # 充电状态上报超时
CHARG_REPLY_TO_WORK_OVERTIME = "reply_to_work_overtime"  # 充电回复到开始充电作业判断超时

# websocket url
WEBSOCKET_URL = 'ws://' + WEB_URL


# 测试号WeChat
WECHAT_TOKEN = 'dayankele123'
APP_URL = 'http://' + WEB_URL + '/wechat'
ROOT_URL = 'http://' + WEB_URL
WECHAT_APPID = 'wxbc591183cb175d16'
WECHAT_SECRET = 'bc4925cf759e581f41e8ea3699c36176'
MCH_ID = '1524211111'
MCH_KEY = 'BE0EE67111111114961EA24AAFS77'
REDIS_URL = 'redis://127.0.0.1:6379/0'
NOTIFY_URL = 'http://' + WEB_URL + '/order/pay/notify/'        # 根据实际域名修改

# e充网
OPERATORSECRET = 'RJ4MmF9RdKMV8lGn'  # 申请认证使用
SIGSECRET = 'TiF5KmJCfXrNzz3r'  # 签名的加密密钥
DATASECRET = 'YaDtFWtGGGiisEBB'  # Data信息进行加密
DATASECRETIV = '6T20he7lkiG2XAuv'  # 用户AES加密过程的混合加密
OPERATORID = 'MA004REG2'  # 组织机构代码
ECHARGE_OPERATORID = '348375727'  # e充网组织机构代码
EXPIRATION_DELTA = 3 * 24 * 3600

# celery
BROKER_URL = 'redis://127.0.0.1:6379/2'
CELERY_TIMEZONE = TIME_ZONE
CELERYBEAT_SCHEDULER = 'djcelery.schedulers.DatabaseScheduler'

CELERYD_CONCURRENCY = 5 # celery worker的并发数 也是命令行-c指定的数目,事实上实践发现并不是worker也多越好,保证任务不堆积,加上一定新增任务的预留就可以
CELERYD_PREFETCH_MULTIPLIER = 4  # celery worker 每次去rabbitmq取任务的数量，我这里预取了4个慢慢执行,因为任务有长有短没有预取太多
CELERYD_MAX_TASKS_PER_CHILD = 40 # 每个worker执行了多少任务就会死掉，我建议数量可以大一些，比如200