export type CloseTabScope = 'current' | 'left' | 'right' | 'other' | 'all';

export function closeTabs(tabs: string[], pinned: string[], active: string, target: string, scope: CloseTabScope) {
  const targetIndex = tabs.indexOf(target);
  if (targetIndex < 0) return { tabs, active };
  const remaining = tabs.filter((name, index) => {
    if (pinned.includes(name)) return true;
    if (scope === 'all') return false;
    if (scope === 'current') return name !== target;
    if (scope === 'left') return index >= targetIndex;
    if (scope === 'right') return index <= targetIndex;
    return name === target;
  });
  const fallback = scope === 'all' ? remaining[0] : remaining.includes(target) ? target : remaining[Math.min(targetIndex, remaining.length - 1)];
  return { tabs: remaining, active: remaining.includes(active) ? active : (fallback || '工作台') };
}
