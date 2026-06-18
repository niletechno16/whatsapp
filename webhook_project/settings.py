
SECRET_KEY='dev-secret-key'
DEBUG=True
ALLOWED_HOSTS=['*']
ROOT_URLCONF='webhook_project.urls'
INSTALLED_APPS=[
    'django.contrib.contenttypes',
    'django.contrib.auth',
]
MIDDLEWARE=[]
DATABASES={'default':{'ENGINE':'django.db.backends.sqlite3','NAME':'db.sqlite3'}}
WSGI_APPLICATION='webhook_project.wsgi.application'
