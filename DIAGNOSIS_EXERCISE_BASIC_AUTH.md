# Diagnosis Exercise: HTTP Basic Authentication

## The Symptom

The Snippet Manager API allows **anyone** to create, update, and delete code snippets without any authentication.

**Testing locally:**
```bash
# Anyone can create snippets - no credentials needed!
$ curl -X POST http://localhost:5001/api/snippets \
    -H "Content-Type: application/json" \
    -d '{"title": "Malicious", "code": "rm -rf /"}'

{
  "id": 11,
  "title": "Malicious",
  "code": "rm -rf /",
  ...
}
# ✅ Created! No authentication required.

# Anyone can delete snippets too
$ curl -X DELETE http://localhost:5001/api/snippets/1
{"message": "Snippet deleted successfully"}
# ✅ Deleted! Still no auth.
```

**The Problem:**
- Malicious users can spam the API with garbage snippets
- Anyone can vandalize or delete existing snippets
- There's no accountability for who made changes
- The API is open to automated abuse

**Starting Question: How do we protect write operations while keeping read operations public?**

---

## Diagnostic Framework: API Authentication Anatomy

Let's map the journey of a request through the system, identifying what needs to change and what stays the same.

### Layer 1: Data Models Layer ⚠️ (CHANGED)

**What's here:**
- `models.py` - SQLAlchemy models
- `Snippet` model - stores code snippets
- `Tag` model - categorizes snippets

**What changed:**
- Added `User` model for storing user credentials
- Passwords stored as secure hashes (never plaintext!)
- `is_active` field allows deactivating users
- `authenticate()` method for credential verification

**Key insight:** Authentication requires a place to store and verify identities. The User model is the foundation.

---

### Layer 2: Request Processing Layer ⚠️ (CHANGED)

**What's here:**
- `app.py` - Flask routes and request handling
- Route decorators (`@app.route`)
- Request/response processing

**What changed:**
- Added `require_basic_auth` decorator
- Decorator intercepts requests before route handlers
- Parses `Authorization: Basic` header
- Validates credentials against User model

**Key insight:** Python decorators are the perfect pattern for cross-cutting concerns like authentication—apply once, enforce everywhere.

---

### Layer 3: HTTP Protocol Layer ⚠️ (CHANGED)

**What's here:**
- HTTP headers (`Authorization`, `WWW-Authenticate`)
- Status codes (200, 401, 404)
- Request/response format

**What changed:**
- Write endpoints now require `Authorization: Basic <credentials>` header
- Failed auth returns 401 with `WWW-Authenticate` header (per HTTP spec)
- Credentials are base64-encoded `username:password`

**Key insight:** HTTP Basic Auth is a well-defined standard. Following the spec means clients (curl, browsers, libraries) know exactly how to authenticate.

---

### Layer 4: Route Handler Layer ✅ (UNCHANGED)

**What's here:**
- `create_snippet()` - POST /api/snippets
- `update_snippet()` - PUT /api/snippets/<id>
- `delete_snippet()` - DELETE /api/snippets/<id>
- `list_snippets()` - GET /api/snippets
- `get_snippet()` - GET /api/snippets/<id>

**Why it didn't break:**
- Route handlers don't know about authentication
- They just process validated requests
- Auth decorator handles auth BEFORE handlers run
- Clean separation of concerns

**Key insight:** The actual business logic doesn't change—only who can trigger it.

---

### Layer 5: Database Layer ✅ (UNCHANGED)

**What's here:**
- SQLite database (`snippets.db`)
- Snippet and Tag tables
- CRUD operations

**Why it didn't break:**
- Database doesn't care who sends queries
- Authentication happens at HTTP layer
- Database just stores and retrieves data

**Key insight:** Security boundaries should be enforced as early as possible in the request lifecycle.

---

## The Anatomical Fix

### What needs to change:

**1. Add User model for credential storage (`models.py`):**

```python
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    """User account for API authentication."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        """Hash and store the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify a password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def authenticate(username, password):
        """Authenticate a user by username and password."""
        user = User.query.filter_by(username=username, is_active=True).first()
        if user and user.check_password(password):
            return user
        return None
```

**What this does:**
- Stores usernames and password *hashes* (never plaintext!)
- Uses werkzeug's battle-tested password hashing
- `authenticate()` provides clean API for credential validation
- `is_active` allows disabling users without deleting them

---

**2. Add authentication decorator (`app.py`):**

```python
import base64
from functools import wraps

def require_basic_auth(f):
    """Decorator that requires HTTP Basic Authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')

        if not auth_header:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please provide credentials using HTTP Basic Authentication'
            }), 401, {'WWW-Authenticate': 'Basic realm="Snippet Manager API"'}

        # Parse Authorization header: "Basic base64(username:password)"
        try:
            auth_type, credentials = auth_header.split(' ', 1)
            if auth_type.lower() != 'basic':
                raise ValueError("Not Basic auth")

            decoded = base64.b64decode(credentials).decode('utf-8')
            username, password = decoded.split(':', 1)
        except (ValueError, UnicodeDecodeError):
            return jsonify({
                'error': 'Invalid authorization header'
            }), 401, {'WWW-Authenticate': 'Basic realm="Snippet Manager API"'}

        # Validate credentials
        user = User.authenticate(username, password)
        if not user:
            return jsonify({
                'error': 'Invalid credentials',
                'message': 'Username or password is incorrect'
            }), 401

        request.current_user = user
        return f(*args, **kwargs)

    return decorated
```

