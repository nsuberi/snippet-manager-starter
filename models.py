import secrets
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# Association table for snippet tags (many-to-many)
snippet_tags = db.Table(
    'snippet_tags',
    db.Column('snippet_id', db.Integer, db.ForeignKey('snippets.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id'), primary_key=True)
)


class Snippet(db.Model):
    """A code snippet with metadata."""

    __tablename__ = 'snippets'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    code = db.Column(db.Text, nullable=False)
    language = db.Column(db.String(50), nullable=False, default='plaintext')
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tags = db.relationship('Tag', secondary=snippet_tags, backref=db.backref('snippets', lazy='dynamic'))

    def to_dict(self):
        """Convert snippet to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'title': self.title,
            'code': self.code,
            'language': self.language,
            'description': self.description,
            'tags': [tag.name for tag in self.tags],
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'updated_at': self.updated_at.isoformat() + 'Z' if self.updated_at else None,
        }

    def __repr__(self):
        return f'<Snippet {self.id}: {self.title}>'


class Tag(db.Model):
    """A tag for categorizing snippets."""

    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self):
        """Convert tag to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'name': self.name,
            'snippet_count': self.snippets.count()
        }

    def __repr__(self):
        return f'<Tag {self.name}>'


def get_or_create_tag(name):
    """Get existing tag or create new one."""
    tag = Tag.query.filter_by(name=name.lower().strip()).first()
    if not tag:
        tag = Tag(name=name.lower().strip())
        db.session.add(tag)
    return tag


class ApiKey(db.Model):
    """API key for authenticating requests."""

    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)  # Description of key owner/purpose
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def generate_key():
        """Generate a secure random API key."""
        return secrets.token_hex(32)

    @staticmethod
    def create(name):
        """Create a new API key with the given name."""
        api_key = ApiKey(
            key=ApiKey.generate_key(),
            name=name
        )
        db.session.add(api_key)
        db.session.commit()
        return api_key

    @staticmethod
    def validate(key):
        """Validate an API key and return the ApiKey object if valid."""
        if not key:
            return None
        api_key = ApiKey.query.filter_by(key=key, is_active=True).first()
        if api_key:
            api_key.last_used_at = datetime.utcnow()
            db.session.commit()
        return api_key

    def to_dict(self):
        """Convert to dictionary (excludes full key for security)."""
        return {
            'id': self.id,
            'name': self.name,
            'key_preview': self.key[:8] + '...',
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'last_used_at': self.last_used_at.isoformat() + 'Z' if self.last_used_at else None,
        }

    def __repr__(self):
        return f'<ApiKey {self.name}>'
