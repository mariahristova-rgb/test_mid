"""Ephemeral synthetic UI QA fixture. No real inference, speech, SIP or production data."""
from pathlib import Path
import os
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.providers import ProviderRegistry
from semantic_os.backend.assistant.demo_seed import seed_smilecare, TENANT
from semantic_os.backend.assistant.store import Store


if __name__ == '__main__':
    import uvicorn
    os.environ['SELF_HOSTED_VOICE_ENABLED']='false'
    os.environ['ASSISTANT_UI_ORIGIN']='http://127.0.0.1:3017'
    store=Store()
    seed_smilecare(store,mode='mock')
    app=create_app(store=store,providers=ProviderRegistry(),demo_enabled=True,demo_token=os.environ['ASSISTANT_DEMO_TOKEN'])
    actor=store.principal('demo-admin',TENANT)
    call=app.state.voice.start(actor,'default','bg-BG')
    for number,text in enumerate(('Искам да запиша час за следващия понеделник в 15:00.','Казвам се Мария Демо.','Потвърждавам')):
        app.state.voice.process_text(actor,call['id'],text,'synthetic-ui-'+str(number))
    app.state.voice.finish(actor,call['id'])
    uvicorn.run(app,host='127.0.0.1',port=8017,access_log=False)
