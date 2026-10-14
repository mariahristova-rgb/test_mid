"""Ephemeral exact-match index of already approved assistant FAQs; no crawler or embeddings."""
from hashlib import sha256
import json

def lookup(entries,question,locale):
    index={}
    for position,entry in enumerate(entries):
        digest=sha256(json.dumps(entry,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        for key in ('question_bg','question_en'):
            index.setdefault(entry[key].strip().casefold(),(entry,position,digest))
    match=index.get(question.strip().casefold())
    if not match:return None
    entry,position,digest=match
    return {'answer':entry['answer_bg' if locale=='bg-BG' else 'answer_en'],
            'provenance':{'kind':'approved_assistant_faq','entry':position,'sha256':digest,'locale':locale}}
