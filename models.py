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
