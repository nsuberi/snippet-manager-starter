# Diagnosis Exercise: Securing a Flask API with API Key Authentication

## The Symptom

You've deployed the Snippet Manager API and it's working great—users can browse code snippets, filter by language, and view individual snippets. But then you notice something alarming in your logs:

**What you expected:**
```bash
$ curl -X POST http://localhost:5001/api/snippets \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "code": "print(1)"}'

# Should require authentication...
{"error": "Unauthorized"}
```

**What actually happens:**
```bash
$ curl -X POST http://localhost:5001/api/snippets \
  -H "Content-Type: application/json" \
  -d '{"title": "SPAM SPAM SPAM", "code": "malicious_code()"}'

# Anyone can create snippets!
{
  "id": 11,
  "title": "SPAM SPAM SPAM",
  "code": "malicious_code()",
  "language": "plaintext",
  ...
}
```

Even worse:
```bash
# Anyone can delete ALL your data!
$ curl -X DELETE http://localhost:5001/api/snippets/1
{"message": "Snippet deleted successfully"}

$ curl -X DELETE http://localhost:5001/api/snippets/2
{"message": "Snippet deleted successfully"}
```

The tests explicitly demonstrate this vulnerability:

```python
class TestNoAuthenticationRequired:
    def test_can_create_data_without_auth(self, client):
        """Anyone can create snippets - potential spam/abuse vector."""
        response = client.post('/api/snippets', json={
            'title': 'Anonymous Creation',
            'code': 'anyone can add this'
        })
        assert response.status_code == 201  # This passes! No auth needed!
```

**Starting Question: How do we protect write operations while keeping read operations public?**

---

## Diagnostic Framework: REST API Security Anatomy

Let's map the journey of an HTTP request through the system, identifying what needs protection and what doesn't.

### Layer 1: HTTP Request Layer ✅ (UNCHANGED)

**What's here:**
- Incoming HTTP requests (GET, POST, PUT, DELETE)
- Request headers, body, query parameters
- Flask's request routing

**Why it didn't need to change:**
- HTTP methods work correctly—they're just not being protected
- The routing (`@app.route`) correctly maps URLs to handlers
- Request parsing and JSON handling work fine

**Key insight:** The transport layer is doing its job. The problem is what happens *after* the request arrives.

---

### Layer 2: Route Handlers 🔴 (NEEDS PROTECTION)

**What's here:**
- `create_snippet()` - POST /api/snippets
- `update_snippet()` - PUT /api/snippets/<id>
- `delete_snippet()` - DELETE /api/snippets/<id>
- `list_snippets()` - GET /api/snippets
- `get_snippet()` - GET /api/snippets/<id>

**The problem:**
- Write operations (POST, PUT, DELETE) execute immediately
- No check for "who is making this request?"
- No gatekeeper between the route and the business logic

**Before (vulnerable):**
```python
@app.route('/api/snippets', methods=['POST'])
def create_snippet():
    # Immediately processes the request - anyone can call this!
    data = request.get_json()
    snippet = Snippet(title=data['title'], code=data['code'])
    db.session.add(snippet)
    db.session.commit()
    return jsonify(snippet.to_dict()), 201
```

**Key insight:** The route handlers trust every request. There's no authentication layer to check credentials.

---

### Layer 3: Data Model Layer ✅ (UNCHANGED... but needs addition)

**What's here:**
- `Snippet` model - stores code snippets
- `Tag` model - categorizes snippets
- SQLAlchemy ORM configuration

**Why the existing models didn't change:**
- Snippets and tags work correctly
- Database operations are fine
- The data layer isn't the security boundary

**What's MISSING:**
- No model to store API keys
- No way to validate credentials
- No record of who owns which key

**Key insight:** We need to ADD to this layer, not change it. Authentication requires storing and validating credentials.

---

### Layer 4: Authentication Layer 🆕 (NEEDS TO BE ADDED)

**What's needed:**
- A way to generate secure API keys
- A way to store and look up keys
- A way to validate incoming requests
- A decorator to protect specific endpoints

**This layer doesn't exist yet!** That's the core problem.

**Key insight:** Security isn't about fixing broken code—it's about adding a missing layer between "request received" and "request processed."

---

## The Anatomical Fix

### Change 1: Add the ApiKey Model (models.py)

```python
import secrets
from datetime import datetime

class ApiKey(db.Model):
    """API key for authenticating requests."""

    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used_at = db.Column(db.DateTime, nullable=True)

    @staticmethod
    def generate_key():
        """Generate a secure random API key."""
        return secrets.token_hex(32)  # 64-character hex string

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
```

**What this does:**
- Creates a database table to store API keys
- Uses `secrets.token_hex(32)` for cryptographically secure key generation
- Tracks when keys are used (audit trail)
- Allows deactivating keys without deleting them

---

### Change 2: Add the Authentication Decorator (app.py)

```python
from functools import wraps
from models import ApiKey

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

        request.api_key = key_obj
        return f(*args, **kwargs)

    return decorated
```

