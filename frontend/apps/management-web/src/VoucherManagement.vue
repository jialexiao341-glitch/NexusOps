<script setup lang="ts">
import { onMounted, ref } from 'vue';
import MerchantSelect from './MerchantSelect.vue';
import { showToast } from './toast';
type Campaign = {id:number;merchant_id:number;title:string;sale_price:string;total_stock:number;available_stock:number;starts_at:string;ends_at:string;status:string};
type Order = {id:number;campaign_id:number;request_id:string;amount_snapshot:string;status:string};
const props=defineProps<{token:string; username:string}>();
const emit=defineEmits<{ 'open-order':[id:number] }>();
const items=ref<Campaign[]>([]), offset=ref(0), more=ref(false), loading=ref(false), busy=ref(false), error=ref(''), merchant=ref(''), showForm=ref(false);
const form=ref({merchant_id:'',title:'',sale_price:'',total_stock:'',starts_at:'',ends_at:''});
const storageKey=()=>`nexusops_voucher_requests_${props.username}`;
function requests():Record<string,string>{try{return JSON.parse(localStorage.getItem(storageKey())||'{}');}catch{return {};}}
function setRequest(id:number,value:string){const data=requests();if(value)data[id]=value;else delete data[id];localStorage.setItem(storageKey(),JSON.stringify(data));}
async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{let res:Response;try{res=await fetch('/api/v1'+path,{method,headers:{Authorization:`Bearer ${props.token}`,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify(body)});}catch{throw new Error('无法连接服务，请检查后端是否启动。');}const data=await res.json().catch(()=>({}));if(!res.ok)throw new Error(typeof data.detail==='string'?data.detail:'操作失败，请检查输入后重试。');return data as T;}
async function load(){loading.value=true;error.value='';try{const p=new URLSearchParams({offset:String(offset.value),limit:'21'});if(merchant.value)p.set('merchant_id',merchant.value);const data=await api<Campaign[]>(`/voucher-campaigns?${p}`);items.value=data.slice(0,20);more.value=data.length>20;}catch(e){error.value=(e as Error).message;}finally{loading.value=false;}}
function search(){offset.value=0;void load();}
async function create(){error.value='';if(!form.value.merchant_id){error.value='请选择所属商户。';return;}if(new Date(form.value.starts_at)>=new Date(form.value.ends_at)){error.value='结束时间须晚于开始时间。';return;}busy.value=true;try{await api('/voucher-campaigns','POST',{...form.value,merchant_id:Number(form.value.merchant_id),total_stock:Number(form.value.total_stock),starts_at:new Date(form.value.starts_at).toISOString(),ends_at:new Date(form.value.ends_at).toISOString()});showForm.value=false;form.value={merchant_id:'',title:'',sale_price:'',total_stock:'',starts_at:'',ends_at:''};showToast('活动创建成功');await load();}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
async function change(item:Campaign,action:'activate'|'close'){if(!confirm(`确定${action==='activate'?'上线':'关闭'}活动“${item.title}”吗？`))return;busy.value=true;error.value='';try{await api(`/voucher-campaigns/${item.id}/${action}`,'POST');showToast(action==='activate'?'活动已上线':'活动已关闭');await load();}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
async function buy(item:Campaign){busy.value=true;error.value='';let key=requests()[item.id];if(!key){key=crypto.randomUUID();setRequest(item.id,key);}try{const order=await api<Order>(`/voucher-campaigns/${item.id}/orders`,'POST',{request_id:key});if(order.status==='cancelled'){setRequest(item.id,'');showToast('原订单已取消，可再次抢购');}else showToast('订单已创建');await load();emit('open-order',order.id);}catch(e){error.value=(e as Error).message;}finally{busy.value=false;}}
function time(value:string){return new Date(value).toLocaleString('zh-CN',{hour12:false});}
function status(value:string){return ({draft:'草稿',active:'已上线',closed:'已关闭',created:'待支付',cancelled:'已取消'} as Record<string,string>)[value]||value;}
onMounted(load);
</script>
<template>
<section class="voucher">
  <div class="filters"><label>所属商户<MerchantSelect v-model="merchant" :token="token" label="筛选所属商户" /></label><div class="filter-actions"><button @click="merchant='';search()" :disabled="loading">重置</button><button class="primary" @click="search" :disabled="loading">搜索</button></div></div>
  <div class="panel campaign-panel"><div class="toolbar"><h2>优惠券活动</h2><div><button @click="load" :disabled="loading">刷新</button><button class="primary" @click="error='';showForm=true">＋ 新建活动</button></div></div>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <div class="table-wrap"><table><thead><tr><th>编号</th><th>活动名称</th><th>商户编号</th><th>售价</th><th>剩余 / 总库存</th><th>活动时间</th><th>状态</th><th>操作</th></tr></thead><tbody><tr v-for="item in items" :key="item.id"><td>{{ item.id }}</td><td>{{ item.title }}</td><td>{{ item.merchant_id }}</td><td>¥ {{ Number(item.sale_price).toFixed(2) }}</td><td>{{ item.available_stock }} / {{ item.total_stock }}</td><td>{{ time(item.starts_at) }}<br>至 {{ time(item.ends_at) }}</td><td><span class="status" :class="item.status">{{ status(item.status) }}</span></td><td class="row-actions"><button v-if="item.status==='draft'" @click="change(item,'activate')" :disabled="busy">上线</button><button v-if="item.status!=='closed'" @click="change(item,'close')" :disabled="busy">关闭</button><button v-if="item.status==='active'" @click="buy(item)" :disabled="busy">抢购</button></td></tr><tr v-if="!items.length"><td colspan="8" class="empty">{{ loading?'加载中…':error?'加载失败，请刷新重试':'暂无活动' }}</td></tr></tbody></table></div>
    <div class="pagination"><span>每页 20 条 · 第 {{ offset/20+1 }} 页</span><div><button :disabled="offset===0||loading" @click="offset-=20;load()">上一页</button><button :disabled="!more||loading" @click="offset+=20;load()">下一页</button></div></div>
  </div>
  <div v-if="showForm" class="overlay" @click.self="!busy && (showForm=false)"><section class="dialog" role="dialog" aria-modal="true" aria-label="新建优惠券活动"><div class="dialog-head"><h2>新建优惠券活动</h2><button aria-label="关闭" :disabled="busy" @click="showForm=false">×</button></div><form @submit.prevent="create"><label>所属商户<MerchantSelect v-model="form.merchant_id" :token="token" label="活动所属商户" /></label><label>活动名称<input v-model.trim="form.title" maxlength="120" required placeholder="请输入活动名称"></label><label>售价（元）<input v-model="form.sale_price" type="number" min="0" max="99999999.99" step="0.01" required></label><label>库存数量<input v-model="form.total_stock" type="number" min="0" step="1" required></label><label>开始时间<input v-model="form.starts_at" type="datetime-local" required></label><label>结束时间<input v-model="form.ends_at" type="datetime-local" required></label><p class="hint">时间按浏览器所在时区填写。</p><p v-if="error" class="error" role="alert">{{ error }}</p><div class="actions"><button type="button" :disabled="busy" @click="showForm=false">取消</button><button class="primary" :disabled="busy">{{ busy?'保存中…':'保存' }}</button></div></form></section></div>
</section>
</template>
<style scoped>
.voucher{flex:1;min-width:0;background:#f0f2f5;padding:2px;display:flex;flex-direction:column;gap:2px;color:#172233;font-size:14px}.filters,.panel{background:#fff;border:2px solid #d8e0ec;padding:12px}.filters,.filters label,.filter-actions,.toolbar,.pagination,.order-search,.order-result,.actions,.dialog-head{display:flex;align-items:center;gap:10px}.filters label{gap:15px}.filters label :deep(.merchant-select){width:200px}.filter-actions{margin-left:auto}.toolbar,.pagination,.dialog-head{justify-content:space-between}.toolbar{min-height:48px}.toolbar h2,.dialog h2{font-size:18px;margin:0}.toolbar>div{display:flex;gap:10px}button{height:40px;padding:0 16px;background:#fff;border:1px solid #dce3ed;border-radius:5px;color:#334155;font:inherit;cursor:pointer}button:hover:not(:disabled){color:#5267ff;border-color:#5267ff}button:disabled{opacity:.45;cursor:not-allowed}.primary{background:#5267ff;color:#fff;border-color:#5267ff}.primary:hover:not(:disabled){background:#4054ed;color:#fff}.table-wrap{overflow:auto;border:1px solid #dce4ef;border-radius:5px}table{width:100%;min-width:1050px;border-collapse:collapse;text-align:center}th,td{height:50px;padding:10px 12px;border-bottom:1px solid #dce4ef}th{background:#eef3f9;color:#344054;font-weight:600}tbody tr:hover{background:#f7f9ff}.empty{height:100px;color:#8190a3}.status{display:inline-block;padding:4px 9px;border-radius:4px;background:#f1f3f5;color:#788594}.status.active{background:#effcf3;color:#32845a}.status.draft{background:#fff8e8;color:#a77916}.row-actions{white-space:nowrap}.row-actions button{height:auto;border:0;padding:5px 7px;color:#5267ff}.pagination{padding:12px 4px 0;color:#718096;font-size:12px}.pagination button+button{margin-left:8px}.order-panel{padding:12px}.hint{font-size:13px;color:#718096}.order-search input{width:220px}.order-result{flex-wrap:wrap;margin-top:16px;padding:15px;background:#f7f9fc}.order-result span{margin-right:20px;color:#718096}.order-result strong{color:#172233;margin-left:6px}.error{color:#ba3e3e;font-size:13px}.overlay{position:fixed;inset:0;z-index:20;background:#14253c66;display:grid;place-items:center;padding:20px}.dialog{box-sizing:border-box;width:min(480px,100%);max-height:90vh;overflow:auto;background:white;border-radius:9px;padding:24px;box-shadow:0 20px 60px #15253a30}.dialog-head button{border:0;font-size:24px;padding:0 5px}.dialog label{display:block;margin:14px 0;font-size:13px}.dialog label :deep(.merchant-select){margin-top:8px}input{box-sizing:border-box;height:40px;border:1px solid #dce3ed;border-radius:5px;padding:0 12px;font:inherit;color:#172233}.dialog label>input{display:block;width:100%;margin-top:8px}.actions{justify-content:flex-end;margin-top:20px}button:focus-visible,input:focus-visible{outline:2px solid #5267ff;outline-offset:2px}@media(max-width:700px){.filters{flex-wrap:wrap}.filters label{width:100%}.filters label :deep(.merchant-select){flex:1}.order-result{align-items:flex-start;flex-direction:column}.dialog{padding:16px}}

/* 与管理列表保持一致：工具按钮按内容定宽，列表占满剩余空间。 */
.voucher{min-height:0}
.campaign-panel{display:flex;flex:1;min-height:280px;flex-direction:column}
.campaign-panel .table-wrap{flex:1;min-height:160px}
.voucher button{box-sizing:border-box;min-width:72px;flex:none;display:inline-flex;align-items:center;justify-content:center;white-space:nowrap;line-height:1;font-weight:400;letter-spacing:normal;margin:0;position:static}
.voucher button.primary{width:auto;height:40px}
.voucher .row-actions button{min-width:0}
.voucher .dialog-head button{min-width:40px}
.order-search input{width:220px;min-width:0}
@media(max-width:700px){
 .campaign-panel{min-height:360px}
 .toolbar{gap:10px;flex-wrap:wrap}
 .toolbar>div{flex-wrap:wrap}
 .order-search input{flex:1;width:auto}
 .pagination{gap:10px;flex-wrap:wrap}
}
</style>
