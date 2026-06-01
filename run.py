"""
Entry point for the HIS.Pro FastAPI Application
"""

import os
import uvicorn

if __name__ == '__main__':
    # Get configuration from environment
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8000))
    env = os.getenv('APP_ENV') or os.getenv('FLASK_ENV', 'development')
    reload = env == 'development'
    workers = 1 if reload else int(os.getenv('WEB_CONCURRENCY', '1'))

    print(f"[OK] Starting HIS.Pro FastAPI server on {host}:{port}")
    print(f"[OK] Environment: {env}")
    print(f"[OK] reload: {reload}")
    print(f"[OK] workers: {workers}")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        workers=workers
    )
