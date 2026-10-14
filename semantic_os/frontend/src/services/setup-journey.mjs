/** Customer stage order over the existing persisted 0..6 draft contract. */
const order=[1,2,0,3,4,5,6];
export const stageTargets=[1,0,3,5,6];
export function customerStage(step){return ({1:0,2:0,0:1,3:2,4:2,5:3,6:4})[step]??0;}
export function adjacentStep(step,direction){const index=order.indexOf(step);return order[Math.max(0,Math.min(order.length-1,index+direction))];}
export function parseFaqImport(text,currentCount=0){
  if(text.length>100000)throw Error('faqImportInvalid');
  const entries=JSON.parse(text);
  const fields=['question_bg','question_en','answer_bg','answer_en'];
  if(!Array.isArray(entries)||!entries.length||entries.length+currentCount>20)throw Error('faqImportInvalid');
  return entries.map(entry=>{
    if(!entry||typeof entry!=='object'||Object.keys(entry).length!==4||fields.some(key=>typeof entry[key]!=='string'||!entry[key].trim()||entry[key].length>(key.startsWith('question')?500:2000)))throw Error('faqImportInvalid');
    return Object.fromEntries(fields.map(key=>[key,entry[key].trim()]));
  });
}
