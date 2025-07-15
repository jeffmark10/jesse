# jecistore_project/settings.py
import os
from dotenv import load_dotenv
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured # Para tratamento de erros de variáveis de ambiente

load_dotenv() # Carrega as variáveis do arquivo .env

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
# Use variáveis de ambiente para a SECRET_KEY em produção
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-_garv=!#u+!ub@t=95wb9yd)*ya+w_8k+54@vndtlx_#h^cd$5')


# SECURITY WARNING: don't run with debug turned on in production!
# Use variáveis de ambiente para DEBUG
DEBUG = os.environ.get('DJANGO_DEBUG', 'True').lower() == 'true' # Garante que 'true' ou 'False' funciona

# ALLOWED_HOSTS para produção
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'jecy.onrender.com'] # Corrigido: Removido aspas ausentes
if not DEBUG:
    # Em produção, adicione os domínios do seu site aqui
    ALLOWED_HOSTS.append('.seusitedaqui.com') 


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'store', # Seu aplicativo de loja
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

ROOT_URLCONF = 'jecistore_project.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')], # Adicione esta linha para templates globais
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'store.context_processors.cart_items_count', # NOVO: Context processor para contagem de itens do carrinho
            ],
        },
    },
]

WSGI_APPLICATION = 'jecistore_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME', 'jecy_dados'), # Nome do banco de dados
        'USER': os.environ.get('DB_USER', 'jeffmark10'), # Usuário do banco de dados
        'PASSWORD': os.environ.get('DB_PASSWORD', 'JFmarques500.'), # Senha do banco de dados
        'HOST': os.environ.get('DB_HOST', 'localhost'),  # Geralmente 'localhost' se o DB estiver no mesmo servidor
        'PORT': os.environ.get('DB_PORT', '5432'),        # Porta padrão do PostgreSQL é 5432
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'pt-br' # Alterado para Português do Brasil

TIME_ZONE = 'America/Sao_Paulo' # Alterado para o fuso horário de São Paulo

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # Onde os arquivos estáticos serão coletados em produção


# Media files (user-uploaded files, like product images)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media') # Onde as imagens de produtos serão salvas


# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configurações para autenticação de usuário
LOGIN_REDIRECT_URL = 'home' # Redireciona para a home após o login
LOGOUT_REDIRECT_URL = 'home' # Redireciona para a home após o logout

# Manipuladores de erro personalizados para páginas 404 e 500
# Certifique-se de que essas views existam e estejam configuradas em urls.py
HANDLER404 = 'store.views.custom_404_view'
HANDLER500 = 'store.views.custom_500_view'