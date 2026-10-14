"""Optional first-party, consent-bound funnel evidence; no text or contact data."""
from datetime import datetime,timedelta
import json
from .store import event_key


class Journey:
    def __init__(self,store,clock):self.store,self.clock=store,clock
    def record(self,row,session,stage,scope):
        if not session.get('analytics_allowed'):return
        if stage not in {'opted_in_opened','conversation_started','availability_checked','booking_proposed','calendar_created','inquiry_recorded','human_requested'}:raise ValueError('Unknown stage')
        key=event_key('journey',session['id']+':'+str(session.get('analytics_revision',0))+':'+stage)
        with self.store.transaction():
            current=self.store.get('operations_events',row['tenant_id'],session['id'])
            if not current.get('analytics_allowed') or current.get('analytics_revision',0)!=session.get('analytics_revision',0) or current.get('status')!='active':return
            if self.store.find('operations_events',row['tenant_id'],key):return
            conversation=self.store.get('conversations',row['tenant_id'],session['conversation_id'])
            self.store.add('operations_events',row['tenant_id'],{'kind':'journey_event','conversation_id':session['conversation_id'],
                'stage':stage,'scope':scope,'assistant_ref':row['assistant_id'],'channel':'web_chat','locale':conversation['active_locale'],
                'timestamp':self.clock().isoformat(),'expires_at':min(datetime.fromisoformat(session['purge_at']),self.clock()+timedelta(days=7)).isoformat()},external_key=key)
    def withdraw(self,tenant,conversation):
        with self.store.transaction():
            for record in self.store.list('operations_events',tenant,conversation):
                if record.get('kind')=='journey_event':self.store.update('operations_events',tenant,record['id'],{'redacted':True,'stage':None})
    def observe(self,row,session,result):
        if not session.get('analytics_allowed'):return
        self.record(row,session,'conversation_started','SERVER_MESSAGE_RESULT')
        if result.get('booking_status')=='awaiting_confirmation':self.record(row,session,'booking_proposed','SERVER_PROPOSAL')
        if result.get('human_requested'):self.record(row,session,'human_requested','SERVER_HANDOFF_REQUEST')
        # Use successful tool receipts, not raw text or guessed visitor intent.
        for receipt in self.store.list('tool_executions',row['tenant_id'],session['conversation_id']):
            if receipt.get('correlation_id')!=result.get('correlation_id'):continue
            outcome=receipt.get('outcome',{})
            if outcome.get('status')!='completed':continue
            tool=receipt.get('tool')
            scope='CONNECTED_PROVIDER_RECEIPT' if tool and tool.startswith('Concierge') else 'MOCK_TOOL_RECEIPT'
            if tool in ('CheckAvailability','ConciergeAvailability'):self.record(row,session,'availability_checked',scope)
            if tool in ('CreateAppointment','ConciergeBooking') and outcome.get('data',{}).get('status')=='confirmed':self.record(row,session,'calendar_created',scope)
            if tool=='ConciergeRequest':self.record(row,session,'inquiry_recorded',scope)
    def purge(self):
        with self.store.transaction():
            rows=self.store.db.execute("SELECT data FROM operations_events WHERE json_extract(data,'$.kind')='journey_event' AND coalesce(json_extract(data,'$.redacted'),0)=0 AND json_extract(data,'$.expires_at')<=? LIMIT 500",(self.clock().isoformat(),)).fetchall()
            for record in rows:
                row=json.loads(record['data']);self.store.update('operations_events',row['tenant_id'],row['id'],{'redacted':True,'stage':None})
        return len(rows)
