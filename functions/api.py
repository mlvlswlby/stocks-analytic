import sys
import os

# Add the project root to sys.path so 'backend' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from mangum import Mangum
from backend.main import app

# Mangum is an adapter for running ASGI applications in AWS Lambda (Netlify Functions)
handler = Mangum(app)
