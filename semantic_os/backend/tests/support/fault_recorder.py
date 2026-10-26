"""Independent durable loopback mock provider oracle for crash experiments."""
import json
import sqlite3
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread,RLock
from time import sleep

class Recorder:
    def __init__(self,path):
        self.db=sqlite3.connect(str(path),check_same_thread=False,isolation_level=None)
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE events(id TEXT PRIMARY KEY,body TEXT NOT NULL)')
        self.db.execute('CREATE TABLE calls(kind TEXT NOT NULL)')
        self.lock=RLock();self.mode='normal';self.on_availability=None
        owner=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):self.respond()
            def do_POST(self):self.respond()
            def respond(self):
                body=json.loads(self.rfile.read(int(self.headers.get('content-length','0'))) or b'{}')
                path=self.path.split('?',1)[0]
                status=200;kind='discovery'
                if path.endswith('/calendarList'):
                    value={'items':[] if owner.mode=='access_removed' else [{'id':'calendar-owner','accessRole':'owner'}]}
                elif path.endswith('/freeBusy'):
                    kind='availability';value={'calendars':{'calendar-owner':{'busy':[]}}}
                    if owner.on_availability:
                        callback=owner.on_availability;owner.on_availability=None;callback()
                elif path.endswith('/events') and self.command=='POST':
                    kind='create'
                    with owner.lock:
                        try:owner.db.execute('INSERT INTO events VALUES (?,?)',(body['id'],json.dumps(body)));status=201
                        except sqlite3.IntegrityError:status=409
                    value=body
                elif '/events/' in path and self.command=='GET':
                    kind='lookup'
                    with owner.lock:row=owner.db.execute('SELECT body FROM events WHERE id=?',(path.rsplit('/',1)[1],)).fetchone()
                    value=json.loads(row[0]) if row else {};status=200 if row else 404
                else:status=404;value={}
                with owner.lock:owner.db.execute('INSERT INTO calls VALUES (?)',(kind,))
                if kind=='create' and owner.mode=='timeout_after_accept':sleep(3)
                content=json.dumps(value).encode()
                try:self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(content)));self.end_headers();self.wfile.write(content)
                except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
        self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        self.thread=Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url='http://127.0.0.1:'+str(self.server.server_address[1])
    def counts(self):
        with self.lock:
            return {'create_posts':self.db.execute("SELECT count(*) FROM calls WHERE kind='create'").fetchone()[0],
                'reconcile_gets':self.db.execute("SELECT count(*) FROM calls WHERE kind='lookup'").fetchone()[0],
                'events':self.db.execute('SELECT count(*) FROM events').fetchone()[0]}
    def close(self):self.server.shutdown();self.server.server_close();self.thread.join(timeout=3);self.db.close()


def transport(url):
    import httpx
    from urllib.parse import urlsplit
    target=urlsplit(url)
    if target.scheme!='http' or target.hostname!='127.0.0.1' or not target.port:raise ValueError('Loopback oracle only')
    def request(original):
        with httpx.Client(timeout=2,trust_env=False) as client:
            response=client.request(original.method,url+original.url.path,content=original.content,headers={'Content-Type':'application/json'})
        return httpx.Response(response.status_code,content=response.content,headers={'Content-Type':'application/json'})
    return httpx.MockTransport(request)
