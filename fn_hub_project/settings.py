ALLOWED_HOSTS = ['*']
import os  # 🔴 Sabse zaroori: Ise add kiya taaki os.path kaam kare

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
SECRET_KEY = 'django-insecure-u44xx3+r2k^=(qbr+&_t01^x2!m9pq0cpk!1$hi^c=o9b)lcx='

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'hub',
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

ROOT_URLCONF = 'fn_hub_project.urls'
AUTH_USER_MODEL = 'hub.User'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                # 'hub.context_processors.notification_count',  # <-- इसे कमेंट कर दें
                'hub.context_processors.user_profile_context', # 🛠️ Added: Har page par user_profile inject karne ke liye
            ],
        },
    },
]

WSGI_APPLICATION = 'fn_hub_project.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# 🟢 Media files setup (Photos aur Documents ke liye)
MEDIA_URL = '/media/'
# MEDIA_ROOT = BASE_DIR / 'media'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------------------------------------------------
# ✨ NEW ADDITIONS (Bina kuch delete kiye add kiya gaya hai)
# -------------------------------------------------------------------------

# 🔵 Login/Logout Redirect Logic
# Ye decide karta hai ki login ke baad user kahan jayega
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'login'
LOGIN_URL = 'login'

# 🟠 CSRF Trusted Origins (Testing ke liye zaroori hai agar error aaye)
CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1:8000', 'http://localhost:8000']

# Login karne ke baad user seedha hamare router par jayega
# LOGIN_REDIRECT_URL = 'dual_dashboard'
LOGIN_REDIRECT_URL = 'dashboard_router'

LOGOUT_REDIRECT_URL = 'signup'

# 🛡️ LINKEDIN-STYLE STRICT SESSION SECURITY
# Isse har tab ka request database se cross-verify hoga aur data mix nahi hoga
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# Agar user browser tab ya window close kare, toh session turant expire ho jaye
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# Har ek request par session update hoga taaki role perfectly locked rahe
SESSION_SAVE_EVERY_REQUEST = True

# Cookie ko strictly same-site isolate karne ke liye
SESSION_COOKIE_SAMESITE = 'Lax'

SESSION_COOKIE_NAME = 'my_website_sessionid'
