"""
Vercel Serverless Entry Point
==============================
Exposes the FastAPI app as a Vercel serverless function.
All /api/* routes are handled by FastAPI.
"""

import os
import sys

# Add backend to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.main import app
