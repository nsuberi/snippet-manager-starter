"""
API Tests for Snippet Manager

These tests verify that:
1. Read operations work without authentication
2. Write operations require valid HTTP Basic Authentication
3. Invalid/missing credentials are properly rejected

Run with: pytest test_api.py -v
"""

import base64
import pytest
from app import app, db
from models import Snippet, Tag, User


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


@pytest.fixture
def auth_headers(client):
    """Create and return auth headers for the test user."""
    with app.app_context():
        User.create("testuser", "testpass123")
    credentials = base64.b64encode(b"testuser:testpass123").decode('utf-8')
    return {'Authorization': f'Basic {credentials}'}


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


def basic_auth_header(username, password):
    """Create Basic Auth header for given credentials."""
    credentials = base64.b64encode(f"{username}:{password}".encode()).decode('utf-8')
    return {'Authorization': f'Basic {credentials}'}


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
# List Snippets Tests (Public - No Auth Required)
# ---------------------------------------------------------------------------

class TestListSnippets:
    """Test GET /api/snippets endpoint - public, no auth needed."""

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
# Get Single Snippet Tests (Public - No Auth Required)
# ---------------------------------------------------------------------------

class TestGetSnippet:
    """Test GET /api/snippets/<id> endpoint - public, no auth needed."""

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
# Create Snippet Tests (Auth Required)
# ---------------------------------------------------------------------------

class TestCreateSnippet:
    """Test POST /api/snippets endpoint - requires HTTP Basic Auth."""

    def test_create_snippet_with_valid_credentials(self, client, auth_headers):
        """Can create a snippet with valid credentials."""
        response = client.post('/api/snippets',
            headers=auth_headers,
            json={
                'title': 'New Snippet',
                'code': 'console.log("test");',
                'language': 'javascript'
            }
        )
        assert response.status_code == 201

        data = response.get_json()
        assert data['title'] == 'New Snippet'
        assert data['language'] == 'javascript'
        assert 'id' in data

    def test_create_snippet_with_tags(self, client, auth_headers):
        """Can create a snippet with tags."""
        response = client.post('/api/snippets',
            headers=auth_headers,
            json={
                'title': 'Tagged Snippet',
                'code': 'x = 1',
                'language': 'python',
                'tags': ['test', 'example']
            }
        )
        assert response.status_code == 201

        data = response.get_json()
        assert 'test' in data['tags']
        assert 'example' in data['tags']

    def test_create_snippet_without_auth_returns_401(self, client):
        """Creating a snippet without credentials returns 401."""
        response = client.post('/api/snippets', json={
            'title': 'No Auth',
            'code': 'test'
        })
        assert response.status_code == 401
        assert 'Authentication required' in response.get_json()['error']
        # Should include WWW-Authenticate header
        assert 'WWW-Authenticate' in response.headers

    def test_create_snippet_with_invalid_credentials_returns_401(self, client):
        """Creating a snippet with wrong password returns 401."""
        with app.app_context():
            User.create("testuser", "correctpassword")

        response = client.post('/api/snippets',
            headers=basic_auth_header("testuser", "wrongpassword"),
            json={
                'title': 'Bad Auth',
                'code': 'test'
            }
        )
        assert response.status_code == 401
        assert 'Invalid credentials' in response.get_json()['error']

    def test_create_snippet_with_nonexistent_user_returns_401(self, client):
        """Creating a snippet with non-existent user returns 401."""
        response = client.post('/api/snippets',
            headers=basic_auth_header("nobody", "password"),
            json={
                'title': 'No User',
                'code': 'test'
            }
        )
        assert response.status_code == 401
        assert 'Invalid credentials' in response.get_json()['error']

    def test_create_snippet_requires_title(self, client, auth_headers):
        """Creating a snippet without title returns 400."""
        response = client.post('/api/snippets',
            headers=auth_headers,
            json={'code': 'some code'}
        )
        assert response.status_code == 400
        assert 'Title is required' in response.get_json()['error']

    def test_create_snippet_requires_code(self, client, auth_headers):
        """Creating a snippet without code returns 400."""
        response = client.post('/api/snippets',
            headers=auth_headers,
            json={'title': 'No Code'}
        )
        assert response.status_code == 400
        assert 'Code is required' in response.get_json()['error']


# ---------------------------------------------------------------------------
# Update Snippet Tests (Auth Required)
# ---------------------------------------------------------------------------

