<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';

type Merchant = { id: number; name: string };
const props = defineProps<{ modelValue: string; token: string; label: string }>();
const emit = defineEmits<{ 'update:modelValue': [value: string] }>();
const query = ref(''), items = ref<Merchant[]>([]), open = ref(false), loading = ref(false), error = ref(''), hasMore = ref(false), active = ref(-1);
let sequence = 0, timer: ReturnType<typeof setTimeout> | undefined;
const pageSize = 20;
async function search(append = false) {
  const request = ++sequence;
  loading.value = true; error.value = '';
  const keyword = props.modelValue && query.value.endsWith(`（ID: ${props.modelValue}）`) ? '' : query.value.trim();
  const params = new URLSearchParams({ keyword, offset: String(append ? items.value.length : 0), limit: String(pageSize + 1) });
  try {
    const response = await fetch(`/api/v1/merchants/manageable?${params}`, { headers: { Authorization: `Bearer ${props.token}` } });
    if (!response.ok) throw new Error('商户加载失败，请重试');
    const data: Merchant[] = await response.json();
    if (request !== sequence) return;
    items.value = append ? [...items.value, ...data.slice(0, pageSize)] : data.slice(0, pageSize);
    hasMore.value = data.length > pageSize; active.value = -1;
  } catch {
    if (request === sequence) { error.value = '商户加载失败，请重试'; if (!append) items.value = []; }
  } finally { if (request === sequence) loading.value = false; }
}
function show() { open.value = true; void search(); }
function input(event: Event) {
  query.value = (event.target as HTMLInputElement).value;
  emit('update:modelValue', ''); open.value = true; clearTimeout(timer);
  sequence++; loading.value = true; items.value = []; hasMore.value = false;
  timer = setTimeout(() => void search(), 250);
}
function choose(item: Merchant) { query.value = `${item.name}（ID: ${item.id}）`; emit('update:modelValue', String(item.id)); open.value = false; }
function keydown(event: KeyboardEvent) {
  if (event.key === 'Escape') { open.value = false; return; }
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault(); if (!open.value) { show(); return; }
    if (items.value.length) active.value = event.key === 'ArrowDown' ? Math.min(active.value + 1, items.value.length - 1) : Math.max(active.value - 1, 0);
  } else if (event.key === 'Enter' && open.value) {
    event.preventDefault(); if (active.value >= 0 && items.value[active.value]) choose(items.value[active.value]);
  }
}
watch(() => props.modelValue, async value => {
  if (!value) { if (!open.value) query.value = ''; return; }
  if (query.value.endsWith(`（ID: ${value}）`)) return;
  try {
    const response = await fetch(`/api/v1/merchants/manageable?keyword=${encodeURIComponent(value)}&limit=100`, { headers: { Authorization: `Bearer ${props.token}` } });
    const data: Merchant[] = response.ok ? await response.json() : [];
    const item = data.find(entry => String(entry.id) === value);
    if (props.modelValue === value && item) query.value = `${item.name}（ID: ${item.id}）`;
  } catch { /* 已选编号仍保留，重新打开可重试查询。 */ }
}, { immediate: true });
onUnmounted(() => { clearTimeout(timer); sequence++; });
</script>

<template>
  <div class="merchant-select" @focusout="event => { if (!(event.currentTarget as HTMLElement).contains(event.relatedTarget as Node | null)) open = false; }">
    <input :value="query" :aria-label="label" role="combobox" aria-autocomplete="list" :aria-expanded="open" :aria-controls="open ? `${label}-options` : undefined" placeholder="搜索商户名称或编号" autocomplete="off" @focus="show" @input="input" @keydown="keydown">
    <div v-if="open" class="options" :id="`${label}-options`" role="listbox">
      <button v-for="(item, index) in items" :key="item.id" type="button" role="option" :aria-selected="String(item.id) === modelValue" :class="{ highlighted: active === index }" @mousedown.prevent @click="choose(item)">{{ item.name }} <span>（ID: {{ item.id }}）</span></button>
      <div v-if="loading" class="hint">加载中…</div>
      <div v-else-if="error" class="hint">{{ error }} <button type="button" class="retry" @mousedown.prevent @click="search(false)">重试</button></div>
      <div v-else-if="!items.length" class="hint">没有可管理的商户</div>
      <button v-if="hasMore && !loading" type="button" class="more" @mousedown.prevent @click="search(true)">加载更多</button>
    </div>
  </div>
</template>

<style scoped>
.merchant-select{position:relative;width:100%;min-width:0}.merchant-select input{box-sizing:border-box;width:100%;height:40px;padding:0 12px;border:1px solid #dce3ed;border-radius:5px;background:#fff;color:#25364b;font:inherit}.merchant-select input::placeholder{color:#b8c2cf}.merchant-select input:focus-visible{outline:2px solid #5267ff;outline-offset:2px}.options{position:absolute;z-index:30;top:calc(100% + 4px);left:0;right:0;max-height:240px;overflow:auto;padding:4px;background:#fff;border:1px solid #dce3ed;border-radius:5px;box-shadow:0 4px 12px #14253c26}.options button{display:block;width:100%;padding:9px 10px;border:0;border-radius:4px;background:#fff;color:#172233;text-align:left;font:inherit;cursor:pointer}.options button:hover,.options button:focus-visible,.options button.highlighted{background:#f1f4ff;outline:none}.options button span{color:#718096}.hint{padding:10px;color:#718096;font-size:13px;white-space:normal}.options .retry{display:inline;width:auto;color:#5267ff}.options .more{text-align:center;color:#5267ff;border-top:1px solid #edf0f5}
</style>
