"""Offline-only admission/capacity check; never calls a cloud API or applies resources."""
import argparse
import json
from pathlib import Path


def validate(plan):
    if any(plan.get(key) is not False for key in ('deployment_allowed','new_spending_authorized',
                                                 'runtime_postgres_accepted','model_artifacts_accepted')):
        raise ValueError('Review-only plan must not authorize activation')
    if plan.get('scope') != 'OFFLINE_REVIEW_ONLY':
        raise ValueError('Invalid plan scope')
    for key in ('api','inference'):
        resource=plan['resources'][key]
        if resource['ingress'] != 'INGRESS_TRAFFIC_INTERNAL_ONLY':
            raise ValueError('Public service is forbidden')
        template=resource['template']
        if template['scaling'] != {'minInstanceCount':0,'maxInstanceCount':1} or template['maxInstanceRequestConcurrency'] != 1:
            raise ValueError('Unreviewed autoscaling')
    model=plan['resources']['inference']['template']['containers'][0]
    if model['resources']['limits'] != {'cpu':'4','memory':'16Gi','nvidia.com/gpu':'1'}:
        raise ValueError('Unexpected model resource envelope')
    if plan['resources']['database']['public_ip'] is not False or not plan['resources']['files']['signed_access_only']:
        raise ValueError('Unreviewed data exposure')
    # Sensitivity assumptions only: not measurements or financial quotations.
    assumptions={'conversations_per_tenant_day':50,'turns_per_conversation':6,
                 'input_tokens_per_turn':800,'output_tokens_per_turn':200,'agent_call_multiplier':2}
    rows=[]
    for tenants in (10,25,50,100):
        calls=tenants*50*6*2
        rows.append({'tenants':tenants,'assumed_calls_per_day':calls,
                     'assumed_input_tokens_per_day':calls*800,'assumed_output_tokens_per_day':calls*200,
                     'measured_capacity':None,'gpu_cost_estimate':None})
    return {'static_admission':'PASS','vendor_schema_validation':'NOT_EXECUTED',
            'deployment_allowed':False,'public_production_ready':False,'assumptions':assumptions,'sensitivity':rows}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--plan',default='semantic_os/deploy/phase26b/staging-plan.json')
    parser.add_argument('--output',default='artifacts/phase26b-staging-plan.json')
    args=parser.parse_args()
    result=validate(json.loads(Path(args.plan).read_text(encoding='utf-8')))
    path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('assumptions','sensitivity')}))
