<script setup lang="ts">
import { CheckCircle2, XCircle } from '@lucide/vue';
import { toasts } from './toast';
</script>

<template>
  <Teleport to="body">
    <div class="toast-viewport" aria-live="polite" aria-relevant="additions">
      <div v-for="item in toasts" :key="item.id" class="toast" :role="item.kind === 'error' ? 'alert' : 'status'">
        <CheckCircle2 v-if="item.kind === 'success'" class="toast-icon success" aria-hidden="true" />
        <XCircle v-else class="toast-icon error" aria-hidden="true" />
        <span>{{ item.message }}</span>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-viewport{position:fixed;z-index:3000;top:20px;left:0;right:0;display:flex;align-items:center;flex-direction:column;gap:8px;padding:0 16px;pointer-events:none}.toast{display:flex;align-items:center;gap:8px;max-width:min(520px,100%);padding:10px 16px;border-radius:8px;background:#fff;box-shadow:0 6px 16px #00000014,0 3px 6px #0000001a;color:#172233;font:14px/1.5 'Microsoft YaHei',sans-serif;overflow-wrap:anywhere}.toast-icon{width:16px;height:16px;flex:none;stroke-width:2.2}.toast-icon.success{color:#52c41a}.toast-icon.error{color:#ff4d4f}
</style>
