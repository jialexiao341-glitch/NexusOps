import { ref, watch, type Ref } from 'vue';

type ToastKind = 'success' | 'error';
type Toast = { id: number; message: string; kind: ToastKind };
export const toasts = ref<Toast[]>([]);
const timers = new Map<number, ReturnType<typeof setTimeout>>();
let nextId = 0;

export function dismissToast(id: number) {
  const timer = timers.get(id);
  if (timer !== undefined) clearTimeout(timer);
  timers.delete(id);
  toasts.value = toasts.value.filter(item => item.id !== id);
}

export function showToast(message: string, kind: ToastKind = 'success', duration = 3000) {
  const existing = toasts.value.find(item => item.message === message && item.kind === kind);
  if (existing) {
    const timer = timers.get(existing.id);
    if (timer !== undefined) clearTimeout(timer);
    timers.set(existing.id, setTimeout(() => dismissToast(existing.id), duration));
    return existing.id;
  }
  const id = ++nextId;
  toasts.value.push({ id, message, kind });
  timers.set(id, setTimeout(() => dismissToast(id), duration));
  return id;
}

export function watchToast(source: Ref<string>, kind: ToastKind) {
  watch(source, value => { if (value) showToast(value, kind); }, { flush: 'sync' });
}
