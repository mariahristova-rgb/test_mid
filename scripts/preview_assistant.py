"""Ephemeral loopback mock preview for browser verification; no credentials or persistent data."""
from pathlib import Path
import os
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cryptography.fernet import Fernet
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.store import Store

if __name__ == '__main__':
    import uvicorn
    os.environ['ASSISTANT_ENABLE_LIVE_MESSAGING'] = 'false'
    os.environ['ASSISTANT_ENABLE_LIVE_VOICE'] = 'false'
    os.environ['ASSISTANT_UI_ORIGIN'] = 'http://127.0.0.1:3011'
    os.environ['ASSISTANT_RATE_LIMIT_READS'] = '1000'
    os.environ['ASSISTANT_RATE_LIMIT_WRITES'] = '500'
    os.environ['ASSISTANT_RATE_LIMIT_AI'] = '200'
    app = create_app(store=Store(), demo_enabled=True, demo_token='synthetic-review-session', encryption_key=Fernet.generate_key().decode(), platform_subjects={'demo-admin'})
    uvicorn.run(app, host='127.0.0.1', port=8011, access_log=False)
