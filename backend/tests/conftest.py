"""
Shared test configuration for ObaidTradez backend tests.
Sets REACT_APP_BACKEND_URL from frontend/.env so all test files resolve the base URL.
"""
import os

def _load_backend_url():
    """Read REACT_APP_BACKEND_URL from frontend/.env if not already set."""
    if os.environ.get('REACT_APP_BACKEND_URL'):
        return
    
    env_path = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', '.env')
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith('REACT_APP_BACKEND_URL='):
                    val = line.split('=', 1)[1].strip()
                    os.environ['REACT_APP_BACKEND_URL'] = val
                    return
    
    # Fallback to localhost
    os.environ['REACT_APP_BACKEND_URL'] = 'http://localhost:8001'

# Run immediately on import (before any test file reads the env var)
_load_backend_url()
