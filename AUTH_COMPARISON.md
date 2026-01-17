# Authentication Approaches Comparison: API Key vs HTTP Basic Auth

This document compares two authentication implementations for the Snippet Manager API, both created as learning exercises from the same starting point (no authentication).

## Implementation Summary

### Branch: `with-api-auth` (API Key Authentication)
- **Header:** `X-API-Key: <64-character-hex-string>`
- **Model:** `ApiKey` with secure key generation
- **Decorator:** `@require_api_key`
- **Key generation:** `secrets.token_hex(32)` (256-bit entropy)

### Branch: `with-basic-auth` (HTTP Basic Authentication)
- **Header:** `Authorization: Basic <base64(username:password)>`
- **Model:** `User` with password hashing
- **Decorator:** `@require_basic_auth`
- **Password storage:** `werkzeug.security.generate_password_hash()`

---

## Side-by-Side Comparison

| Aspect | API Key | HTTP Basic Auth |
|--------|---------|-----------------|
| **Lines of code added** | ~100 | ~150 |
| **New models** | 1 (ApiKey) | 1 (User) |
| **External dependencies** | None (uses stdlib `secrets`) | werkzeug (already in Flask) |
| **Header format** | Custom (`X-API-Key`) | Standard (`Authorization: Basic`) |
| **Credential complexity** | Single 64-char key | Username + Password |
| **Browser native support** | No | Yes (shows login dialog) |
| **curl convenience** | `-H "X-API-Key: key"` | `-u user:pass` |

---

## Detailed Analysis

### 1. Implementation Complexity

**API Key:**
```python
# Simple model - just key and metadata
class ApiKey(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)

# Simple validation
api_key = request.headers.get('X-API-Key')
key_record = ApiKey.query.filter_by(key=api_key, is_active=True).first()
```

**HTTP Basic Auth:**
```python
# More complex model - user identity + secure password storage
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)  # Never plaintext!
    is_active = db.Column(db.Boolean, default=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# More complex validation - parse header, decode base64, hash comparison
auth_header = request.headers.get('Authorization')
auth_type, credentials = auth_header.split(' ', 1)
decoded = base64.b64decode(credentials).decode('utf-8')
username, password = decoded.split(':', 1)
user = User.authenticate(username, password)
```

**Winner:** API Key is simpler to implement.

---

### 2. Security Properties

**API Key:**
- ✅ High entropy (256-bit random)
- ✅ Easy to rotate (generate new key)
- ⚠️ Key is stored in database as-is (not hashed)
- ⚠️ If database is compromised, keys are exposed
- ⚠️ Keys often accidentally logged/leaked

**HTTP Basic Auth:**
- ✅ Password is hashed (one-way)
- ✅ Database breach doesn't expose passwords
- ✅ User can choose memorable password
- ⚠️ Users might reuse passwords from other sites
- ⚠️ Credentials sent every request (needs HTTPS)

**Winner:** HTTP Basic Auth has better database breach protection.

---

### 3. User Experience

**API Key:**
```bash
# User must copy/paste 64-character key
curl -X POST http://localhost:5001/api/snippets \
  -H "X-API-Key: 8a4f...3b2c" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "code": "x = 1"}'
```

**HTTP Basic Auth:**
```bash
# User can use memorable credentials
curl -u admin:snippets123 -X POST http://localhost:5001/api/snippets \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "code": "x = 1"}'

# Browser shows native login dialog when accessing protected endpoints
```

**Winner:** HTTP Basic Auth for human users, API Key for programmatic access.

---

### 4. Identity & Audit Trail

**API Key:**
- Key can optionally have a `name` field
- One key might be shared among team members
- Harder to trace actions to individuals
- Good for "this service can access the API"

**HTTP Basic Auth:**
- Every request is tied to a specific user
- Easy to audit who did what
- `request.current_user` available in route handlers
- Good for "this person made this change"

**Winner:** HTTP Basic Auth for accountability.

---

### 5. Credential Management

**API Key:**
```python
# Admin generates key for user
api_key = ApiKey.generate(name="Production Server")
print(f"Your API key: {api_key.key}")
# User must store this securely - it's the only time they see it

# To revoke: delete or deactivate the key
api_key.is_active = False
```

**HTTP Basic Auth:**
```python
# User sets their own password
user = User.create("alice", "her-chosen-password")

# To revoke: deactivate account or user changes password
user.is_active = False
# or
user.set_password("new-password")
```

**Winner:** Depends on use case. API Keys are better for admin-managed access, Basic Auth for self-service.

---

### 6. Client Library Support

**API Key:**
```python
# Python requests
requests.get(url, headers={"X-API-Key": key})

# JavaScript fetch
fetch(url, { headers: { "X-API-Key": key } })
```

**HTTP Basic Auth:**
```python
# Python requests - native support!
requests.get(url, auth=("user", "pass"))

# JavaScript fetch
fetch(url, { headers: { "Authorization": "Basic " + btoa("user:pass") } })
# or with credentials in URL (not recommended)
fetch("https://user:pass@api.example.com/endpoint")
```

**Winner:** HTTP Basic Auth has better native library support.

---

## When to Use Each

### Use API Key When:
- Building service-to-service integrations
- Access is managed by administrators
- You want easy key rotation
- Identity of caller doesn't matter (just authorization)
- Building a developer platform where one key = one app

### Use HTTP Basic Auth When:
- Building user-facing APIs
- Need to track which user made each change
- Users should manage their own credentials
- Want browser-native authentication
- Building internal tools where users already have accounts

---

## Teaching Value

Both approaches teach important concepts:

### API Key Teaches:
- Custom header handling
- Secure random generation (`secrets` module)
- Simple credential validation
- The concept of "bearer tokens"

### HTTP Basic Auth Teaches:
- HTTP authentication standards
- Password hashing (never store plaintext!)
- Base64 encoding (encoding ≠ encryption)
- User identity in request context
- The `WWW-Authenticate` response header

### Combined Learning:
Having students implement both approaches on separate branches teaches:
- There's rarely one "right" way
- Different requirements lead to different solutions
- Trade-off analysis is a core engineering skill
- Git branching for exploring alternatives

---

## Recommendation for Learning Exercises

**For beginners:** Start with API Key
- Fewer moving parts
- No password hashing to understand
- Clearer mental model (key = access)

**For intermediate:** HTTP Basic Auth
- Introduces security concepts (hashing)
- Follows HTTP standards
- More representative of production systems

**Advanced exercise:** Implement both and write this comparison themselves!
