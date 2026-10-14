"""Offline root-owned staging initialization; no demo login or live provider grant."""
import argparse
import json
import os
from pathlib import Path
from backend.assistant.api import create_app
from backend.assistant.store import Store
from backend.assistant.domain import AssistantConfig
from backend.assistant.saas_domain import SubscriptionPlan
from backend.assistant.ux import DraftInput,RunInput,ConfirmInput
from backend.assistant.widget import WidgetSettings,WidgetPublish

TENANT='phase15-public-staging'
SITE='https://assistant-demo.ontelyx.tech'
WIDGET='https://assistant-staging.ontelyx.tech'

def prepare(app,store,site_dir,approved):
    actor=store.principal('offline-staging-owner',TENANT)
    billing=app.state.billing
    if not billing.plans():
        billing.save_plan(SubscriptionPlan(id='staging-text',name_bg='Синтетичен staging тест',name_en='Synthetic staging test',trial_days=7,
            limits={'assistants':{'maximum':1},'agents':{'maximum':2},'users':{'maximum':2},'ai_messages':{'maximum':1000},'tool_executions':{'maximum':1000},'storage_bytes':{'maximum':5000000}}))
    if not billing.entitlements.subscription(TENANT):
        store.update_tenant(TENANT,{**store.tenant(TENANT),'email_verified':True,'onboarding_state':'configuring','owner_subject':'offline-staging-owner','administrator_email':'synthetic-owner@example.invalid','name':'Ontelyx synthetic staging','retention_days':7})
        store.add('billing_customers',TENANT,billing.provider.create_customer(TENANT),external_key='current')
        billing.select_trial(actor,'staging-text','monthly')
    existing=app.state.widget.rows(TENANT,'widget_integration')
    if existing:
        row=existing[0];return {'widget_id':row['id'],'public_id':row['public_id'],'draft_id':row.get('draft_id'),'state':row['state']}
    config=AssistantConfig(name='Ontelyx staging FAQ',instructions='Use approved public FAQs only. This is synthetic staging. Booking, email and voice are unavailable; never claim they completed.',
        public_knowledge_only=True,enabled_channels=['web_chat'],allowed_tools=['EscalateToHuman'],llm_provider='mock',faq_entries=approved['faq_entries'])
    draft=app.state.ux.save(actor,DraftInput(assistant_id='default',config=config,business={'name':'Ontelyx synthetic staging','website':SITE,'industry':'Synthetic staging','timezone':'Europe/Sofia'}))
    for locale in ('bg-BG','en-US'):
        for scenario in ('greeting','faq'):
            receipt=app.state.ux.test(actor,draft['id'],RunInput(revision=draft['revision'],locale=locale,scenario=scenario))
            if receipt['verdict']!='PASS':raise RuntimeError('Staging text test failed')
    app.state.ux.publish(actor,draft['id'],ConfirmInput(revision=draft['revision'],confirmed=True))
    row=app.state.widget.configure(actor,WidgetSettings(assistant_id='default',origins=[SITE],appearance='ontelyx-dark',color='#54dde2',booking_enabled=False,faq_approved=True,retention_days=7,daily_sessions=20,daily_messages=200,
        greetings={'bg-BG':'Ontelyx staging: одобрена продуктова информация.','en-US':'Ontelyx staging: approved product information.'},
        privacy_notices={'bg-BG':'Синтетична staging демонстрация. Без реално записване, имейл или глас. Не въвеждайте лични данни.','en-US':'Synthetic staging demo. No live booking, email or voice. Do not enter personal data.'}))
    proof=app.state.widget.challenge(actor,row['id'],SITE)
    target=site_dir/'.well-known/testmid-widget';target.mkdir(parents=True,exist_ok=True)
    (target/(row['public_id']+'.txt')).write_text(proof['content'],encoding='utf-8')
    page='<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ontelyx staging preview</title><style>body{background:#080f1c;color:#fff;font:18px Segoe UI,sans-serif;margin:32px;line-height:1.6}main{max-width:800px;margin:auto}a{color:#54dde2}</style><main><h1>Ontelyx staging preview</h1><p>Approved public product questions, Bulgarian and English. / Одобрени продуктови въпроси на български и английски.</p><p>Synthetic text-only test. No live appointments, email or voice. Do not enter personal data. / Синтетичен текстов тест. Без реални часове, имейл или глас. Не въвеждайте лични данни.</p><p>Use the chat button after the domain is verified. / Използвайте бутона за чат след проверката на домейна.</p></main><script src="'+WIDGET+'/widget/assets/v1.js" data-assistant-id="'+row['public_id']+'" data-locale="auto" async></script></html>'
    (site_dir/'index.html').write_text(page,encoding='utf-8')
    return {'widget_id':row['id'],'public_id':row['public_id'],'draft_id':draft['id'],'state':'DOMAIN_VERIFICATION_REQUIRED'}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','publish']);args=parser.parse_args()
    if os.getenv('ASSISTANT_ENV')!='staging' or os.getenv('ASSISTANT_STAGING_BOOTSTRAP')!='true' or os.getenv('ASSISTANT_DEMO')!='false':raise RuntimeError('Explicit isolated staging required')
    store=Store(os.environ['ASSISTANT_DATABASE'])
    with store.lock:
        if any(row['id']!=TENANT for row in store.db.execute('SELECT id FROM tenants')):raise RuntimeError('An empty isolated store is required')
    store.seed(TENANT,'offline-staging-owner')
    app=create_app(store=store,demo_enabled=False)
    try:
        site=Path('/site');site.mkdir(exist_ok=True);state=site/'public-state.json'
        if args.action=='prepare':
            report=json.loads(state.read_text()) if state.exists() else prepare(app,store,site,json.loads(Path('/approved-public-config.json').read_text(encoding='utf-8')))
            state.write_text(json.dumps(report,indent=2),encoding='utf-8')
        else:
            report=json.loads(state.read_text());actor=store.principal('offline-staging-owner',TENANT)
            # Verify real HTTPS ownership. Never stub DNS or domain proof.
            app.state.widget.verify(actor,report['widget_id'],SITE)
            app.state.widget.publish(actor,report['widget_id'],WidgetPublish(draft_id=report['draft_id'],confirmed=True))
            report['state']='PUBLISHED_TEXT_MOCK_ONLY';state.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps(report))
    finally:app.state.voice_runtime.shutdown();store.close()

if __name__=='__main__':main()
