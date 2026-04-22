"""
Vercel Serverless Entry Point
==============================
Exposes the FastAPI app as a Vercel serverless function.
All /api/* routes are handled by FastAPI.
"""

import os
import sys

# Vercel runs from the project root. Add backend/ to sys.path
# so that 'from app.main import app' resolves correctly.
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_backend_dir = os.path.join(_project_root, "backend")

if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from app.main import app  # noqa: E402
