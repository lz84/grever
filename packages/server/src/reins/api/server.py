# Reins Server compatibility module
# Use api.server.create_app() instead of importing app directly to avoid circular imports

def create_app():
    """Create the FastAPI app - delegates to api.server"""
    from api.server import create_app as _create_app
    return _create_app()

# Lazy app property
_app = None

def get_app():
    """Get the app instance (lazy initialization)"""
    global _app
    if _app is None:
        from api.server import app as _app_instance
        _app = _app_instance
    return _app

# For backward compatibility - use get_app() instead
# app = get_app()  # Don't create at import time to avoid circular imports
