<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { watchToast } from './toast';
import { RefreshCw, Maximize, CircleHelp, ChevronDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from '@lucide/vue';

type User = { id:number; username:string; nickname:string|null; mobile:string; created_at:string; status:string; platform_admin:boolean; super_admin:boolean };
type Member = { user_id:number; merchant_id:number; role:'admin'|'staff'; status:string };
const props = defineProps<{ token:string }>();
const keyword = ref(''), status = ref(''), appliedKeyword = ref(''), appliedStatus = ref('');
const total = ref(0), showMembers = ref(false), showCreate = ref(false), creating = ref(false), createError = ref(''), tablePanel = ref<HTMLElement|null>(null);
const users = ref<User[]>([]), members = ref<Member[]>([]), offset = ref(0), hasNext = ref(false);
const merchantInput = ref(''), merchantId = ref<number|null>(null), memberUserId = ref('');
const role = ref<'admin'|'staff'>('staff'), error = ref(''), notice = ref('');
const userError = ref(''), busy = ref(false), loadingUsers = ref(false), platformAdmin = ref(false);
watchToast(error, 'error'); watchToast(notice, 'success'); watchToast(userError, 'error'); watchToast(createError, 'error');
const newUser = ref({username:'', mobile:'', nickname:'', password:''});
const confirmation = ref<{ title:string; message:string; run:()=>Promise<void> } | null>(null);
function askConfirmation(title:string, message:string, run:()=>Promise<void>) { confirmation.value={title,message,run}; }
async function confirmAction() { const action=confirmation.value; if(!action || busy.value) return; confirmation.value=null; await action.run(); }
function closeCreate() { if (creating.value) return; showCreate.value=false; createError.value=''; newUser.value={username:'',mobile:'',nickname:'',password:''}; }
async function createUser() {
  creating.value=true; createError.value='';
  try {
    await api('/admin/users','POST',{username:newUser.value.username.trim(),mobile:newUser.value.mobile.trim(),nickname:newUser.value.nickname.trim() || null,password:newUser.value.password});
    creating.value=false; closeCreate(); keyword.value=''; status.value=''; appliedKeyword.value=''; appliedStatus.value=''; offset.value=0; await loadUsers(); notice.value='用户已创建';
  } catch (e) { createError.value=e instanceof Error?e.message:'创建失败，请重试'; }
  finally { creating.value=false; }
}
function openMemberAccess(item:User) { memberUserId.value=String(item.id); showMembers.value=true; }
function toggleFullscreen() { if(document.fullscreenElement) void document.exitFullscreen(); else void tablePanel.value?.requestFullscreen(); }

async function api(path:string, method='GET', body?:unknown) {
  const response = await fetch('/api/v1'+path, {method, headers:{Authorization:`Bearer ${props.token}`, ...(body===undefined?{}:{'Content-Type':'application/json'})}, ...(body===undefined?{}:{body:JSON.stringify(body)})});
  if (!response.ok) { const data = await response.json().catch(()=>({})); throw new Error(typeof data.detail==='string'?data.detail:'操作失败，请重试'); }
  return response.status===204 ? null : response.json();
}
async function loadUsers() {
  loadingUsers.value=true; userError.value='';
  try { const params=new URLSearchParams({offset:String(offset.value),limit:'21'}); if(appliedKeyword.value) params.set('keyword',appliedKeyword.value); if(appliedStatus.value) params.set('status',appliedStatus.value); const response=await fetch(`/api/v1/admin/users?${params}`,{headers:{Authorization:`Bearer ${props.token}`}}); if(!response.ok) { const data=await response.json().catch(()=>({})); throw new Error(typeof data.detail==='string'?data.detail:'无法加载用户'); } const data:User[]=await response.json(); users.value=data.slice(0,20); total.value=Number(response.headers.get('X-Total-Count') || 0); hasNext.value=offset.value+20<total.value; }
  catch (e) { users.value=[]; userError.value=e instanceof Error?e.message:'无法加载用户'; }
  finally { loadingUsers.value=false; }
}
async function loadPermissions() {
  try { const data=await api('/users/me/permissions'); platformAdmin.value=data.platform_roles.includes('platform_admin'); if(platformAdmin.value) await loadUsers(); }
  catch (e) { userError.value=e instanceof Error?e.message:'无法加载权限'; }
}
onMounted(loadPermissions);
async function perform(fn:()=>Promise<void>) {
  busy.value=true; error.value=''; notice.value='';
  try { await fn(); } catch(e) { error.value=e instanceof Error?e.message:'操作失败'; } finally { busy.value=false; }
}
async function searchMembers() {
  merchantId.value=null; members.value=[];
  await perform(async()=>{ if(!/^[1-9]\d*$/.test(merchantInput.value)) throw new Error('请输入有效的商户编号'); const id=Number(merchantInput.value); const data:Member[]=await api(`/merchants/${id}/members`); merchantId.value=id; members.value=data; });
}
async function reloadMembers() { if(merchantId.value!==null) members.value=await api(`/merchants/${merchantId.value}/members`); }
async function addMember() {
  await perform(async()=>{ if(merchantId.value===null) throw new Error('请先查询商户'); if(!/^[1-9]\d*$/.test(memberUserId.value)) throw new Error('请输入有效的用户编号'); await api(`/merchants/${merchantId.value}/members`,'POST',{user_id:Number(memberUserId.value),role:role.value}); memberUserId.value=''; await reloadMembers(); notice.value='成员已添加'; });
}
function changeRole(member:Member, next:'admin'|'staff') {
  if(next===member.role) return;
  askConfirmation('调整商户角色', `确定将用户 ${member.user_id} 的商户角色调整为${next==='admin'?'管理员':'员工'}吗？`, async()=>{
    await perform(async()=>{ await api(`/merchants/${merchantId.value}/members/${member.user_id}`,'PATCH',{role:next}); await reloadMembers(); notice.value='商户角色已更新'; });
  });
}
function removeMember(member:Member) {
  askConfirmation('移除商户成员', `确定移除用户 ${member.user_id} 的商户成员资格吗？`, async()=>{
    await perform(async()=>{ await api(`/merchants/${merchantId.value}/members/${member.user_id}`,'DELETE'); await reloadMembers(); notice.value='成员已移除'; });
  });
}
function toggleAdmin(user:User) {
  if(user.super_admin) return;
  const action=user.platform_admin?'撤销':'授予';
  askConfirmation(`${action}管理员权限`, `确定${action}用户 ${user.username} 的平台管理员权限吗？`, async()=>{
    await perform(async()=>{ await api(`/admin/users/${user.id}/platform-admin`,user.platform_admin?'DELETE':'PUT'); await loadPermissions(); notice.value='平台角色已更新'; });
  });
}
function searchUsers() { appliedKeyword.value=keyword.value.trim(); appliedStatus.value=status.value; offset.value=0; void loadUsers(); }
function resetUsers() { keyword.value=''; status.value=''; searchUsers(); }
function page(delta:number) { offset.value+=delta*20; void loadUsers(); }
</script>

<template>
  <main class="access-page">
    <form class="filters" @submit.prevent="searchUsers"><div class="filter-fields"><label>关键字<input v-model="keyword" placeholder="请输入账号名或姓名"></label><label>状态<select v-model="status"><option value="">全部状态</option><option value="active">启用</option><option value="inactive">停用</option></select></label></div><div class="filter-actions"><button type="button" class="secondary" :disabled="loadingUsers || !platformAdmin" @click="resetUsers">重置</button><button class="primary" :disabled="loadingUsers || !platformAdmin">搜索</button></div></form>
    <section ref="tablePanel" class="panel users-panel">
      <div class="heading"><div><h2>系统用户</h2></div><div class="toolbar"><button class="primary" :disabled="!platformAdmin" @click="showCreate=true">＋ 新增用户</button><button class="tool" :disabled="loadingUsers || !platformAdmin" aria-label="刷新用户列表" title="刷新" @click="loadUsers"><RefreshCw /></button><button class="tool" aria-label="全屏显示用户列表" title="全屏" @click="toggleFullscreen"><Maximize /></button><button v-if="!platformAdmin" class="secondary" @click="showMembers=true">商户成员授权</button></div></div>



      <div class="table-wrap user-table"><table><thead><tr><th>账号名</th><th>显示姓名</th><th>角色身份</th><th>邮箱</th><th>手机号</th><th>状态</th><th>创建日期</th><th>操作</th></tr></thead><tbody><tr v-for="item in users" :key="item.id"><td>{{ item.username }}</td><td>{{ item.nickname || '—' }}</td><td>{{ item.super_admin?'超级管理员':item.platform_admin?'平台管理员':'普通用户' }}</td><td>—</td><td>{{ item.mobile }}</td><td><span class="badge" :class="{active:item.status==='active'}">{{ item.status==='active'?'启用':'停用' }}</span></td><td>{{ item.created_at.slice(0,10) }}</td><td class="row-actions"><button v-if="!item.super_admin" class="link" :disabled="busy || (item.status!=='active' && !item.platform_admin)" @click="toggleAdmin(item)">{{ item.platform_admin?'撤销管理员':'设为管理员' }}</button><button class="link" @click="openMemberAccess(item)">商户授权</button></td></tr><tr v-if="!users.length"><td colspan="8" class="empty">{{ loadingUsers?'加载中…':!platformAdmin?'平台管理员可查看用户及管理平台权限':'暂无用户' }}</td></tr></tbody></table></div>
      <div class="pagination"><div class="page-count"><span>共 {{ total }} 条记录</span><span class="page-size">20条/页 <ChevronDown :size="15" /></span></div><div class="page-controls"><button :disabled="offset===0 || loadingUsers" aria-label="第一页" @click="offset=0;loadUsers()"><ChevronsLeft /></button><button :disabled="offset===0 || loadingUsers" aria-label="上一页" @click="page(-1)"><ChevronLeft /></button><span class="current-page">{{ offset/20+1 }}</span><button :disabled="!hasNext || loadingUsers" aria-label="下一页" @click="page(1)"><ChevronRight /></button><button :disabled="!hasNext || loadingUsers" aria-label="最后一页" @click="offset=Math.max(0,(Math.ceil(total/20)-1)*20);loadUsers()"><ChevronsRight /></button></div></div>
    </section>
    <div v-if="showCreate" class="overlay" @click.self="closeCreate"><section class="panel create-dialog" role="dialog" aria-modal="true" aria-labelledby="create-user-title">
      <div class="heading"><h2 id="create-user-title">新增用户</h2><button class="close" type="button" aria-label="关闭" :disabled="creating" @click="closeCreate">×</button></div>
      <form class="create-form" @submit.prevent="createUser"><label>账号名<input v-model.trim="newUser.username" required minlength="3" maxlength="64" pattern="[A-Za-z0-9_]+" autocomplete="off" placeholder="3–64 位字母、数字或下划线"></label><label>手机号<input v-model.trim="newUser.mobile" required pattern="1[3-9][0-9]{9}" inputmode="numeric" maxlength="11" placeholder="请输入手机号"></label><label>显示姓名（选填）<input v-model.trim="newUser.nickname" maxlength="80" placeholder="请输入显示姓名"></label><label>初始密码<input v-model="newUser.password" required type="password" minlength="8" maxlength="128" autocomplete="new-password" placeholder="至少 8 位"></label><p class="hint">验证码登录成功后手机号将标记为已验证；新用户默认为普通用户。</p><div class="dialog-actions"><button type="button" class="secondary" :disabled="creating" @click="closeCreate">取消</button><button class="primary" :disabled="creating">{{ creating?'创建中…':'创建用户' }}</button></div></form>
    </section></div>
    <div v-if="showMembers" class="overlay" @click.self="showMembers=false"><section class="panel members" role="dialog" aria-modal="true" aria-label="商户成员授权">
      <div class="heading"><div><h2>商户成员授权</h2><p>平台管理员或商户管理员可管理指定商户的成员</p></div><button class="close" aria-label="关闭" @click="showMembers=false">×</button></div>
      <form class="fields" @submit.prevent="searchMembers"><label>商户编号<input v-model.trim="merchantInput" inputmode="numeric" placeholder="请输入商户编号"></label><button class="primary" :disabled="busy">查询成员</button></form>

      <template v-if="merchantId!==null"><div class="subheading"><h3>商户 {{ merchantId }} 的成员</h3></div><form class="fields add" @submit.prevent="addMember"><label>用户编号<input v-model.trim="memberUserId" inputmode="numeric" placeholder="请输入用户编号"></label><label>商户角色<select v-model="role"><option value="staff">员工</option><option value="admin">管理员</option></select></label><button class="primary" :disabled="busy">添加成员</button></form>
        <div class="table-wrap"><table><thead><tr><th>用户编号</th><th>商户角色</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="member in members" :key="member.user_id"><td>{{ member.user_id }}</td><td><span class="badge" :class="{admin:member.role==='admin'}">{{ member.role==='admin'?'管理员':'员工' }}</span></td><td>{{ member.status==='active'?'启用':'停用' }}</td><td><button class="link" :disabled="busy" @click="changeRole(member,member.role==='admin'?'staff':'admin')">{{ member.role==='admin'?'设为员工':'设为管理员' }}</button><button class="link danger" :disabled="busy" @click="removeMember(member)">移除</button></td></tr><tr v-if="!members.length"><td colspan="4" class="empty">暂无成员</td></tr></tbody></table></div>
      </template>
      <p v-else class="hint">输入商户编号后查看和管理成员。</p>
    </section></div>
    <div v-if="confirmation" class="overlay confirm-overlay" @click.self="confirmation=null"><section class="confirm-dialog" role="alertdialog" aria-modal="true" aria-labelledby="confirm-title" aria-describedby="confirm-message"><div class="confirm-body"><CircleHelp class="confirm-icon" aria-hidden="true" /><div><h2 id="confirm-title">{{ confirmation.title }}</h2><p id="confirm-message">{{ confirmation.message }}</p></div></div><div class="confirm-actions"><button type="button" class="secondary" @click="confirmation=null">取消</button><button type="button" class="primary" @click="confirmAction">确定</button></div></section></div>
  </main>
</template>
<style scoped>
.access-page{flex:1;min-height:0;overflow:auto;background:#f0f2f5;padding:2px;display:flex;flex-direction:column;gap:2px;color:#172233}.filters{display:flex;align-items:center;justify-content:space-between;gap:20px;flex-wrap:wrap;background:#fff;border:2px solid #d8e0ec;padding:18px 20px}.filter-fields,.filter-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap}.filter-fields{gap:30px}.filter-fields label{display:flex;align-items:center;gap:12px;font-size:14px}.filter-fields input,.filter-fields select{box-sizing:border-box;height:38px;border:1px solid #dce3ed;border-radius:5px;background:#fff;padding:0 12px;font:inherit;color:#172233}.filter-fields input{width:240px}.filter-fields select{width:170px}.filter-fields input::placeholder{color:#a8b4c3}.panel{background:#fff;border:2px solid #d8e0ec;padding:18px 20px}.heading,.subheading,.pagination{display:flex;align-items:center;justify-content:space-between;gap:12px}.heading{margin-bottom:18px}.heading h2{font-size:18px;margin:0}.heading p,.hint{font-size:13px;color:#718096;margin:7px 0 0}.subheading h3{font-size:15px;margin:20px 0 12px}.fields{display:flex;align-items:end;gap:12px;flex-wrap:wrap}.fields label{display:flex;flex-direction:column;gap:6px;font-size:13px;color:#48596e}.fields input,.fields select{height:38px;min-width:180px;box-sizing:border-box;padding:0 10px;border:1px solid #dce3ed;border-radius:5px;background:#fff;color:#172233;font:inherit}.add{margin-bottom:14px}.primary,.secondary{height:38px;padding:0 16px;border-radius:5px;font:inherit;cursor:pointer}.primary{border:1px solid #5267ff;background:#5267ff;color:#fff}.secondary{border:1px solid #dce3ed;background:#fff;color:#334155}.primary:disabled,.secondary:disabled,.link:disabled{opacity:.45;cursor:not-allowed}.table-wrap{overflow:auto;border:1px solid #dce4ef;border-radius:5px}table{width:100%;min-width:600px;border-collapse:collapse;text-align:center;font-size:14px}th,td{height:50px;padding:8px 14px;border-bottom:1px solid #dce4ef}th{background:#eef3f9;color:#344054;font-weight:600}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:#f7f9ff}.badge{display:inline-block;padding:3px 9px;border-radius:4px;background:#f1f3f5;color:#5f6c7a;font-size:13px}.badge.admin{background:#eef1ff;color:#5267ff}.badge.active{background:#effcf3;color:#36b75d}.refresh{width:38px;height:38px;border:1px solid #dce3ed;border-radius:50%;background:white;color:#53647a;font-size:22px;cursor:pointer}.refresh:disabled{opacity:.45;cursor:not-allowed}.link{border:0;background:none;color:#5267ff;cursor:pointer;padding:5px 8px;font:inherit}.danger{color:#d45f62}.empty{height:80px;color:#8c99a9}.pagination{font-size:12px;color:#718096;padding-top:12px}.pagination button+button{margin-left:8px}.error,.success{font-size:13px;margin:12px 0}.error{color:#ba3e3e}.success{color:#32845a}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #5267ff;outline-offset:2px}@media(max-width:700px){.filters{padding:14px}.filter-fields{gap:12px}.filter-fields label{flex-wrap:wrap}.filter-fields input{width:190px}.panel{padding:14px}.heading{align-items:flex-start}.fields label{flex:1;min-width:150px}.fields input,.fields select{width:100%;min-width:0}.pagination{flex-wrap:wrap}}

/* 与用户管理参考图保持一致的筛选、表格和工具栏布局。 */
.access-page .primary{width:auto;flex:none;margin:0;letter-spacing:normal;font-weight:400;position:static;transform:none}.access-page .primary span{position:static}.filter-actions{flex:none;flex-wrap:nowrap}.filter-actions button,.toolbar button{flex:none;white-space:nowrap}.toolbar{flex-wrap:nowrap;min-width:0}.heading{gap:16px}.heading h2{white-space:nowrap}
.access-page{padding:14px 10px 20px;gap:14px}.filters{min-height:92px;box-sizing:border-box;border:0;border-radius:7px;padding:20px}.filter-fields{gap:40px}.filter-fields input{width:305px}.filter-fields select{width:218px}.panel{border:0;border-radius:0;padding:10px}.users-panel{flex:1;min-height:480px;display:flex;flex-direction:column;border-radius:0 0 7px 7px}.users-panel:fullscreen{padding:20px;overflow:auto}.heading{min-height:54px;margin-bottom:0}.toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.toolbar .secondary,.toolbar .primary{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:40px}.toolbar .primary:disabled{background:#5267ff;color:#fff;opacity:.55}.tool{width:38px;height:38px;display:inline-grid;place-items:center;border:1px solid #dce3ed;border-radius:50%;background:#fff;color:#192638;cursor:pointer}.tool svg{width:18px;height:18px;stroke-width:1.8}.tool.search-tool{background:#5267ff;border-color:#5267ff;color:white}.tool:disabled{opacity:.5;cursor:not-allowed}.user-table{flex:1;min-height:240px;border-radius:4px}.user-table table{min-width:1100px;border-collapse:separate;border-spacing:0}.user-table th,.user-table td{box-sizing:border-box;height:50px;padding:8px 12px}.user-table th{position:sticky;top:0;z-index:1}.user-table th:not(:last-child)::after{content:'';position:absolute;right:0;top:12px;bottom:12px;width:1px;background:#dce4ef}.check-cell{width:58px}.check-cell input{width:19px;height:19px;accent-color:#5267ff;vertical-align:middle}.user-table th:last-child,.user-table td:last-child{position:sticky;right:0;min-width:230px;background:#fff;box-shadow:-5px 0 10px #26344812}.user-table th:last-child{z-index:3;background:#eef3f9}.user-table td:last-child{z-index:1}.row-actions{white-space:nowrap}.pagination{padding:14px 6px 4px;color:#172233;font-size:14px}.page-count,.page-controls{display:flex;align-items:center;gap:14px}.page-size{display:inline-flex;align-items:center;justify-content:space-between;min-width:125px;padding:7px 10px;border:1px solid #dce3ed;border-radius:5px;color:#334155}.page-controls{gap:7px}.page-controls button{display:grid;place-items:center;width:34px;height:36px;border:0;background:transparent;color:#52637a;cursor:pointer}.page-controls button:disabled{opacity:.4;cursor:not-allowed}.page-controls svg{width:18px;height:18px}.current-page{display:grid;place-items:center;width:38px;height:38px;background:#5267ff;border-radius:4px;color:white}.overlay{position:fixed;inset:0;z-index:50;display:grid;place-items:center;background:#14253c66;padding:20px}.members{width:min(760px,100%);max-height:85vh;overflow:auto;padding:20px;border-radius:6px;box-shadow:0 20px 60px #15253a30}.members .heading{margin-bottom:14px}.close{border:0;background:none;color:#718096;font-size:26px;cursor:pointer}@media(max-width:700px){.access-page{padding:10px;gap:10px}.filters{padding:14px}.filter-fields{gap:12px}.filter-fields input{width:190px}.filter-fields select{width:160px}.toolbar{justify-content:flex-end}.users-panel{min-height:380px}.user-table{max-height:none}.pagination{gap:12px}}

@media(min-width:1000px){.filters,.filter-fields,.filter-actions,.toolbar{flex-wrap:nowrap}.toolbar{justify-content:flex-end}.heading{flex-wrap:nowrap}}

.create-dialog{width:min(480px,100%);max-height:85vh;overflow:auto;padding:20px 24px;border-radius:6px;box-shadow:0 20px 60px #15253a30}.create-dialog .heading{margin-bottom:12px}.create-form{display:grid;gap:14px}.create-form label{display:grid;gap:6px;font-size:13px;color:#48596e}.create-form input{width:100%;height:40px;box-sizing:border-box;padding:0 10px;border:1px solid #dce3ed;border-radius:5px;background:#fff;color:#172233;font:inherit}.create-form .hint{margin:0;line-height:1.5}.dialog-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:4px}.create-form input:focus-visible{outline:2px solid #5267ff;outline-offset:2px}

/* 与商户、商品管理页保持相同的画布和面板间距。 */
.access-page{padding:2px;gap:2px}.filters{min-height:68px;padding:10px 12px;border:2px solid #d8e0ec;border-radius:0}.filter-fields{gap:20px}.filter-fields label{gap:15px}.filter-fields input{width:270px}.filter-fields input,.filter-fields select{height:40px}.users-panel{min-height:400px;padding:4px;border:2px solid #d8e0ec;border-radius:0}.users-panel>.heading{min-height:52px;padding-bottom:4px}.pagination{padding:8px 4px}.filter-actions .primary,.filter-actions .secondary{min-width:72px;height:40px}
@media(max-width:700px){.access-page{padding:2px;gap:2px}.filters{padding:10px}.filter-fields{gap:12px}.filter-fields input{width:190px}.users-panel{padding:4px}}

.confirm-overlay{z-index:60}.confirm-dialog{width:min(416px,100%);padding:24px;background:#fff;border-radius:8px;box-shadow:0 8px 28px #00000024;color:#172233}.confirm-body{display:flex;align-items:flex-start;gap:14px}.confirm-icon{width:22px;height:22px;flex:none;color:#faad14}.confirm-body h2{margin:0;font-size:16px;line-height:22px;font-weight:600}.confirm-body p{margin:10px 0 0;font-size:14px;line-height:1.6;color:#48596e;overflow-wrap:anywhere}.confirm-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:24px}.confirm-actions .primary,.confirm-actions .secondary{height:32px;padding:0 15px;font-size:14px}
</style>
