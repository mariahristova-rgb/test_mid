const formatter=zone=>new Intl.DateTimeFormat('en-CA',{timeZone:zone,year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'});
const parts=(format,instant)=>Object.fromEntries(format.formatToParts(instant).map(p=>[p.type,p.value]));
const text=p=>`${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}`;
export function scheduleLocal(value,zone){
  if(!value)return '';
  try{return text(parts(formatter(zone),new Date(value)));}catch{return '';}
}
export function scheduleInstant(value,zone){
  if(!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(value))throw new Error('invalid_local_time');
  const target=Date.parse(value+':00Z'),format=formatter(zone),offsets=new Set();
  if(!Number.isFinite(target)||new Date(target).toISOString().slice(0,16)!==value)throw new Error('invalid_local_time');
  for(let hours=-36;hours<=36;hours+=12){
    const instant=new Date(target+hours*3600000),p=parts(format,instant);
    offsets.add(Date.parse(`${text(p)}:${p.second}Z`)-instant.getTime());
  }
  const matches=[...offsets].map(offset=>new Date(target-offset)).filter(instant=>text(parts(format,instant))===value);
  if(matches.length!==1)throw new Error('ambiguous_or_missing_local_time');
  return matches[0].toISOString();
}
