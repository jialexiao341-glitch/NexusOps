import { test } from 'node:test';
import assert from 'node:assert/strict';
import { showToast, toasts, dismissToast } from '../src/toast.ts';

test('messages disappear independently and can be dismissed early', async () => {
  const first = showToast('保存成功', 'success', 20);
  const second = showToast('保存失败', 'error', 1000);
  assert.deepEqual(toasts.value.map(item => item.id), [first, second]);
  await new Promise(resolve => setTimeout(resolve, 60));
  assert.deepEqual(toasts.value.map(item => item.id), [second]);
  dismissToast(second);
  assert.equal(toasts.value.length, 0);
});

test('repeated identical messages refresh one visible notification', () => {
  const first = showToast('库存已更新', 'success', 1000);
  const second = showToast('库存已更新', 'success', 1000);
  assert.equal(first, second);
  assert.equal(toasts.value.length, 1);
  dismissToast(first);
});
