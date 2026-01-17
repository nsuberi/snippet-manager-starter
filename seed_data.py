"""
Database initialization and seed data.

Run this script to create the database and populate it with sample snippets:
    python seed_data.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Snippet, Tag, User, get_or_create_tag


SAMPLE_SNIPPETS = [
    {
        'title': 'Flask Basic Route',
        'language': 'python',
        'description': 'A simple Flask route that returns JSON data.',
        'tags': ['flask', 'web', 'beginner'],
        'code': '''from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/hello')
def hello():
    return jsonify({
        'message': 'Hello, World!',
        'status': 'success'
    })

if __name__ == '__main__':
    app.run(debug=True)'''
    },
    {
        'title': 'Python List Comprehension Examples',
        'language': 'python',
        'description': 'Common list comprehension patterns in Python.',
        'tags': ['python', 'beginner', 'utility'],
        'code': '''# Basic list comprehension
squares = [x**2 for x in range(10)]

# With condition
evens = [x for x in range(20) if x % 2 == 0]

# Nested comprehension (flatten 2D list)
matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
flat = [num for row in matrix for num in row]

# Dictionary comprehension
word_lengths = {word: len(word) for word in ['hello', 'world', 'python']}

# Set comprehension
unique_lengths = {len(word) for word in ['hello', 'world', 'hi', 'python']}

print(f"Squares: {squares}")
print(f"Evens: {evens}")
print(f"Flattened: {flat}")
print(f"Word lengths: {word_lengths}")
print(f"Unique lengths: {unique_lengths}")'''
    },
    {
        'title': 'JavaScript Fetch API Wrapper',
        'language': 'javascript',
        'description': 'A reusable fetch wrapper with error handling and JSON parsing.',
        'tags': ['javascript', 'api', 'utility'],
        'code': '''async function fetchJSON(url, options = {}) {
  const defaultOptions = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  const mergedOptions = {
    ...defaultOptions,
    ...options,
    headers: {
      ...defaultOptions.headers,
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, mergedOptions);

    if (!response.ok) {
      const error = new Error(`HTTP ${response.status}: ${response.statusText}`);
      error.status = response.status;
      error.response = response;
      throw error;
    }

    return await response.json();
  } catch (error) {
    console.error('Fetch error:', error);
    throw error;
  }
}

// Usage examples:
// const data = await fetchJSON('/api/users');
// const user = await fetchJSON('/api/users', {
//   method: 'POST',
//   body: JSON.stringify({ name: 'John' })
// });'''
    },
    {
        'title': 'SQL Common Table Expression (CTE)',
        'language': 'sql',
        'description': 'Using CTEs for readable complex queries with employee hierarchy example.',
        'tags': ['sql', 'database', 'intermediate'],
        'code': '''-- Find all employees and their management chain
WITH RECURSIVE employee_hierarchy AS (
    -- Base case: top-level managers (no manager)
    SELECT
        id,
        name,
        manager_id,
        1 AS level,
        name AS management_chain
    FROM employees
    WHERE manager_id IS NULL

    UNION ALL

    -- Recursive case: employees with managers
    SELECT
        e.id,
        e.name,
        e.manager_id,
        eh.level + 1,
        eh.management_chain || ' > ' || e.name
    FROM employees e
    INNER JOIN employee_hierarchy eh ON e.manager_id = eh.id
)
SELECT
    id,
    name,
    level,
    management_chain
FROM employee_hierarchy
ORDER BY management_chain;'''
    },
    {
        'title': 'Python Decorator with Arguments',
        'language': 'python',
        'description': 'A decorator that accepts arguments, useful for retry logic or rate limiting.',
        'tags': ['python', 'intermediate', 'patterns'],
        'code': '''import functools
import time

def retry(max_attempts=3, delay=1, exceptions=(Exception,)):
    """
    Decorator that retries a function on failure.

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Seconds to wait between retries
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        print(f"Attempt {attempt} failed: {e}. Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        print(f"All {max_attempts} attempts failed.")

            raise last_exception
        return wrapper
    return decorator


# Usage
@retry(max_attempts=3, delay=2, exceptions=(ConnectionError, TimeoutError))
def fetch_data(url):
    # Simulated API call that might fail
    import random
    if random.random() < 0.7:
        raise ConnectionError("Failed to connect")
    return {"data": "success"}'''
    },
    {
        'title': 'CSS Flexbox Centering',
        'language': 'css',
        'description': 'Different ways to center elements using CSS Flexbox.',
        'tags': ['css', 'layout', 'beginner'],
        'code': '''/* Center single item both horizontally and vertically */
.container-center {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}

/* Center items with space between */
.container-space-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}

