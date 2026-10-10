"""Actual owned cgroup high-water marks, including startup; not host RAM estimates."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    report={'timestamp':datetime.now(timezone.utc).isoformat(),
            'scope':'owned containers since startup; cgroup charged memory includes cache/kernel',
            'services':[]}
    for service in ('qwen','stt','tts','backend','asterisk','frontend'):
        name='testmid-cpu-voice-'+service+'-1'
        item={'service':service,'container':name}
        for field, path in [('peak_bytes','memory.peak'),('current_bytes','memory.current'),
                            ('memory_events','memory.events'),('cpu_cumulative','cpu.stat')]:
            result=subprocess.run(['docker','exec',name,'cat','/sys/fs/cgroup/'+path],capture_output=True,text=True)
            if result.returncode:
                item[field]=None
            elif field.endswith('_bytes'):
                item[field]=int(result.stdout.strip())
            else:
                item[field]=dict(line.split() for line in result.stdout.splitlines())
        result=subprocess.run(['docker','inspect','--format','{{json .RestartCount}} {{json .State.OOMKilled}}',name],capture_output=True,text=True)
        if result.returncode==0:
            count, killed=result.stdout.split()
            item.update(restart_count=int(count),oom_killed=json.loads(killed))
        report['services'].append(item)
    (ROOT/'artifacts/local-demo/cgroup-memory-results.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()
