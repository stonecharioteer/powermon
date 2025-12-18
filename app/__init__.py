from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from celery import Celery
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize extensions
db = SQLAlchemy()


def make_celery(app):
    """Create and configure Celery instance"""
    celery = Celery(
        app.import_name,
        backend=app.config["CELERY_RESULT_BACKEND"],
        broker=app.config["CELERY_BROKER_URL"],
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)

    # Configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "postgresql://localhost/powermon"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
    app.config["CELERY_BROKER_URL"] = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    app.config["CELERY_RESULT_BACKEND"] = os.getenv(
        "REDIS_URL", "redis://localhost:6379/0"
    )

    # Initialize extensions
    db.init_app(app)

    # Register blueprints
    from app.main import bp as main_bp

    app.register_blueprint(main_bp)

    from app.api import bp as api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    # Create database tables
    with app.app_context():
        db.create_all()

    return app


# Create Celery instance
celery = make_celery(create_app())
