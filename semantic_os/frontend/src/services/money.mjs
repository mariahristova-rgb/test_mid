// Display integer minor units without converting monetary values to floating point.
export function formatMinor(value, currency, locale) {
  if (typeof value === 'number' && !Number.isSafeInteger(value)) throw new RangeError('Unsafe monetary integer');
  const amount = BigInt(value);
  if (amount < 0n) throw new RangeError('Negative amounts are unsupported');
  const formatter = new Intl.NumberFormat(locale, { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fraction = String(amount % 100n).padStart(2, '0');
  return formatter.formatToParts(amount / 100n).map(part => part.type === 'fraction' ? fraction : part.value).join('');
}
