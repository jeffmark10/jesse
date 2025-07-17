# jecistore_project/settings.py
import os
from pathlib import Path
import environ # Importa django-environ
from django.core.exceptions import ImproperlyConfigured # Importa para lidar com chaves secretas ausentes
import sys # Importa o módulo sys para acessar sys.stderr

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 1. Inicializa django-environ.
#    Não definimos valores padrão aqui para as variáveis que esperamos do ambiente de produção.
#    Isso força o django-environ a procurar em os.environ ou no .env.
env = environ.Env()

# 2. Lendo o arquivo .env se existir (apenas para desenvolvimento local).
#    No Render, as variáveis de ambiente da plataforma terão precedência sobre este arquivo.
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
# A SECRET_KEY deve ser definida como uma variável de ambiente (DJANGO_SECRET_KEY).
# Em produção, a ausência desta variável irá levantar um erro, o que é o comportamento desejado.
# Para desenvolvimento local, defina-a no seu ficheiro .env.
SECRET_KEY = env('DJANGO_SECRET_KEY') # Removido o fallback padrão no código

# SECURITY WARNING: don't run with debug turned on in production!
# Força a leitura de DJANGO_DEBUG como booleano. Padrão False para produção.
DEBUG = env.bool('DJANGO_DEBUG', default=False)

# ALLOWED_HOSTS para produção e desenvolvimento.
# Em DEBUG=True, permite qualquer host para facilitar o desenvolvimento.
# Em DEBUG=False (produção), usa apenas os hosts definidos na variável de ambiente.
if DEBUG:
    ALLOWED_HOSTS = ['*'] # Permite qualquer host em desenvolvimento
else:
    # Em produção, obtenha hosts da variável de ambiente DJANGO_ALLOWED_HOSTS.
    # Adicionamos um fallback mais robusto para incluir 127.0.0.1 e localhost
    # caso a variável de ambiente não seja lida corretamente.
    allowed_hosts_from_env = env.list('DJANGO_ALLOWED_HOSTS', default=[])
    default_production_hosts = ['jecistore.onrender.com', '127.0.0.1', 'localhost']
    
    # Combina os hosts do ambiente com os hosts padrão de produção, removendo duplicatas
    ALLOWED_HOSTS = list(set(allowed_hosts_from_env + default_production_hosts))

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
# Configuração do banco de dados para usar DATABASE_URL.
# Removido 'conn_max_age' e 'options' da chamada env.db_url()
DATABASES = {
    'default': env.db_url('DATABASE_URL')
}

# Adiciona conn_max_age e OPTIONS (para client_encoding) após a inicialização
# do banco de dados pelo django-environ.
# Isso é necessário porque a versão 0.12.0 do django-environ não aceita esses argumentos
# diretamente no env.db_url().
DATABASES['default']['CONN_MAX_AGE'] = 600
DATABASES['default']['OPTIONS'] = {'client_encoding': 'UTF8'}


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
HANDLER404 = 'store.views.custom_404_view'
HANDLER500 = 'store.views.custom_500_view'

# Exemplo: Acessando a variável do WhatsApp (se for definida como env)
# Este valor será usado nas views e templates para o número de contato do WhatsApp
STORE_WHATSAPP_NUMBER = env('STORE_WHATSAPP_NUMBER', default='5511999999999')

# Alerta em produção se DEBUG estiver ativado (apenas para depuração no Render)
if not DEBUG:
    if 'runserver' not in sys.argv: # Não alerta em runserver local
        print("AVISO: DEBUG está DESATIVADO em ambiente de produção.", file=sys.stderr)
        print(f"ALLOWED_HOSTS: {ALLOWED_HOSTS}", file=sys.stderr) # Log para verificar
        try:
            db_host = DATABASES['default'].get('HOST', 'N/A')
            print(f"HOST DO BANCO DE DADOS: {db_host}", file=sys.stderr)
        except Exception as e:
            print(f"Erro ao obter HOST do DB para log: {e}", file=sys.stderr)

