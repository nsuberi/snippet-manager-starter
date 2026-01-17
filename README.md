# Snippet Manager API

A simple REST API for storing and sharing code snippets. Built with Flask and SQLite.

## Features

- Create, read, update, and delete code snippets
- Support for multiple programming languages with syntax highlighting metadata
- Tag snippets for organization
- Search snippets by title or language
- **HTTP Basic Authentication** for write operations (create, update, delete)

## Quick Start

### 1. Set up virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Initialize the database

```bash
python seed_data.py
```

This creates the SQLite database, populates it with sample snippets, and creates a test user. **Note the credentials displayed** - you'll need them for write operations.

### 4. Run the server

```bash
python app.py
```

The API will be available at `http://localhost:5001`

## Authentication

Write operations (POST, PUT, DELETE) require HTTP Basic Authentication. Include credentials in the request:

```bash
# Using curl's -u flag (recommended)
curl -u admin:snippets123 -X POST http://localhost:5001/api/snippets \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "code": "print(1)"}'

# Or using the Authorization header directly
curl -X POST http://localhost:5001/api/snippets \
  -H "Authorization: Basic YWRtaW46c25pcHBldHMxMjM=" \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "code": "print(1)"}'
```

Read operations (GET) are public and do not require authentication.

### Default Test Credentials

After running `seed_data.py`:
- **Username:** `admin`
- **Password:** `snippets123`

### Authentication Errors

Missing credentials:
```json
{
  "error": "Authentication required",
  "message": "Please provide credentials using HTTP Basic Authentication"
}
```

Invalid credentials:
```json
{
  "error": "Invalid credentials",
  "message": "Username or password is incorrect"
}
```

## API Endpoints

### List all snippets
```
GET /api/snippets
```

Query parameters:
- `language` - Filter by programming language
- `tag` - Filter by tag

Example:
```bash
curl http://localhost:5001/api/snippets
curl http://localhost:5001/api/snippets?language=python
curl http://localhost:5001/api/snippets?tag=utility
```

### Get a single snippet
```
GET /api/snippets/<id>
```

Example:
```bash
curl http://localhost:5001/api/snippets/1
```

### Create a new snippet
```
POST /api/snippets
Content-Type: application/json
```

Request body:
```json
{
  "title": "Hello World",
  "code": "print('Hello, World!')",
  "language": "python",
  "description": "A simple greeting",
  "tags": ["beginner", "example"]
}
```

Example:
```bash
curl -u admin:snippets123 -X POST http://localhost:5001/api/snippets \
  -H "Content-Type: application/json" \
  -d '{"title": "Hello World", "code": "print(\"Hello!\")", "language": "python"}'
```

### Update a snippet
```
PUT /api/snippets/<id>
Content-Type: application/json
```

Example:
```bash
curl -u admin:snippets123 -X PUT http://localhost:5001/api/snippets/1 \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'
```

### Delete a snippet
```
DELETE /api/snippets/<id>
```

Example:
```bash
curl -u admin:snippets123 -X DELETE http://localhost:5001/api/snippets/3
```

### Get available languages
```
GET /api/languages
```

Returns a list of programming languages used in stored snippets.

### Get all tags
```
GET /api/tags
```

Returns a list of all tags used across snippets.

## Response Format

All responses are JSON. Successful responses include the data directly:

```json
{
  "id": 1,
  "title": "Hello World",
  "code": "print('Hello, World!')",
  "language": "python",
  "description": "A simple greeting",
  "tags": ["beginner", "example"],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

Error responses include an error message:

```json
{
  "error": "Snippet not found"
}
```

## Project Structure

```
snippet-manager/
├── app.py              # Flask application and routes
├── models.py           # SQLAlchemy database models
├── config.py           # Configuration settings
├── seed_data.py        # Database initialization and sample data
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Development

### Running in debug mode

The app runs in debug mode by default during development. For production, set:

```bash
export FLASK_DEBUG=0
```

### Database

The SQLite database is stored in `snippets.db`. To reset:

```bash
rm snippets.db
python seed_data.py
```

## License

MIT License - feel free to use this for learning and experimentation.
