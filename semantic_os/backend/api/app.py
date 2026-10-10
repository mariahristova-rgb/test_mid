"""Deployed entry point. No legacy runtime imports or automatic legacy migrations."""
from ..assistant.api import create_app
app = create_app()
