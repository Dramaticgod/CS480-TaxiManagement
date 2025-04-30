from flask import Flask, session
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_alembic import Alembic
from flask_executor import Executor
from flask_admin.contrib.sqla import ModelView
from flask_wtf.csrf import CSRFProtect, generate_csrf
from passlib.hash import sha256_crypt
from flask_login import LoginManager
from itsdangerous import URLSafeTimedSerializer, SignatureExpired
from functools import wraps
from datetime import timedelta
import logging
import os
from dotenv import load_dotenv


load_dotenv()


application = Flask(__name__, static_folder='static')
app = application


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + 'TaxiDB.db'

app.config.update(
    SQLALCHEMY_ENGINE_OPTIONS={
        'pool_size': 3,  # Small pool size
        'max_overflow': 5,
        'pool_timeout': 20,
        'pool_recycle': 280,
        'pool_pre_ping': True
    },
    SQLALCHEMY_TRACK_MODIFICATIONS = False,  
    TEMPLATES_AUTO_RELOAD = False,  
    PERMANENT_SESSION_LIFETIME = timedelta(days=7),
    SESSION_COOKIE_SECURE = True,
    SESSION_COOKIE_HTTPONLY = True,
    SECRET_KEY=os.getenv('SECRET_KEY'),
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_PROTECTION='strong',
    SESSION_REFRESH_EACH_REQUEST=True
)

app.config['WTF_CSRF_ENABLED'] = True


hidden_key = URLSafeTimedSerializer(app.config['SECRET_KEY'])
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


logging.basicConfig(level=logging.DEBUG)


db = SQLAlchemy(app)
csrf = CSRFProtect(app)
alembic = Alembic(app)
app.app_context().push()

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'danger'

from application import routes