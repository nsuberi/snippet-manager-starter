import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Application configuration."""

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'DATABASE_URL',
        f'sqlite:///{os.path.join(basedir, "snippets.db")}'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'

    # API Settings
    MAX_SNIPPET_SIZE = 50000  # Maximum code length in characters
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
