import { test } from 'node:test';
import assert from 'node:assert/strict';
import { closeTabs } from '../src/tab-state.ts';

test('bulk close keeps pinned tabs and selects the target when the active tab is removed', () => {
  const tabs = ['工作台', '商户管理', '商品管理', '用户管理'];
  const result = closeTabs(tabs, ['工作台', '商户管理'], '用户管理', '商品管理', 'right');
  assert.deepEqual(result, { tabs: ['工作台', '商户管理', '商品管理'], active: '商品管理' });
});

test('close all preserves pinned tabs and chooses the first remaining tab', () => {
  const result = closeTabs(['工作台', '商户管理', '商品管理'], ['工作台', '商户管理'], '商品管理', '商品管理', 'all');
  assert.deepEqual(result, { tabs: ['工作台', '商户管理'], active: '工作台' });
});

test('closing other or left tabs never removes pinned tabs', () => {
  const tabs = ['工作台', '商户管理', '商品管理', '用户管理'];
  assert.deepEqual(closeTabs(tabs, ['工作台', '商品管理'], '商户管理', '用户管理', 'left').tabs, ['工作台', '商品管理', '用户管理']);
  assert.deepEqual(closeTabs(tabs, ['工作台', '商品管理'], '商户管理', '用户管理', 'other').tabs, ['工作台', '商品管理', '用户管理']);
});