/* Center items in a column */
.container-column {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

/* Responsive card grid */
.card-grid {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 24px;
}

.card-grid > .card {
  flex: 0 1 300px;
  max-width: 400px;
}'''
    },
    {
        'title': 'Bash Script Template',
        'language': 'bash',
        'description': 'A robust bash script template with error handling and argument parsing.',
        'tags': ['bash', 'devops', 'utility'],
        'code': '''#!/bin/bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Script metadata
SCRIPT_NAME=$(basename "$0")
VERSION="1.0.0"

# Default values
VERBOSE=false
OUTPUT_DIR="./output"

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

usage() {
    cat << EOF
Usage: $SCRIPT_NAME [OPTIONS] <input_file>

Options:
    -o, --output DIR    Output directory (default: $OUTPUT_DIR)
    -v, --verbose       Enable verbose output
    -h, --help          Show this help message
    --version           Show version

Example:
    $SCRIPT_NAME -v -o ./results input.txt
EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -o|--output) OUTPUT_DIR="$2"; shift 2 ;;
        -v|--verbose) VERBOSE=true; shift ;;
        -h|--help) usage; exit 0 ;;
        --version) echo "$VERSION"; exit 0 ;;
        -*) log_error "Unknown option: $1"; usage; exit 1 ;;
        *) INPUT_FILE="$1"; shift ;;
    esac
done

# Validate required arguments
if [[ -z "${INPUT_FILE:-}" ]]; then
    log_error "Input file is required"
    usage
    exit 1
fi

# Main logic
log_info "Processing $INPUT_FILE..."
mkdir -p "$OUTPUT_DIR"
# ... your code here ...
log_info "Done!"'''
    },
    {
        'title': 'React Custom Hook - useLocalStorage',
        'language': 'javascript',
        'description': 'A React hook for persisting state to localStorage with SSR support.',
        'tags': ['react', 'javascript', 'hooks'],
        'code': '''import { useState, useEffect } from 'react';

function useLocalStorage(key, initialValue) {
  // State to store our value
  // Pass initial state function to useState so logic is only executed once
  const [storedValue, setStoredValue] = useState(() => {
    if (typeof window === 'undefined') {
      return initialValue;
    }

    try {
      const item = window.localStorage.getItem(key);
      return item ? JSON.parse(item) : initialValue;
    } catch (error) {
      console.warn(`Error reading localStorage key "${key}":`, error);
      return initialValue;
    }
  });

  // Return a wrapped version of useState's setter function that
  // persists the new value to localStorage
  const setValue = (value) => {
    try {
      // Allow value to be a function so we have same API as useState
      const valueToStore = value instanceof Function ? value(storedValue) : value;

      setStoredValue(valueToStore);

      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore));
      }
    } catch (error) {
      console.warn(`Error setting localStorage key "${key}":`, error);
    }
  };

  return [storedValue, setValue];
}

// Usage:
// const [theme, setTheme] = useLocalStorage('theme', 'light');
// const [user, setUser] = useLocalStorage('user', null);

export default useLocalStorage;'''
    },
    {
        'title': 'Docker Compose - Python Web App',
        'language': 'yaml',
        'description': 'Docker Compose configuration for a Python web app with PostgreSQL and Redis.',
        'tags': ['docker', 'devops', 'python'],
        'code': '''version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:5000"
    environment:
      - FLASK_ENV=development
      - DATABASE_URL=postgresql://user:password@db:5432/appdb
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - .:/app
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    command: flask run --host=0.0.0.0

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=appdb
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d appdb"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:'''
    },
    {
        'title': 'Python Context Manager',
        'language': 'python',
        'description': 'Custom context manager for timing code execution.',
        'tags': ['python', 'intermediate', 'utility'],
        'code': '''import time
from contextlib import contextmanager

@contextmanager
def timer(label="Operation"):
    """
    Context manager for timing code blocks.

    Usage:
        with timer("Database query"):
            results = db.execute(query)
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        print(f"{label} took {elapsed:.4f} seconds")


# Class-based version with more features
class Timer:
    def __init__(self, label="Operation", logger=None):
        self.label = label
        self.logger = logger or print
        self.elapsed = None

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed = time.perf_counter() - self.start
        self.logger(f"{self.label} took {self.elapsed:.4f} seconds")
        return False  # Don\'t suppress exceptions


# Usage examples
if __name__ == "__main__":
    # Simple usage
    with timer("Sleep test"):
        time.sleep(0.5)

    # Access elapsed time after
    with Timer("Processing") as t:
        time.sleep(0.25)
    print(f"Elapsed time was: {t.elapsed}")'''
    },
]


def seed_database():
    """Create tables and insert sample data."""
    print("Creating database tables...")
    db.create_all()

    # Check if data already exists
    if Snippet.query.first():
        print("Database already has data. Skipping seed.")
        return

    print("Inserting sample snippets...")
    for snippet_data in SAMPLE_SNIPPETS:
        tags = snippet_data.pop('tags', [])

        snippet = Snippet(**snippet_data)

        for tag_name in tags:
            tag = get_or_create_tag(tag_name)
            snippet.tags.append(tag)

        db.session.add(snippet)

    db.session.commit()

    # Create a default user for testing
    print("Creating test user...")
    test_user = User.create("admin", "snippets123")
    print(f"\n{'='*60}")
    print("TEST CREDENTIALS:")
    print(f"  Username: admin")
    print(f"  Password: snippets123")
    print(f"{'='*60}\n")

    snippet_count = Snippet.query.count()
    tag_count = Tag.query.count()
    print(f"Done! Created {snippet_count} snippets, {tag_count} tags, and 1 user.")


def reset_database():
    """Drop all tables and recreate with seed data."""
    print("Dropping all tables...")
    db.drop_all()
    seed_database()


if __name__ == '__main__':
    import sys

    with app.app_context():
        if len(sys.argv) > 1 and sys.argv[1] == '--reset':
            reset_database()
        else:
            seed_database()
