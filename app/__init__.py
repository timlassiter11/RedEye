from config import Config
from flask import Flask, render_template
from flask_login import LoginManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_msearch import Search
from werkzeug.exceptions import HTTPException

db = SQLAlchemy()
migrate = Migrate()
login = LoginManager()
mail = Mail()
search = Search()


def create_app(config_class=Config) -> "Flask":
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.config['TRAP_HTTP_EXCEPTIONS'] = True

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    search.init_app(app)

    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp)

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    from app.admin import bp as admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.agent import bp as agent_bp
    app.register_blueprint(agent_bp, url_prefix='/agent')

    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.errorhandler(HTTPException)
    def handle_error(error):
        code = error.code
        return render_template(
            'error.html',
            error_text=error.name,
            error_code=code
        ), code

    return app

from app import models