**What this does:**
- Intercepts requests before they reach route handlers
- Parses standard HTTP Basic Auth header format
- Validates credentials against User database
- Returns proper 401 response with `WWW-Authenticate` header
- Stores authenticated user in request context for route handlers

---

**3. Apply decorator to write endpoints (`app.py`):**

```python
@app.route('/api/snippets', methods=['POST'])
@require_basic_auth  # <-- Added
def create_snippet():
    ...

@app.route('/api/snippets/<int:snippet_id>', methods=['PUT'])
@require_basic_auth  # <-- Added
def update_snippet(snippet_id):
    ...

@app.route('/api/snippets/<int:snippet_id>', methods=['DELETE'])
@require_basic_auth  # <-- Added
def delete_snippet(snippet_id):
    ...
```

**What this does:**
- Single line per endpoint to enable authentication
- Read endpoints (GET) remain unprotected—intentionally public
- Decorators compose cleanly with existing route decorators

---

## Diagnosis Questions (for learners)

### Question 1: Why didn't the GET endpoints need the decorator?
**Answer:** The design decision is that reading snippets should be public—anyone can browse the code library. Only modifications (create, update, delete) need authentication because those are the actions that could cause harm.

### Question 2: Why store password hashes instead of passwords?
**Answer:** If the database is ever compromised (SQL injection, backup theft, etc.), attackers get hashes that can't easily be reversed. With plaintext passwords, one breach exposes all user credentials.

### Question 3: What would break WITHOUT the fix?
- Anyone could create spam snippets
- Anyone could modify or delete existing snippets
- No way to track who made changes
- Automated bots could abuse the API
- No accountability for actions

### Question 4: What WOULDN'T break even without the fix?
- Listing all snippets still works
- Getting individual snippets still works
- Filtering by language/tag still works
- Health check endpoint still works
- API documentation endpoint still works

### Question 5: Why use a decorator instead of checking auth inside each route?
**Answer:** DRY (Don't Repeat Yourself). The decorator:
- Eliminates duplicated auth code in every protected route
- Can't be forgotten when adding new endpoints (just add `@require_basic_auth`)
- Separates auth logic from business logic
- Makes it easy to change auth strategy later

---

## The Pattern: What This Teaches

### Core Concepts:

1. **Security Boundaries**
   - Protect at the earliest point in the request lifecycle
   - Don't trust that internal code won't be reached by attackers
   - Authentication happens before business logic

2. **Password Security**
   - Never store plaintext passwords
   - Use established libraries (werkzeug, bcrypt, argon2)
   - One-way hashing means even admins can't see passwords

3. **HTTP Authentication Standards**
   - Basic Auth: `Authorization: Basic base64(user:pass)`
   - 401 responses should include `WWW-Authenticate` header
   - Following standards means better client compatibility

4. **Decorator Pattern**
   - Cross-cutting concerns (auth, logging, timing) use decorators
   - Single point of change for security policy
   - Clean separation from business logic

### Diagnostic Skill Building:

**When an API has no authentication, ask:**
1. What operations should be public vs. protected?
2. What's the threat model? (spam, vandalism, data theft)
3. What auth method fits the use case? (API key, Basic Auth, OAuth, JWT)
4. Where in the request lifecycle should auth be enforced?
5. How are credentials stored securely?

---

## Practice Exercise

**Given this error:** "A competitor is scraping all our premium content via the API"

**Walk through:**
1. Which layer is this happening in? (HTTP/Route layer - no access control)
2. What's working? (API serves data correctly)
3. What's the gap? (No distinction between public and premium content)
4. What auth strategy fits? (API key for premium access, or user-based auth)
5. What's the minimal fix? (Add auth decorator to premium endpoints)

---

## HTTP Basic Auth vs. API Key: A Comparison

| Aspect | HTTP Basic Auth | API Key |
|--------|----------------|---------|
| **Header** | `Authorization: Basic <base64>` | `X-API-Key: <key>` |
| **Credentials** | Username + Password | Single key string |
| **User Identity** | Yes - tied to user account | Optional - key can represent user or app |
| **Revocation** | Change password or deactivate user | Delete/regenerate key |
| **Browser Support** | Native (login dialog) | None (requires custom header) |
| **curl Usage** | `curl -u user:pass` | `curl -H "X-API-Key: key"` |

### When to use HTTP Basic Auth:
- User-facing APIs where identity matters
- When you want browser native auth dialogs
- When users already have accounts
- When audit trails need to track individual users

### When to use API Keys:
- Machine-to-machine communication
- Service integrations
- When you want easy key rotation
- When one key might represent a team/org, not individual

### Security Considerations:
- **Both** require HTTPS in production (credentials in headers)
- **Basic Auth** sends credentials every request (no token expiry)
- **API Keys** are easier to accidentally leak (often in URLs, logs)
- **Both** can be rate-limited per credential
