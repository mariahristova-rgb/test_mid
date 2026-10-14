// Exact non-monetary quantities; durations are stored in integer milliseconds.
export function measuredQuantity(text,unit,locale) {
  if(!/^\d+$/.test(String(text)))return null;
  const value=BigInt(text),format=new Intl.NumberFormat(locale);
  if(unit!=='millisecond')return format.format(value);
  const whole=format.format(value/1000n),fraction=(value%1000n).toString().padStart(3,'0').replace(/0+$/,'');
  const decimal=format.formatToParts(1.1).find(part=>part.type==='decimal')?.value||'.';
  return whole+(fraction?decimal+fraction:'');
}
