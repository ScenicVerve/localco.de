import os
#import djcelery
#djcelery.setup_loader()

path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


#my_path = '/Users/carlos/projects/open-reblock' # Change this to the local path
#my_path = '/Users/eleannapanagoulia/Documents/open-reblock' # Change this to the local path
my_path = '/home/pwz/open-reblock' # Change this to the local path



if path == my_path: # If i'm running it locally
    from mysettings import *

else: # If i'm running it on the server
    # Django settings for localcode project.
    import os
    from pw import PW

    DEBUG = False
    TEMPLATE_DEBUG = DEBUG
    
    ADMINS = (
            ('Nicholas de Monchaux', 'demonchaux@berkeley.edu'),
            ('Benjamin Golder', 'benjamin.j.golder@gmail.com'),
            ('Carlos Sandoval', 'ce.sandoval@berkeley.edu'),
    )  
    
    MANAGERS = ADMINS
    
    DATABASES = {
        'default': {
            'ENGINE': 'django.contrib.gis.db.backends.postgis',  ## Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': 'localcode',                      # Or path to database file if using sqlite3.
            'USER': 'localcode',                      # Not used with sqlite3.
            'PASSWORD': PW,                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }
    
    # Local time zone for this installation. Choices can be found here:
    # http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
    # although not all choices may be available on all operating systems.
    # On Unix systems, a value of None will cause Django to use the same
    # timezone as the operating system.
    # If running in a Windows environment this must be set to the same as your
    # system time zone.
    TIME_ZONE = None
    
    # Language code for this installation. All choices can be found here:
    # http://www.i18nguy.com/unicode/language-identifiers.html
    LANGUAGE_CODE = 'en-us'
    
    SITE_ID = 1
    
    # If you set this to False, Django will make some optimizations so as not
    # to load the internationalization machinery.
    USE_I18N = True
    
    # If you set this to False, Django will not format dates, numbers and
    # calendars according to the current locale
    USE_L10N = True
    
    # Absolute filesystem path to the directory that will hold user-uploaded files.
    # Example: "/home/media/media.lawrence.com/media/"
    #MEDIA_ROOT = '/Library/WebServer/Documents/media/localcode/' # LOCAL DEVELOPMENT
    #MEDIA_ROOT = '/home/localcode/webapps/media' # WEBFACTION DEPLOYMENT
    MEDIA_ROOT = '/var/www/openreblock.berkeley.edu/media' # Berkeley Server
    
    # URL that handles the media served from MEDIA_ROOT. Make sure to use a
    # trailing slash.
    # Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
    #MEDIA_URL = 'http://localhost/media/localcode/'
    MEDIA_URL = 'http://openreblock.berkeley.edu/media/' # Berkeley Server
    
    
    # Absolute path to the directory static files should be collected to.
    # Don't put anything in this directory yourself; store your static files
    # in apps' "static/" subdirectories and in STATICFILES_DIRS.
    # Example: "/home/media/media.lawrence.com/static/"
    #STATIC_ROOT = '/Library/WebServer/Documents/static/localcode/' # LOCAL DEVELOPMENT
    #STATIC_ROOT = '/home/localcode/webapps/static' # WEBFACTION DEPLOYMENT
    STATIC_ROOT = '/var/www/openreblock.berkeley.edu/localcode/static' # Berkeley DEVELOPMENT
    
    
    # URL prefix for static files.
    # Example: "http://media.lawrence.com/static/"
    STATIC_URL = '/static/'
    
    # URL prefix for admin static files -- CSS, JavaScript and images.
    # Make sure to use a trailing slash.
    # Examples: "http://foo.com/static/admin/", "/static/admin/".
    ADMIN_MEDIA_PREFIX = '/static/admin/'
    
    # URL of the login page.
    LOGIN_URL = '/login/'
    # Unique.
    SECRET_KEY = 'localcode'
    
    # Additional locations of static files
    STATICFILES_DIRS = (
            os.path.join(os.path.abspath(os.path.dirname(__file__)), 'static'),
        # Put strings here, like "/home/html/static" or "C:/www/django/static".
        # Always use forward slashes, even on Windows.
        # Don't forget to use absolute paths, not relative paths.
    )
    
    # List of finder classes that know how to find static files in
    # various locations.
    STATICFILES_FINDERS = (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
        #'django.contrib.staticfiles.finders.DefaultStorageFinder',
    )
    
    # Make this unique, and don't share it with anybody.
    SECRET_KEY = ')_xt_9_edjdr*cr--!3ip%a)crjrcbks@lo8=_1!=p=sx6cpe!'
    
    # List of callables that know how to import templates from various sources.
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    #     'django.template.loaders.eggs.Loader',
    )
    
    TEMPLATE_CONTEXT_PROCESSORS = (
        'django.core.context_processors.debug',
        'django.core.context_processors.i18n',
        'django.core.context_processors.media',
        'django.core.context_processors.static',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    )
    
    MIDDLEWARE_CLASSES = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
        'django.contrib.messages.middleware.MessageMiddleware',
    )
    
    ROOT_URLCONF = 'localcode.urls'
    
    TEMPLATE_DIRS = (
        # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
        # Always use forward slashes, even on Windows.
        # Don't forget to use absolute paths, not relative paths.
            os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates'),
            
    )
    
    INSTALLED_APPS = (
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.sites',
        'django.contrib.messages',
        'django.contrib.staticfiles',
        'django.contrib.admin',
        'django.contrib.admindocs',
        'django.contrib.webdesign',
        'django.contrib.humanize',
        'textbits',
        'topology',
        'django.contrib.contenttypes',
        'django.contrib.gis',
        #'celery',
        'djcelery',
        'reblock',
        
    )
    
    AUTH_PROFILE_MODULE = 'reblock.UserProfile'
    ACCOUNT_ACTIVATION_DAYS = 2 # Any value. 
    EMAIL_HOST='localhost' #'smtp.gmail.com'
    EMAIL_PORT=587
    EMAIL_HOST_USER='user@example.com'
    EMAIL_HOST_PASSWORD='secret'
    
    # A sample logging configuration. The only tangible logging
    # performed by this configuration is to send an email to
    # the site admins on every HTTP 500 error.
    # See http://docs.djangoproject.com/en/dev/topics/logging for
    # more details on how to customize your logging configuration.
    LOGGING = {
        'version': 1,
        'disable_existing_loggers': False,
        'handlers': {
            'mail_admins': {
                'level': 'ERROR',
                'class': 'django.utils.log.AdminEmailHandler'
            }
        },
        'loggers': {
            'django.request': {
                'handlers': ['mail_admins'],
                'level': 'ERROR',
                'propagate': True,
            },
        }
    }

