<script setup lang="ts">
import { ref, watch } from 'vue';
import { watchToast } from './toast';
const props=defineProps<{user:{username:string;nickname:string|null;mobile:string};token:string}>();
const emit=defineEmits<{updated:[user:{username:string;nickname:string|null;mobile:string}]}>();
const nickname=ref(props.user.nickname||''),error=ref(''),notice=ref(''),busy=ref(false);
watchToast(error, 'error'); watchToast(notice, 'success');
watch(()=>props.user.nickname, value=>nickname.value=value||'');
async function save(){busy.value=true;error.value='';notice.value='';try{const response=await fetch('/api/v1/users/me',{method:'PATCH',headers:{'Content-Type':'application/json',Authorization:`Bearer ${props.token}`},body:JSON.stringify({nickname:nickname.value.trim()||null})});const data=await response.json();if(!response.ok)throw new Error(typeof data.detail==='string'?data.detail:'保存失败，请检查输入。');emit('updated',data);notice.value='昵称已保存。';}catch(e){error.value=(e as Error).message||'无法连接服务。';}finally{busy.value=false;}}
</script>
<template><main class="profile"><h1>个人中心</h1><p>查看账号信息并修改昵称</p><section><h2>基本信息</h2><form @submit.prevent="save"><label>登录账号<input :value="user.username" disabled></label><label>手机号<input :value="user.mobile" disabled></label><label>昵称<input v-model="nickname" maxlength="80" placeholder="请输入昵称"></label><button :disabled="busy">{{ busy?'保存中…':'保存修改' }}</button></form></section></main></template>
<style scoped>.profile{padding:36px 40px;max-width:900px}.profile h1{font-size:26px;margin:0}.profile>p{color:#728297;font-size:13px;margin:9px 0 24px}.profile section{background:white;border:1px solid #e5e9ef;border-radius:8px;padding:24px}.profile h2{font-size:16px;margin:0 0 24px}.profile form{max-width:420px}.profile label{display:block;font-size:13px;margin:16px 0;color:#42546a}.profile input{display:block;width:100%;padding:10px;margin-top:8px;border:1px solid #dbe3ec;border-radius:5px;font:inherit}.profile input:disabled{background:#f5f7fa;color:#8190a0}.profile button{background:#0073e6;border:0;color:white;padding:10px 18px;border-radius:5px;cursor:pointer}.error{color:#ba3e3e}.notice{color:#32845a}button:focus-visible,input:focus-visible{outline:2px solid #0073e6;outline-offset:2px}@media(max-width:700px){.profile{padding:24px 16px}}
.profile{flex:1;max-width:none;min-height:0;padding:20px;background:#f0f2f5}.profile>h1,.profile>p{margin:0;background:#fff;padding:20px 20px 0;font-size:18px}.profile>p{padding:8px 20px 20px;font-size:13px;color:#8290a3}.profile section{margin-top:14px;min-height:320px;border:0;border-radius:0 0 6px 6px;padding:24px 20px}.profile h2{color:#172233;font-size:18px}.profile input{border-color:#dce3ed;border-radius:6px;box-sizing:border-box}.profile button{background:#5267ff;border-radius:5px}.profile button:hover{background:#4054ed}.profile button:focus-visible,.profile input:focus-visible{outline-color:#5267ff}@media(max-width:700px){.profile{padding:12px}.profile section{padding:20px}}

.profile input,.profile button{box-sizing:border-box;height:40px;font-size:14px}.profile button{min-width:72px;padding:0 16px;display:inline-flex;align-items:center;justify-content:center;line-height:1}


.profile{padding:8px}.profile>h1{border:2px solid #d8e0ec;border-bottom:0}.profile>p{border:2px solid #d8e0ec;border-top:0}.profile section{margin-top:8px;border:2px solid #d8e0ec}@media(max-width:700px){.profile{padding:6px}.profile section{margin-top:6px}}


.profile{padding:2px}.profile section{margin-top:2px;border-radius:0}@media(max-width:700px){.profile{padding:2px}.profile section{margin-top:2px}}
</style>
