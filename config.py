import os
from dotenv import load_dotenv
from distutils.util import strtobool

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config(object):
    SECRET_KEY = os.environ.get('SECRET_KEY') or '1069aa45fee63a513706f9abf3ac95dba04b4ee4971474cd'
    WTF_CSRF_ENABLED = bool(strtobool(os.environ.get('CSRF_ENABLED', 'True')))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    MAIL_DEFAULT_SENDER  = "RedEye <no-reply@workoutbuddy.app>"
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_SSL = bool(strtobool(os.environ.get('MAIL_USE_SSL', 'False')))
    MAIL_USE_TLS = bool(strtobool(os.environ.get('MAIL_USE_TLS', 'True')))
    GOOGLE_MAPS_KEY = os.environ.get('GOOGLE_MAPS_KEY')
    MSEARCH_BACKEND = 'whoosh'
    # auto create or update index
    MSEARCH_ENABLE = True
    SESSION_COOKIE_DOMAIN = False
    REMEMBER_COOKIE_DOMAIN = None
    # Fix for MySQL connection timeout  
    SQLALCHEMY_POOL_RECYCLE = 280
    