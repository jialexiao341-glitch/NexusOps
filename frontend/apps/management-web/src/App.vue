<script setup lang="ts">
import { ref, watch } from 'vue';
import ToastViewport from './ToastViewport.vue';
import { showToast } from './toast';
import Workspace from './Workspace.vue';

type Mode = 'password' | 'sms' | 'register';
type User = { username: string; nickname: string | null; mobile: string; avatar: string | null };
const mode = ref<Mode>('password');
const username = ref(''); const password = ref(''); const mobile = ref(''); const code = ref(''); const nickname = ref('');
const showPassword = ref(false); const busy = ref(false); const sending = ref(false); const message = ref(''); const notice = ref('');
watch(message, value => { if (value) showToast(value, 'error'); }, { flush:'sync' });
watch(notice, value => { if (value && !value.startsWith('模拟验证码：')) showToast(value, 'success'); }, { flush:'sync' });
const currentUser = ref<User | null>(null);
const token = ref(sessionStorage.getItem('nexusops_token') || '');

async function request<T>(url: string, data?: unknown, accessToken?: string): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1${url}`, { method: data === undefined ? 'GET' : 'POST', headers: { ...(data === undefined ? {} : { 'Content-Type': 'application/json' }), ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}) }, ...(data === undefined ? {} : { body: JSON.stringify(data) }) });
  } catch { throw new Error('无法连接服务，请确认后端已经启动。'); }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : '输入信息有误，请检查后重试。');
  return body as T;
}
async function loadUser() {
  try { currentUser.value = await request<User>('/users/me', undefined, token.value); }
  catch { token.value = ''; sessionStorage.removeItem('nexusops_token'); }
}
if (token.value) void loadUser();
function selectMode(value: Mode) { mode.value = value; message.value = ''; notice.value = ''; code.value = ''; }
async function sendCode() {
  if (!/^1[3-9]\d{9}$/.test(mobile.value)) { message.value = '请输入有效的 11 位手机号。'; return; }
  message.value = ''; notice.value = ''; sending.value = true;
  try { const result = await request<{code: string}>('/auth/codes', { mobile: mobile.value, purpose: mode.value === 'register' ? 'register' : 'login' }); notice.value = `模拟验证码：${result.code}（仅用于开发测试）`; }
  catch (error) { message.value = (error as Error).message; } finally { sending.value = false; }
}
async function submit() {
  message.value = ''; notice.value = ''; busy.value = true;
  try {
    if (mode.value === 'register') {
      await request('/auth/register', { mobile: mobile.value, code: code.value, username: username.value, password: password.value, nickname: nickname.value || null });
      mode.value = 'password'; password.value = ''; code.value = ''; notice.value = '注册成功，请使用账号和密码登录。'; return;
    }
    const result = await request<{access_token: string}>(mode.value === 'password' ? '/auth/login' : '/auth/login/sms', mode.value === 'password' ? { username: username.value, password: password.value } : { mobile: mobile.value, code: code.value });
    token.value = result.access_token; sessionStorage.setItem('nexusops_token', token.value);
    const url = new URL(window.location.href);
    url.searchParams.delete('tab');
    window.history.replaceState(window.history.state, '', url);
    await loadUser();
    if (!currentUser.value) throw new Error('获取用户信息失败，请重新登录。');
  } catch (error) { message.value = (error as Error).message; } finally { busy.value = false; }
}
function logout() { token.value = ''; currentUser.value = null; sessionStorage.removeItem('nexusops_token'); password.value = ''; notice.value = '已退出登录。'; }
</script>

<template>
  <ToastViewport />
  <Workspace v-if="currentUser" :user="currentUser" :token="token" @updated="currentUser = $event" @logout="logout" />
  <main v-else class="page">
    <section class="story" aria-label="NexusOps 品牌介绍">
      <div class="story-grid" aria-hidden="true"></div>
      <div class="brand"><img src="/logo.svg" alt=""><span>Nexus<span class="brand-light">Ops</span></span><i></i><small>智慧商圈运营平台</small></div>
      <div class="story-copy"><div class="eyebrow"><span></span> 让经营更有章法</div><h1>让每一家小店<br><em>都能从容经营。</em></h1><p>连接商户、交易与服务，<br>让每一次用心经营，都有迹可循。</p></div>
      <div class="story-foot"><span>用心连接每一门好生意</span><div><b></b> NEXUSOPS <strong> / </strong> LOCAL COMMERCE</div></div>
    </section>
    <section class="auth-panel">
      <header class="mobile-brand"><img src="/logo.svg" alt=""><span>NexusOps</span></header>
      <div class="panel-top">商家与平台工作台 <span>·</span> 欢迎使用</div>
      <div class="auth-content">
        <p class="section-label">WELCOME TO NEXUSOPS</p><h2>{{ mode === 'register' ? '创建你的账号' : '欢迎回来' }}<span class="heading-dot">.</span></h2><p class="intro">{{ mode === 'register' ? '从一个账号开始，连接你的商圈生活。' : '登录你的账号，继续管理你的业务。' }}</p>
        <div v-if="mode !== 'register'" class="tabs" role="tablist" aria-label="登录方式"><button type="button" role="tab" :aria-selected="mode === 'password'" :class="{active:mode==='password'}" @click="selectMode('password')">账号登录</button><button type="button" role="tab" :aria-selected="mode === 'sms'" :class="{active:mode==='sms'}" @click="selectMode('sms')">验证码登录</button></div>
        <form @submit.prevent="submit" class="form" :class="{registration:mode==='register'}">
          <label v-if="mode !== 'password'" for="mobile">手机号<input id="mobile" v-model.trim="mobile" inputmode="numeric" autocomplete="tel" maxlength="11" placeholder="请输入手机号" required></label>
          <label v-if="mode !== 'password'" for="code">验证码<span class="code-field"><input id="code" v-model.trim="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" placeholder="请输入验证码" required><button type="button" :disabled="sending" @click="sendCode">{{ sending ? '获取中' : '获取验证码' }}</button></span></label>
          <label v-if="mode !== 'sms'" for="username">账号<input id="username" v-model.trim="username" autocomplete="username" placeholder="请输入登录账号" required></label>
          <label v-if="mode !== 'sms'" for="password">密码<span class="password-field"><input id="password" v-model="password" :type="showPassword ? 'text' : 'password'" :autocomplete="mode === 'register' ? 'new-password' : 'current-password'" :placeholder="mode === 'register' ? '请设置至少 8 位密码' : '请输入密码'" :minlength="mode === 'register' ? 8 : undefined" required><button type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword">{{ showPassword ? '隐藏' : '显示' }}</button></span></label>
          <label v-if="mode === 'register'" for="nickname">昵称 <span class="optional">选填</span><input id="nickname" v-model.trim="nickname" maxlength="80" placeholder="怎么称呼你"></label>
          <p v-if="notice.startsWith('模拟验证码：')" class="feedback notice" role="status">{{ notice }}</p>
          <button class="primary" :disabled="busy" type="submit">{{ busy ? '请稍候…' : mode === 'register' ? '创建账号' : '登 录' }}<span>↗</span></button>
        </form>
        <p class="switch">{{ mode === 'register' ? '已有账号？' : '还没有账号？' }} <button type="button" @click="selectMode(mode === 'register' ? 'password' : 'register')">{{ mode === 'register' ? '返回登录' : '立即注册' }} <span>→</span></button></p>
      </div>
      <footer class="auth-footer"><span>© {{ new Date().getFullYear() }} NexusOps</span><span>让好生意持续发生</span></footer>
    </section>
  </main>
</template>


