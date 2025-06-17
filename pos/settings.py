from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-3%(kmd^a*uv+^&8#4$&jtrw7@sq&66(h3@wk!p6ksm=j%3hu*s'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'widget_tweaks',
    'ventas',
    # 'inventario',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

LOGIN_URL = '/login/'

LOGIN_REDIRECT_URL = '/'

LOGOUT_REDIRECT_URL = '/login/'

ROOT_URLCONF = 'pos.urls'

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'ventas.context_processors.roles',
            ],
        },
    },
]

WSGI_APPLICATION = 'pos.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        'OPTIONS': {
            'user_attributes': ('username', 'email'),
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
            # 'message': "La contraseña debe tener al menos 8 caracteres.",  # <-- quita esto
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        # 'OPTIONS': {
        #     'message': "Esta contraseña es demasiado común.",  # <-- quita esto también
        # }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        # 'OPTIONS': {
        #     'message': "La contraseña no puede ser totalmente numérica.",  # <-- quita esto también
        # }
    },
]

# Tiempo de inactividad antes de cerrar sesión automáticamente (en segundos)
SESSION_COOKIE_AGE = 600  # 10 minutos

SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Opcional: cierra sesión al cerrar navegador

SESSION_SAVE_EVERY_REQUEST = True  # Renueva el tiempo en cada request activa

LOCALE_PATHS = [ BASE_DIR.parent / 'locale' ]

LANGUAGE_CODE = 'es'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'

STATICFILES_DIRS = [ BASE_DIR / "static" ]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

STATIC_ROOT = BASE_DIR.parent / 'static_collected'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = 'noreply@hellstech.com'