"""External acceptance admission only; never grants provider consent itself."""
from datetime import datetime, timezone
from hashlib import sha256
from .domain import DomainError


def authorize_acceptance(manifest, *, enabled=False, approval_id='', tenant='', account='', resource='', action='', clock=None):
    if enabled is not True or not approval_id or not isinstance(manifest,dict):
        raise DomainError('forbidden',403)
    current=(clock or (lambda:datetime.now(timezone.utc)))()
    try:
        expiry=datetime.fromisoformat(manifest['expires_at'])
        approved=datetime.fromisoformat(manifest['approved_at'])
        if expiry.tzinfo is None or approved.tzinfo is None or not approved <= current < expiry or (expiry-approved).total_seconds()>3600:
            raise ValueError()
        if (manifest['approval_id']!=approval_id or manifest['provider']!='google'
                or manifest['tenant_id']!=tenant or manifest['account_sha256']!=sha256(account.encode()).hexdigest()
                or manifest['resource_sha256']!=sha256(resource.encode()).hexdigest()
                or manifest['isolated_test_calendar'] is not True or manifest['consent_receipt'] is not True
                or action not in manifest['actions'] or set(manifest['actions'])-{'read','create_one_test','reconcile','cleanup_test'}
                or manifest['max_events']!=1 or manifest['send_updates']!='none'
                or not manifest['cleanup_approved']):
            raise ValueError()
    except (KeyError,TypeError,ValueError):
        raise DomainError('forbidden',403) from None
    return {'scope':'APPROVED_ISOLATED_TEST_ONLY','action':action,'max_events':1}


def run_acceptance(manifest, *, service, actor, connection_id, approval_id='', enabled=False, action='read', clock=None):
    """Reuse the customer service; default harness performs discovery only.

    Write steps must use the existing visitor approval/job workflow, not a second
    direct event writer. This read harness deliberately cannot bypass that gate.
    """
    if enabled is not True or not approval_id: raise DomainError('forbidden',403)
    row=service.row(actor,connection_id)
    account=service.vault.get(actor.tenant_id,'customer:account:'+connection_id,actor)
    if len(row['resource_ids'])!=1: raise DomainError('forbidden',403)
    resource=service.resolve_resource(actor,row,row['resource_ids'][0])
    authorize_acceptance(manifest,enabled=enabled,approval_id=approval_id,tenant=actor.tenant_id,
        account=account,resource=resource,action=action,clock=clock)
    if action!='read': raise DomainError('tool_denied',403)
    discovered=service.resources(actor,connection_id)
    if not any(r['id']==row['resource_ids'][0] and r['writable'] for r in discovered):
        raise DomainError('forbidden',403)
    return {'resource_access':'REAL_HTTP_RESOURCE_ACCESS_ONLY' if service.http.__class__.__name__=='ProductionProviderHTTP' and service.http.transport is None else 'PASS_OFFLINE',
        'write_performed':False,'account_or_resource_disclosed':False}
