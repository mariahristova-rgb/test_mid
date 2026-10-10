import assert from 'node:assert/strict';
import test from 'node:test';
import { formatMinor } from '../src/services/money.mjs';
test('Bulgarian and English currency formatting preserves exact minor units', () => {
  assert.match(formatMinor('1201', 'EUR', 'en-US'), /12\.01/);
  assert.match(formatMinor('1201', 'EUR', 'bg-BG'), /12,01/);
  assert.match(formatMinor('900719925474099312', 'EUR', 'en-US'), /\.12/);
  assert.throws(() => formatMinor(900719925474099312, 'EUR', 'en-US'), RangeError);
});
