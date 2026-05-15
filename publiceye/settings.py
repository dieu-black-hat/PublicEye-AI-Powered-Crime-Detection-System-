import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-your-secret-key-here'

DEBUG = True

ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',  # Add channels for WebSocket support
    'core',
    # Comment out these apps until you install them
    # 'crispy_forms',
    # 'crispy_bootstrap5',
    # 'rest_framework',
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

ROOT_URLCONF = 'publiceye.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'publiceye.wsgi.application'
ASGI_APPLICATION = 'publiceye.asgi.application'  # Enable ASGI for WebSocket support

# Database Configuration - Using SQLite for now (easier to start)
# Switch to MySQL/XAMPP later after everything works
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# XAMPP MySQL Database Configuration (Uncomment when ready for MySQL)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'publiceye_db',
#         'USER': 'root',
#         'PASSWORD': '',
#         'HOST': 'localhost',
#         'PORT': '3306',
#         'OPTIONS': {
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#         }
#     }
# }

# Channel Layers for WebSocket Real-time Alerts
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',  # Use for development
        # For production, use Redis:
        # 'BACKEND': 'channels_redis.core.RedisChannelLayer',
        # 'CONFIG': {
        #     "hosts": [('127.0.0.1', 6379)],
        # },
    },
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files (Uploaded files)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Serve static files correctly in development
if DEBUG:
    import mimetypes
    mimetypes.add_type("text/css", ".css", True)
    mimetypes.add_type("application/javascript", ".js", True)
    mimetypes.add_type("image/jpeg", ".jpg", True)
    mimetypes.add_type("image/png", ".png", True)

# Comment out crispy settings until you install crispy_forms
# CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
# CRISPY_TEMPLATE_PACK = "bootstrap5"

# AI Settings
AI_MODEL_PATH = BASE_DIR / 'models'
CRIME_TYPES = ['theft', 'assault', 'vandalism', 'robbery', 'suspicious_activity', 'fight', 'accident']

# Real-time Alert Settings
ALERT_SOUND_ENABLED = True
ALERT_POPUP_DURATION = 10  # Seconds
ALERT_TOAST_DURATION = 5  # Seconds
NOTIFICATION_SOUND_FILE = BASE_DIR / 'static' / 'sounds' / 'alert.mp3'

# WebSocket Settings
WEBSOCKET_RECONNECT_INTERVAL = 5  # Seconds
WEBSOCKET_HEARTBEAT_INTERVAL = 30  # Seconds

# Create necessary directories if they don't exist
os.makedirs(STATIC_ROOT, exist_ok=True)
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(AI_MODEL_PATH, exist_ok=True)
os.makedirs(BASE_DIR / 'static' / 'sounds', exist_ok=True)  # For alert sounds
os.makedirs(BASE_DIR / 'static' / 'css', exist_ok=True)
os.makedirs(BASE_DIR / 'static' / 'js', exist_ok=True)
os.makedirs(BASE_DIR / 'static' / 'images', exist_ok=True)
os.makedirs(BASE_DIR / 'logs', exist_ok=True)  # For log files
os.makedirs(MEDIA_ROOT / 'uploads', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'crime_clips', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'crime_screenshots', exist_ok=True)
os.makedirs(MEDIA_ROOT / 'camera_snapshots', exist_ok=True)

# Logging Configuration for Alerts
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/publiceye.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'alert_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs/alerts.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
        'core': {
            'handlers': ['file', 'console', 'alert_file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'channels': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

# Security Settings (For production)
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# Custom Settings for PublicEye
MAX_VIDEO_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
ALLOWED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.mpeg', '.flv']
CAMERA_RETENTION_DAYS = 30  # Keep camera footage for 30 days
ALERT_RETENTION_DAYS = 90  # Keep alerts for 90 days

# Real-time detection settings
REAL_TIME_DETECTION_FPS = 2  # Analyze 2 frames per second
MOTION_THRESHOLD = 50  # Motion detection sensitivity
EDGE_DENSITY_THRESHOLD = 0.3  # Edge detection threshold

# Notification Settings
NOTIFICATION_SETTINGS = {
    'enable_sound': True,
    'enable_popup': True,
    'enable_toast': True,
    'enable_browser_notification': True,
    'sound_volume': 0.5,
    'popup_duration': 10,
    'toast_duration': 5,
}

# Police Station Contacts (for future SMS/Email integration)
POLICE_STATIONS = [
    {
        'name': 'Central Police Station',
        'phone': '+1234567890',
        'email': 'central@police.gov',
        'zone': 'Downtown'
    },
    {
        'name': 'North District Station',
        'phone': '+1234567891',
        'email': 'north@police.gov',
        'zone': 'North'
    },
]

# API Settings
API_VERSION = 'v1'
API_PAGINATION_PAGE_SIZE = 20

# Cache Settings (Optional - for better performance)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Email Configuration (for future use)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Console for development
# For production, use SMTP:
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-password'
DEFAULT_FROM_EMAIL = 'PublicEye System <noreply@publiceye.com>'

# Session Settings
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# File Upload Settings
DATA_UPLOAD_MAX_NUMBER_FILES = 100
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

print("=" * 60)
print("🚔 PublicEye Crime Detection System")
print("=" * 60)
print(f"✅ Settings Loaded - Debug: {DEBUG}")
print(f"📁 Database: SQLite ({BASE_DIR / 'db.sqlite3'})")
print(f"📁 Media Root: {MEDIA_ROOT}")
print(f"📁 Static Root: {STATIC_ROOT}")
print(f"📁 Static Files Directory: {STATICFILES_DIRS[0]}")
print(f"🔌 WebSocket: {'Enabled' if CHANNEL_LAYERS else 'Disabled'}")
print(f"🤖 AI Detection: Enabled")
print(f"📊 Analytics: Enabled")
print("=" * 60)