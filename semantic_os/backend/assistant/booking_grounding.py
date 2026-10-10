"""Application-owned explicit entities. Constrains model suggestions; grants no permissions."""
import re

DAY=r'(?:(?:next|следващия|следващият)\s+)?(?:today|tomorrow|днес|утре|monday|tuesday|wednesday|thursday|friday|saturday|sunday|понеделник|понедельник|вторник|сряда|четвъртък|петък|събота|неделя)'
BG_HOURS={'нула':0,'един':1,'едно':1,'два':2,'две':2,'три':3,'четири':4,'пет':5,'шест':6,'седем':7,'осем':8,'девет':9,'десет':10,
    'единадесет':11,'дванадесет':12,'тринадесет':13,'четиринадесет':14,'петнадесет':15,'шестнадесет':16,'седемнадесет':17,'осемнадесет':18,'деветнадесет':19}
MERIDIAN=r'(a\.?m\.?|p\.?m\.?|a|p)'

def explicit_entities(text, *, collecting_name=False):
    lower=text.casefold()
    day=re.search(r'\b('+DAY+r')\b',lower)
    # Exact weekday synonym observed in multilingual ASR; never fuzzy-match unknown dates.
    day_text=day[0].replace('понедельник','понеделник') if day else None
    absolute=re.search(r'\b(?:\d{4}-\d{2}-\d{2}|\d{2}[./]\d{2}[./]\d{4})(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?)?',text)
    clock=re.search(r'\b(\d{1,2}):(\d{2})\s*'+MERIDIAN+r'?\b',lower)
    hour,minute=None,0
    if clock:
        hour,minute=int(clock[1]),int(clock[2])
        if clock[3]: hour=hour%12+(12 if clock[3].startswith('p') else 0)
    else:
        match=re.search(r'\b(\d{1,2})\s*'+MERIDIAN+r'\b',lower)
        if match: hour=int(match[1])%12+(12 if match[2].startswith('p') else 0)
        else:
            match=re.search(r'\b(?:в|с|at)\s+(\d{1,2})\s*(?:часа|час|ч\.?|o.clock)?\b',lower)
            if match: hour=int(match[1])
            else:
                match=re.search(r'\bв\s+('+'|'.join(BG_HOURS)+r')\s+часа\b',lower)
                if match: hour=BG_HOURS[match[1]]
    full=None
    if absolute and 'T' in absolute[0]: full=absolute[0]
    elif hour is not None and 0<=hour<=23 and 0<=minute<=59:
        time=f'{hour:02d}:{minute:02d}'
        full=(day_text+' '+time) if day else (absolute[0]+' '+time) if absolute else time
    duration=None
    amount=re.search(r'\b(\d+)\s*(?:minutes?|минути|минута|мин)\b',lower)
    if amount and 5<=int(amount[1])<=480: duration=int(amount[1])
    elif re.search(r'\b(?:half an hour|половин час)\b',lower): duration=30
    elif re.search(r'\b(?:duration|lasting|продължителност)\b',lower):
        amount=re.search(r'\b(\d+)\s*(?:hours?|часа|час)\b',lower)
        if amount and 5<=int(amount[1])*60<=480: duration=int(amount[1])*60
    name=None
    match=re.search(r'(?:казвам се|името ми е|my name is|name is)\s+([^.,;!?]+)',text,re.I)
    if match: name=re.split(r'\s+(?:и\s+потвърждавам|and\s+i\s+confirm)\b',match[1],flags=re.I)[0].strip()
    elif collecting_name and re.fullmatch(r'[^\W\d_]+(?:[ \-\'][^\W\d_]+){0,5}',text.strip(),re.U):
        candidate=text.strip()
        if (candidate.casefold() not in ('yes','no','confirm','i confirm','потвърждавам','да','не','hello','thanks','здравейте','благодаря')
                and not re.search(r'\b(?:се|са|is|am|name)\b',candidate,re.I)
                and not re.match(r'^(?:what|when|why|how|please|switch|continue|как|кога|защо|кой|може|премини|продължи)\b',candidate,re.I)):
            name=candidate
    if name and (len(name)>120 or not re.fullmatch(r'[^\W\d_]+(?:[ \-\'][^\W\d_]+){0,5}',name,re.U)): name=None
    result={'duration_minutes':duration}
    if full: result.update(date_text=full,day_text=None)
    elif day: result.update(date_text=None,day_text=day_text)
    if name: result['contact_name']=name
    return result
