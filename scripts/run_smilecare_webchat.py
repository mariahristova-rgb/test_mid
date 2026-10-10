"""Loopback fallback using the existing agents/tools/persistence; mock inference requires --mock."""
import argparse
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.demo_seed import seed_smilecare
from semantic_os.backend.assistant.store import Store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--mock', action='store_true', help='Explicit deterministic mock LLM fallback; never presented as a Qwen test')
    parser.add_argument('--port', type=int, default=8011)
    args = parser.parse_args()
    workspace = Path(__file__).resolve().parents[1]
    target = args.database.resolve()
    if not target.is_relative_to(workspace/'.assistant-data'): parser.error('Use a dedicated database under test_mid/.assistant-data')
    if os.getenv('ASSISTANT_ENV') in ('production','staging'): parser.error('Loopback demo is disabled in production/staging')
    if not os.getenv('ASSISTANT_DEMO_TOKEN'): parser.error('Set ASSISTANT_DEMO_TOKEN through the local environment')
    if args.mock: os.environ['LLM_PROVIDER']='mock'
    elif os.getenv('LLM_PROVIDER') not in ('local','qwen'): parser.error('Configure the existing Qwen endpoint or explicitly choose --mock')
    os.environ['SELF_HOSTED_VOICE_ENABLED']='false'  # This launcher is explicitly the Web Chat fallback.
    os.environ['ASSISTANT_ENABLE_LIVE_VOICE']='false'
    os.environ['ASSISTANT_ENABLE_LIVE_MESSAGING']='false'
    store=Store(str(target))
    seeded=seed_smilecare(store,mode='mock' if args.mock else 'qwen')
    if seeded['llm_provider'] != ('mock' if args.mock else 'qwen'):
        store.close(); parser.error('Existing demo mode differs; choose its dedicated database without overwriting configuration')
    import uvicorn
    app=create_app(store=store,demo_enabled=True)
    uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False)


if __name__ == '__main__': main()
