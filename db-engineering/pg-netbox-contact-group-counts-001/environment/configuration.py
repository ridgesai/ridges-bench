ALLOWED_HOSTS = ['localhost', 'testserver']
SECRET_KEY = 'solver-visible-development-secret-0000000000000000000000000000'
API_TOKEN_PEPPERS = {1: 'solver-visible-development-pepper-000000000000000000000000000'}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'netbox_dev',
        'USER': 'solver',
        'PASSWORD': 'solver-development-35d886f2',
        'HOST': 'postgres',
        'PORT': 5432,
        'TEST': {'NAME': 'netbox_test'},
    }
}

REDIS = {
    'tasks': {
        'HOST': 'redis', 'PORT': 6379, 'USERNAME': 'solver',
        'PASSWORD': 'redis-solver-visible-250583cf', 'DATABASE': 0,
    },
    'caching': {
        'HOST': 'redis', 'PORT': 6379, 'USERNAME': 'solver',
        'PASSWORD': 'redis-solver-visible-250583cf', 'DATABASE': 1,
    },
}

RELEASE_CHECK_URL = None
