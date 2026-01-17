"""
API Tests for Snippet Manager

These tests demonstrate that all API endpoints work without authentication.
Run with: pytest test_api.py -v
"""

import pytest
from app import app, db
from models import Snippet, Tag


@pytest.fixture
def client():
    """Create a test client with a fresh database for each test."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.drop_all()
        db.create_all()
        _seed_test_data()

        with app.test_client() as client:
            yield client

        db.session.remove()
        db.drop_all()


def _seed_test_data():
    """Add minimal test data."""
    tag_python = Tag(name='python')
    tag_utility = Tag(name='utility')
    db.session.add_all([tag_python, tag_utility])

    snippet = Snippet(
        title='Hello World',
        code='print("Hello, World!")',
        language='python',
        description='A simple greeting'
    )
    snippet.tags.append(tag_python)
    db.session.add(snippet)
    db.session.commit()


# ---------------------------------------------------------------------------
# Health Check Tests
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Test health and info endpoints."""

    def test_index_returns_api_info(self, client):
        """GET / returns API information."""
        response = client.get('/')
        assert response.status_code == 200

        data = response.get_json()
        assert data['name'] == 'Snippet Manager API'
        assert 'endpoints' in data

    def test_health_check(self, client):
        """GET /health returns healthy status."""
        response = client.get('/health')
        assert response.status_code == 200
        assert response.get_json()['status'] == 'healthy'


# ---------------------------------------------------------------------------
# List Snippets Tests
# ---------------------------------------------------------------------------

class TestListSnippets:
    """Test GET /api/snippets endpoint."""

    def test_list_snippets_no_auth_required(self, client):
        """Anyone can list snippets without authentication."""
        response = client.get('/api/snippets')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_list_snippets_returns_snippet_data(self, client):
        """Listed snippets include all expected fields."""
        response = client.get('/api/snippets')
        data = response.get_json()

        snippet = data[0]
        assert 'id' in snippet
        assert 'title' in snippet
        assert 'code' in snippet
        assert 'language' in snippet
        assert 'tags' in snippet
        assert 'created_at' in snippet

    def test_filter_by_language(self, client):
        """Can filter snippets by language."""
        response = client.get('/api/snippets?language=python')
        assert response.status_code == 200

        data = response.get_json()
        for snippet in data:
            assert snippet['language'] == 'python'

    def test_filter_by_tag(self, client):
        """Can filter snippets by tag."""
        response = client.get('/api/snippets?tag=python')
        assert response.status_code == 200

        data = response.get_json()
        for snippet in data:
            assert 'python' in snippet['tags']


# ---------------------------------------------------------------------------
# Get Single Snippet Tests
# ---------------------------------------------------------------------------

class TestGetSnippet:
    """Test GET /api/snippets/<id> endpoint."""

    def test_get_snippet_no_auth_required(self, client):
        """Anyone can get a snippet without authentication."""
        response = client.get('/api/snippets/1')
        assert response.status_code == 200

        data = response.get_json()
        assert data['id'] == 1
        assert data['title'] == 'Hello World'

    def test_get_nonexistent_snippet_returns_404(self, client):
        """Getting a non-existent snippet returns 404."""
        response = client.get('/api/snippets/9999')
        assert response.status_code == 404
        assert 'error' in response.get_json()


# ---------------------------------------------------------------------------
# Create Snippet Tests
# ---------------------------------------------------------------------------

class TestCreateSnippet:
    """Test POST /api/snippets endpoint."""

    def test_create_snippet_no_auth_required(self, client):
        """Anyone can create a snippet without authentication."""
        response = client.post('/api/snippets', json={
            'title': 'New Snippet',
            'code': 'console.log("test");',
            'language': 'javascript'
        })
        assert response.status_code == 201

        data = response.get_json()
        assert data['title'] == 'New Snippet'
        assert data['language'] == 'javascript'
        assert 'id' in data

    def test_create_snippet_with_tags(self, client):
        """Can create a snippet with tags."""
        response = client.post('/api/snippets', json={
            'title': 'Tagged Snippet',
            'code': 'x = 1',
            'language': 'python',
            'tags': ['test', 'example']
        })
        assert response.status_code == 201

        data = response.get_json()
        assert 'test' in data['tags']
        assert 'example' in data['tags']

    def test_create_snippet_requires_title(self, client):
        """Creating a snippet without title returns 400."""
        response = client.post('/api/snippets', json={
            'code': 'some code'
        })
        assert response.status_code == 400
        assert 'Title is required' in response.get_json()['error']

    def test_create_snippet_requires_code(self, client):
        """Creating a snippet without code returns 400."""
        response = client.post('/api/snippets', json={
            'title': 'No Code'
        })
        assert response.status_code == 400
        assert 'Code is required' in response.get_json()['error']