**What this does:**
- Checks for `X-API-Key` header on every decorated request
- Returns 401 Unauthorized if missing or invalid
- Stores the validated key in `request.api_key` for downstream use
- Uses `@wraps` to preserve function metadata

---

### Change 3: Apply the Decorator to Write Endpoints (app.py)

```python
@app.route('/api/snippets', methods=['POST'])
@require_api_key  # <-- Added this line
def create_snippet():
    # ... existing code unchanged ...

@app.route('/api/snippets/<int:snippet_id>', methods=['PUT'])
@require_api_key  # <-- Added this line
def update_snippet(snippet_id):
    # ... existing code unchanged ...

@app.route('/api/snippets/<int:snippet_id>', methods=['DELETE'])
@require_api_key  # <-- Added this line
def delete_snippet(snippet_id):
    # ... existing code unchanged ...
```

**What this does:**
- Interposes authentication check before route handler executes
- Read operations (GET) remain unprotected (public access)
- Write operations (POST, PUT, DELETE) now require valid API key

---

## Diagnosis Questions

### Question 1: Why didn't the GET endpoints need to change?

**Answer:** GET endpoints (`list_snippets`, `get_snippet`, `list_languages`, `list_tags`) are intentionally public. Reading snippets doesn't modify data, so there's no security risk. The API follows the common pattern of "public reads, authenticated writes."

---

### Question 2: Why use a decorator instead of checking auth inside each function?

**Answer:** The decorator pattern provides:
- **DRY (Don't Repeat Yourself)**: One auth check, applied to many endpoints
- **Separation of concerns**: Route logic doesn't mix with auth logic
- **Consistency**: Impossible to forget auth check on a new endpoint if you use the decorator
- **Testability**: Can test auth logic separately from business logic

---

### Question 3: What would break WITHOUT the fix?

- **Data integrity**: Anyone could modify or delete snippets they don't own
- **Spam/abuse**: Bots could flood the API with garbage data
- **No accountability**: No way to track who made what changes
- **Denial of service**: Malicious users could delete all content

---

### Question 4: What WOULDN'T break even without the fix?

- **Reading snippets**: GET requests would still work normally
- **Database operations**: CRUD operations themselves are correct
- **Data validation**: Title/code required checks still function
- **JSON serialization**: Response formatting is unchanged

---

### Question 5: Why check for BOTH missing AND invalid keys separately?

**Answer:** Different error messages help API consumers debug issues:
- Missing key → "You forgot to include credentials"
- Invalid key → "Your credentials are wrong or expired"

This is better UX than a generic "Unauthorized" for both cases.

---

## The Pattern: What This Teaches

### Core Concepts

1. **Defense in Depth**
   - Security is a layer you ADD, not a property of existing code
   - The route handler shouldn't know about authentication
   - Each layer has one job

2. **The Decorator Pattern for Cross-Cutting Concerns**
   - Authentication applies to many endpoints
   - Decorators let you add behavior without modifying functions
   - `@require_api_key` is reusable across any route

3. **Public Reads, Authenticated Writes**
   - Common API pattern: anyone can read, only authorized users can write
   - Reduces friction for legitimate users while protecting data
   - GET is idempotent and safe; POST/PUT/DELETE are not

### Diagnostic Skill Building

**When you see "anyone can modify data," ask:**
1. Is there an authentication layer? (Often: no)
2. Where should the check happen? (Before route handler executes)
3. What credentials should be required? (API key, JWT, session, etc.)
4. Which operations need protection? (Usually: anything that modifies state)
5. What's the minimal change? (Decorator + model, applied to specific routes)

---

## Practice Exercise

**Given this error:**
```
Your e-commerce API allows anyone to:
- View products (GET /api/products) ✅ This is fine
- Add items to any user's cart (POST /api/cart) ❌ Security issue!
- Checkout with any user's saved payment (POST /api/checkout) ❌ Security issue!
```

**Walk through:**

1. **Which layer is this happening in?**
   → Route handler layer. Requests are processed without checking who's making them.

2. **What's working?**
   → Product listing (GET) is intentionally public. Database operations work correctly.

3. **What's the gap?**
   → No authentication layer between request arrival and cart/checkout processing.

4. **What should the fix include?**
   → User authentication (session, JWT, or API key), applied to `/api/cart` and `/api/checkout` endpoints.

5. **What's the minimal fix?**
   → Add `@require_auth` decorator to POST routes for cart and checkout. Keep GET routes public.

---

## Test Your Understanding

After the fix, the tests now verify authentication is enforced:

```python
def test_create_snippet_without_api_key_returns_401(self, client):
    """Creating a snippet without API key returns 401."""
    response = client.post('/api/snippets', json={
        'title': 'No Auth',
        'code': 'test'
    })
    assert response.status_code == 401
    assert 'API key required' in response.get_json()['error']

def test_create_snippet_with_valid_api_key(self, client, api_key):
    """Can create a snippet with valid API key."""
    response = client.post('/api/snippets',
        headers={'X-API-Key': api_key},
        json={'title': 'New Snippet', 'code': 'print(1)'}
    )
    assert response.status_code == 201
```

The security gap is closed. Write operations now require proof of identity.
