"""
Snippet Manager API

A simple REST API for storing and sharing code snippets.
Requires API key authentication for write operations.
"""

from functools import wraps
from flask import Flask, request, jsonify
from config import Config
from models import db, Snippet, Tag, ApiKey, get_or_create_tag

app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def require_api_key(f):
    """
    Decorator that requires a valid API key for the endpoint.

    API key should be provided in the X-API-Key header.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')

        if not api_key:
            return jsonify({
                'error': 'API key required',
                'message': 'Please provide an API key in the X-API-Key header'
            }), 401

        key_obj = ApiKey.validate(api_key)
        if not key_obj:
            return jsonify({
                'error': 'Invalid API key',
                'message': 'The provided API key is invalid or inactive'
            }), 401

        # Store the validated key in request context for potential use
        request.api_key = key_obj
        return f(*args, **kwargs)

    return decorated


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """API welcome message and basic info."""
    return jsonify({
        'name': 'Snippet Manager API',
        'version': '1.0.0',
        'endpoints': {
            'snippets': '/api/snippets',
            'languages': '/api/languages',
            'tags': '/api/tags',
        }
    })


@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


# ---------------------------------------------------------------------------
# Snippet Endpoints
# ---------------------------------------------------------------------------

@app.route('/api/snippets', methods=['GET'])
def list_snippets():
    """
    List all snippets with optional filtering.

    Query parameters:
    - language: Filter by programming language
    - tag: Filter by tag name
    """
    query = Snippet.query

    # Filter by language
    language = request.args.get('language')
    if language:
        query = query.filter(Snippet.language.ilike(language))

    # Filter by tag
    tag_name = request.args.get('tag')
    if tag_name:
        query = query.join(Snippet.tags).filter(Tag.name.ilike(tag_name))

    # Order by most recent first
    snippets = query.order_by(Snippet.created_at.desc()).all()

    return jsonify([snippet.to_dict() for snippet in snippets])


@app.route('/api/snippets/<int:snippet_id>', methods=['GET'])
def get_snippet(snippet_id):
    """Get a single snippet by ID."""
    snippet = Snippet.query.get(snippet_id)

    if not snippet:
        return jsonify({'error': 'Snippet not found'}), 404

    return jsonify(snippet.to_dict())


@app.route('/api/snippets', methods=['POST'])
@require_api_key
def create_snippet():
    """
    Create a new snippet.

    Required fields:
    - title: Snippet title
    - code: The code content

    Optional fields:
    - language: Programming language (default: 'plaintext')
    - description: Description of the snippet
    - tags: List of tag names
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    # Validate required fields
    if not data.get('title'):
        return jsonify({'error': 'Title is required'}), 400

    if not data.get('code'):
        return jsonify({'error': 'Code is required'}), 400

    # Check code size limit
    if len(data['code']) > Config.MAX_SNIPPET_SIZE:
        return jsonify({
            'error': f'Code exceeds maximum size of {Config.MAX_SNIPPET_SIZE} characters'
        }), 400

    # Create snippet
    snippet = Snippet(
        title=data['title'].strip(),
        code=data['code'],
        language=data.get('language', 'plaintext').lower().strip(),
        description=data.get('description', '').strip() or None
    )

    # Handle tags
    if data.get('tags'):
        for tag_name in data['tags']:
            if tag_name and isinstance(tag_name, str):
                tag = get_or_create_tag(tag_name)
                snippet.tags.append(tag)

    db.session.add(snippet)
    db.session.commit()

    return jsonify(snippet.to_dict()), 201


@app.route('/api/snippets/<int:snippet_id>', methods=['PUT'])
@require_api_key
def update_snippet(snippet_id):
    """
    Update an existing snippet.

    All fields are optional - only provided fields will be updated.
    """
    snippet = Snippet.query.get(snippet_id)

    if not snippet:
        return jsonify({'error': 'Snippet not found'}), 404

    data = request.get_json()

    if not data:
        return jsonify({'error': 'Request body must be JSON'}), 400

    # Update fields if provided
    if 'title' in data:
        snippet.title = data['title'].strip()

    if 'code' in data:
        if len(data['code']) > Config.MAX_SNIPPET_SIZE:
            return jsonify({
                'error': f'Code exceeds maximum size of {Config.MAX_SNIPPET_SIZE} characters'
            }), 400
        snippet.code = data['code']

    if 'language' in data:
        snippet.language = data['language'].lower().strip()

    if 'description' in data:
        snippet.description = data['description'].strip() or None

    # Update tags if provided
    if 'tags' in data:
        snippet.tags.clear()
        for tag_name in data['tags']:
            if tag_name and isinstance(tag_name, str):
                tag = get_or_create_tag(tag_name)
                snippet.tags.append(tag)

    db.session.commit()

    return jsonify(snippet.to_dict())


@app.route('/api/snippets/<int:snippet_id>', methods=['DELETE'])
@require_api_key
def delete_snippet(snippet_id):
    """Delete a snippet."""
    snippet = Snippet.query.get(snippet_id)

    if not snippet:
        return jsonify({'error': 'Snippet not found'}), 404

    db.session.delete(snippet)
    db.session.commit()

    return jsonify({'message': 'Snippet deleted successfully'})


# ---------------------------------------------------------------------------
# Language & Tag Endpoints
# ---------------------------------------------------------------------------

@app.route('/api/languages', methods=['GET'])
def list_languages():
    """Get list of all languages used in snippets."""
    languages = db.session.query(Snippet.language).distinct().order_by(Snippet.language).all()
    return jsonify([lang[0] for lang in languages])


@app.route('/api/tags', methods=['GET'])
def list_tags():
    """Get list of all tags with snippet counts."""
    tags = Tag.query.all()
    return jsonify([tag.to_dict() for tag in tags])


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

@app.errorhandler(400)
def bad_request(error):
    return jsonify({'error': 'Bad request'}), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=Config.DEBUG, port=5001)