# ---------------------------------------------------------------------------
# Update Snippet Tests
# ---------------------------------------------------------------------------

class TestUpdateSnippet:
    """Test PUT /api/snippets/<id> endpoint."""

    def test_update_snippet_no_auth_required(self, client):
        """Anyone can update a snippet without authentication."""
        response = client.put('/api/snippets/1', json={
            'title': 'Updated Title'
        })
        assert response.status_code == 200

        data = response.get_json()
        assert data['title'] == 'Updated Title'

    def test_update_snippet_partial(self, client):
        """Can update only specific fields."""
        # Get original
        original = client.get('/api/snippets/1').get_json()

        # Update only title
        response = client.put('/api/snippets/1', json={
            'title': 'New Title Only'
        })
        assert response.status_code == 200

        data = response.get_json()
        assert data['title'] == 'New Title Only'
        assert data['code'] == original['code']  # Unchanged

    def test_update_nonexistent_snippet_returns_404(self, client):
        """Updating a non-existent snippet returns 404."""
        response = client.put('/api/snippets/9999', json={
            'title': 'Does Not Exist'
        })
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete Snippet Tests
# ---------------------------------------------------------------------------

class TestDeleteSnippet:
    """Test DELETE /api/snippets/<id> endpoint."""

    def test_delete_snippet_no_auth_required(self, client):
        """Anyone can delete a snippet without authentication."""
        # Create a snippet to delete
        create_response = client.post('/api/snippets', json={
            'title': 'To Delete',
            'code': 'delete me'
        })
        snippet_id = create_response.get_json()['id']

        # Delete it
        response = client.delete(f'/api/snippets/{snippet_id}')
        assert response.status_code == 200
        assert 'deleted' in response.get_json()['message'].lower()

        # Verify it's gone
        get_response = client.get(f'/api/snippets/{snippet_id}')
        assert get_response.status_code == 404

    def test_delete_nonexistent_snippet_returns_404(self, client):
        """Deleting a non-existent snippet returns 404."""
        response = client.delete('/api/snippets/9999')
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Languages & Tags Tests
# ---------------------------------------------------------------------------

class TestLanguagesAndTags:
    """Test metadata endpoints."""

    def test_list_languages_no_auth_required(self, client):
        """Anyone can list languages without authentication."""
        response = client.get('/api/languages')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert 'python' in data

    def test_list_tags_no_auth_required(self, client):
        """Anyone can list tags without authentication."""
        response = client.get('/api/tags')
        assert response.status_code == 200

        data = response.get_json()
        assert isinstance(data, list)
        assert any(tag['name'] == 'python' for tag in data)


# ---------------------------------------------------------------------------
# Security Concern Demonstration
# ---------------------------------------------------------------------------

class TestNoAuthenticationRequired:
    """
    These tests explicitly demonstrate that NO authentication is required.
    This is the security gap that students will fix by adding API key auth.
    """

    def test_can_read_all_data_without_auth(self, client):
        """Anyone can read all snippets - no auth headers needed."""
        response = client.get('/api/snippets')
        assert response.status_code == 200
        # No Authorization header, no API key, nothing - still works!

    def test_can_create_data_without_auth(self, client):
        """Anyone can create snippets - potential spam/abuse vector."""
        response = client.post('/api/snippets', json={
            'title': 'Anonymous Creation',
            'code': 'anyone can add this'
        })
        assert response.status_code == 201
        # No way to track who created this!

    def test_can_modify_data_without_auth(self, client):
        """Anyone can modify any snippet - no ownership checks."""
        response = client.put('/api/snippets/1', json={
            'title': 'Vandalized!'
        })
        assert response.status_code == 200
        # Anyone can modify anyone's snippets!

    def test_can_delete_data_without_auth(self, client):
        """Anyone can delete any snippet - destructive action unprotected."""
        # Create then delete
        create = client.post('/api/snippets', json={
            'title': 'Temporary',
            'code': 'x'
        })
        snippet_id = create.get_json()['id']

        response = client.delete(f'/api/snippets/{snippet_id}')
        assert response.status_code == 200
        # Anyone can delete anything!