class TestUpdateSnippet:
    """Test PUT /api/snippets/<id> endpoint - requires HTTP Basic Auth."""

    def test_update_snippet_with_valid_credentials(self, client, auth_headers):
        """Can update a snippet with valid credentials."""
        response = client.put('/api/snippets/1',
            headers=auth_headers,
            json={'title': 'Updated Title'}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['title'] == 'Updated Title'

    def test_update_snippet_partial(self, client, auth_headers):
        """Can update only specific fields."""
        # Get original
        original = client.get('/api/snippets/1').get_json()

        # Update only title
        response = client.put('/api/snippets/1',
            headers=auth_headers,
            json={'title': 'New Title Only'}
        )
        assert response.status_code == 200

        data = response.get_json()
        assert data['title'] == 'New Title Only'
        assert data['code'] == original['code']  # Unchanged

    def test_update_snippet_without_auth_returns_401(self, client):
        """Updating a snippet without credentials returns 401."""
        response = client.put('/api/snippets/1', json={
            'title': 'No Auth Update'
        })
        assert response.status_code == 401
        assert 'Authentication required' in response.get_json()['error']

    def test_update_snippet_with_invalid_credentials_returns_401(self, client):
        """Updating a snippet with invalid credentials returns 401."""
        with app.app_context():
            User.create("testuser", "realpass")

        response = client.put('/api/snippets/1',
            headers=basic_auth_header("testuser", "fakepass"),
            json={'title': 'Bad Auth'}
        )
        assert response.status_code == 401
        assert 'Invalid credentials' in response.get_json()['error']

    def test_update_nonexistent_snippet_returns_404(self, client, auth_headers):
        """Updating a non-existent snippet returns 404."""
        response = client.put('/api/snippets/9999',
            headers=auth_headers,
            json={'title': 'Does Not Exist'}
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Delete Snippet Tests (Auth Required)
# ---------------------------------------------------------------------------

class TestDeleteSnippet:
    """Test DELETE /api/snippets/<id> endpoint - requires HTTP Basic Auth."""

    def test_delete_snippet_with_valid_credentials(self, client, auth_headers):
        """Can delete a snippet with valid credentials."""
        # Create a snippet to delete
        create_response = client.post('/api/snippets',
            headers=auth_headers,
            json={
                'title': 'To Delete',
                'code': 'delete me'
            }
        )
        snippet_id = create_response.get_json()['id']

        # Delete it
        response = client.delete(f'/api/snippets/{snippet_id}',
            headers=auth_headers
        )
        assert response.status_code == 200
        assert 'deleted' in response.get_json()['message'].lower()

        # Verify it's gone
        get_response = client.get(f'/api/snippets/{snippet_id}')
        assert get_response.status_code == 404

    def test_delete_snippet_without_auth_returns_401(self, client):
        """Deleting a snippet without credentials returns 401."""
        response = client.delete('/api/snippets/1')
        assert response.status_code == 401
        assert 'Authentication required' in response.get_json()['error']

    def test_delete_snippet_with_invalid_credentials_returns_401(self, client):
        """Deleting a snippet with invalid credentials returns 401."""
        response = client.delete('/api/snippets/1',
            headers=basic_auth_header("fake", "creds")
        )
        assert response.status_code == 401

    def test_delete_nonexistent_snippet_returns_404(self, client, auth_headers):
        """Deleting a non-existent snippet returns 404."""
        response = client.delete('/api/snippets/9999',
            headers=auth_headers
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Languages & Tags Tests (Public - No Auth Required)
# ---------------------------------------------------------------------------

class TestLanguagesAndTags:
    """Test metadata endpoints - public, no auth needed."""

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
# Authentication Security Tests
# ---------------------------------------------------------------------------

class TestAuthenticationSecurity:
    """
    These tests verify that HTTP Basic Authentication is properly enforced.
    Write operations are protected while read operations remain public.
    """

    def test_read_operations_are_public(self, client):
        """GET endpoints work without authentication."""
        assert client.get('/api/snippets').status_code == 200
        assert client.get('/api/snippets/1').status_code == 200
        assert client.get('/api/languages').status_code == 200
        assert client.get('/api/tags').status_code == 200

    def test_write_operations_require_auth(self, client):
        """POST/PUT/DELETE endpoints require authentication."""
        assert client.post('/api/snippets', json={
            'title': 'Test', 'code': 'x'
        }).status_code == 401

        assert client.put('/api/snippets/1', json={
            'title': 'Test'
        }).status_code == 401

        assert client.delete('/api/snippets/1').status_code == 401

    def test_valid_credentials_grant_access(self, client, auth_headers):
        """Valid credentials allow write operations."""
        response = client.post('/api/snippets',
            headers=auth_headers,
            json={'title': 'Auth Test', 'code': 'pass'}
        )
        assert response.status_code == 201

    def test_inactive_user_is_rejected(self, client):
        """Deactivated users are rejected."""
        with app.app_context():
            user = User.create("inactive", "password")
            user.is_active = False
            db.session.commit()

        response = client.post('/api/snippets',
            headers=basic_auth_header("inactive", "password"),
            json={'title': 'Test', 'code': 'x'}
        )
        assert response.status_code == 401
        assert 'Invalid credentials' in response.get_json()['error']

    def test_malformed_auth_header_returns_401(self, client):
        """Malformed Authorization header returns 401."""
        # Not base64
        response = client.post('/api/snippets',
            headers={'Authorization': 'Basic not-base64!!!'},
            json={'title': 'Test', 'code': 'x'}
        )
        assert response.status_code == 401

        # Wrong auth type
        response = client.post('/api/snippets',
            headers={'Authorization': 'Bearer sometoken'},
            json={'title': 'Test', 'code': 'x'}
        )
        assert response.status_code == 401

    def test_password_is_hashed_in_database(self, client):
        """Passwords are stored hashed, not in plaintext."""
        with app.app_context():
            user = User.create("hashtest", "mysecretpassword")
            # Password should not be stored in plaintext
            assert user.password_hash != "mysecretpassword"
            assert len(user.password_hash) > 50  # Hash is much longer than password
            # But should still validate correctly
            assert user.check_password("mysecretpassword") is True
            assert user.check_password("wrongpassword") is False
