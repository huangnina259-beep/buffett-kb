(function(global){
'use strict';
const KEY='compounder.lesson.moat.v1';
const answers=[1,2,0];
const explanations=[
 '竞争优势解释回报为什么可能持续，再投资需求影响有多少现金能取出。喜诗与 FlightSafety 的材料说明，这两个问题需要分别判断。',
 '品牌知名度提供线索，顾客在价格和替代品变化后的行为更有助于检验优势。还需要多期证据，不能凭一次观察确认持久性。',
 '竞争优势不能替代估值。还需要分析未来现金、维持与增长投入，以及价格留出的安全边际。可继续阅读“安全边际”导读。'
];
function normalize(raw){
 const x=raw&&typeof raw==='object'?raw:{};
 const clip=(s,n)=>typeof s==='string'?s.slice(0,n):'';
 const choices=answers.map((_,i)=>Number.isInteger(x.choices?.[i])&&x.choices[i]>=0&&x.choices[i]<3?x.choices[i]:null);
 const viewed=Array.isArray(x.viewed)?[...new Set(x.viewed.filter(i=>Number.isInteger(i)&&i>=0&&i<3))]:[];
 const reason=clip(x.reason,3000),understanding=clip(x.understanding,4000),next=clip(x.next,2000);
 const submitted=x.submitted===true&&choices.every(i=>i!==null)&&reason.trim().length>=20;
 return {step:Number.isInteger(x.step)&&x.step>=0&&x.step<4?x.step:0,understood:x.understood===true,viewed,read:x.read===true&&viewed.length>0,choices,reason,submitted,understanding,next,saved:x.saved===true&&understanding.trim().length>=20&&next.trim().length>=10,updated:clip(x.updated,50)};
}
function completed(s){return [s.understood,s.read,s.submitted,s.saved];}
function exportRecord(s){return '# 我的护城河学习记录\n\n'+`更新时间：${s.updated||'尚未保存'}\n\n已完成：${completed(s).filter(Boolean).length}/4 步（不代表掌握程度）\n\n`+'## 我的初次判断\n\n'+s.reason+'\n\n'+s.choices.map((x,i)=>`第 ${i+1} 题：${x===null?'未选择':String.fromCharCode(65+x)}${s.submitted?'；'+(x===answers[i]?'与本题证据一致':'值得重新检查')+'。'+explanations[i]:''}`).join('\n\n')+'\n\n## 现在的理解\n\n'+s.understanding+'\n\n## 下一步验证\n\n'+s.next+'\n\n## 原典与继续学习\n\n巴菲特 2007 年致股东信：https://www.berkshirehathaway.com/letters/2007ltr.pdf\n\n复利国护城河单元：/static/moat.html\n';}
const api={normalize,completed,exportRecord,answers};
if(typeof module!=='undefined'&&module.exports)module.exports=api;
if(!global.document)return;
const $=id=>document.getElementById(id);let state;try{state=normalize(JSON.parse(localStorage.getItem(KEY)||'{}'));}catch(e){state=normalize({});}
function save(){state.updated=new Date().toISOString();try{localStorage.setItem(KEY,JSON.stringify(state));$('storage-status').textContent='已保存在此浏览器 · 下次可继续。清理浏览器数据前请导出备份。';return true;}catch(e){$('storage-status').textContent='此浏览器无法保存。请使用“导出学习记录”保留本次内容。';return false;}}
function progress(){const done=completed(state);$('progress').textContent=`已完成 ${done.filter(Boolean).length} / 4 步`;document.querySelectorAll('[data-step]').forEach((b,i)=>{b.classList.toggle('done',done[i]);if(i===state.step)b.setAttribute('aria-current','step');else b.removeAttribute('aria-current');});}
function show(step,focus=true){state.step=step;document.querySelectorAll('[data-panel]').forEach((p,i)=>p.hidden=i!==step);progress();if(step===3)excerpts();save();if(focus)document.querySelector(`[data-panel="${step}"] h2`).focus();}
function excerpts(){let rows=[];try{const parsed=JSON.parse(localStorage.getItem('compounder.readings.v1')||'[]');if(Array.isArray(parsed))rows=parsed.filter(x=>x&&typeof x.original==='string'&&/护城河|喜诗|FlightSafety/i.test([x.focus,x.note,...(Array.isArray(x.tags)?x.tags:[])].join(' ')));}catch(e){}const root=$('saved-excerpts');root.replaceChildren();if(!rows.length){root.textContent='还没有相关摘录。回到“核对原文”，打开材料后可收藏重点并记笔记。';return;}for(const row of rows){const p=document.createElement('p');p.textContent=(row.title||'原文摘录')+' · '+(row.note||row.focus||row.original).slice(0,110);root.append(p);}}
function feedback(){const root=$('feedback');root.hidden=!state.submitted;$('practice-next').hidden=!state.submitted;if(!state.submitted)return;root.replaceChildren();const title=document.createElement('h3');title.textContent='对照证据，修正判断';root.append(title);const intro=document.createElement('p');intro.textContent='以下为预先整理的教学反馈。选择题按材料核对；你的文字回答保留供自我复盘，未由 AI 评分。';root.append(intro);explanations.forEach((text,i)=>{const p=document.createElement('p');p.textContent=`${i+1}. ${state.choices[i]===answers[i]?'这个选择与材料一致。':'这个选择需要再检查。'}${text}`;root.append(p);});const p=document.createElement('p');p.textContent='回看自己的文字：是否写清了优势的机制、可验证的证据，以及让判断失效的条件？';root.append(p);}
$('reason').value=state.reason;$('understanding').value=state.understanding;$('next-evidence').value=state.next;
state.choices.forEach((v,i)=>{const input=document.querySelector(`input[name=q${i}][value="${v}"]`);if(input)input.checked=true;});
document.querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>show(Number(b.dataset.step)));
$('understood').onclick=()=>{state.understood=true;show(1);};
$('read-done').onclick=()=>{if(!state.viewed.length){$('read-status').textContent='请先打开至少一段原文，再确认已核对。';return;}state.read=true;show(2);};
$('practice').oninput=()=>{state.reason=$('reason').value;state.choices=answers.map((_,i)=>{const v=document.querySelector(`input[name=q${i}]:checked`);return v?Number(v.value):null;});state.submitted=false;state.saved=false;feedback();progress();save();};
$('practice').onsubmit=e=>{e.preventDefault();if(!e.target.reportValidity()||state.reason.trim().length<20)return;state.submitted=true;save();feedback();progress();$('feedback').scrollIntoView({behavior:'smooth',block:'start'});};
$('practice-next').onclick=()=>show(3);
$('reflection').oninput=()=>{state.understanding=$('understanding').value;state.next=$('next-evidence').value;state.saved=false;$('completion').textContent='修改已记为草稿。整理好后点击“保存我的理解”。';save();progress();};
$('reflection').onsubmit=e=>{e.preventDefault();if(!e.target.reportValidity()||state.understanding.trim().length<20||state.next.trim().length<10)return;state.saved=true;const ok=save();progress();$('completion').textContent=(ok?'已保存你的理解。':'本次理解已整理，请导出备份。')+(completed(state).every(Boolean)?'你已走完本单元；下次回来，试着不用提示再解释一次。':'其他步骤仍可继续，完成后会保留完整的学习记录。');};
$('export').onclick=e=>{e.preventDefault();const url=URL.createObjectURL(new Blob([exportRecord(state)],{type:'text/markdown;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='复利国-我的护城河学习记录.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
let sourcesPromise;async function openSource(index,button){const dialog=$('source-dialog');dialog.showModal();$('source-title').textContent=['护城河 · 2007 年股东信','喜诗糖果 · 2007 年股东信','FlightSafety · 2007 年股东信'][index];$('reader').textContent='正在打开原文依据…';try{if(!sourcesPromise)sourcesPromise=fetch('/static/moat-sources.json?v=1').then(r=>{if(!r.ok)throw Error();return r.json();}).catch(e=>{sourcesPromise=null;throw e;});const sources=await sourcesPromise;if(!dialog.open)return;const focus=['护城河如何保护持久的资本回报？','喜诗糖果的竞争优势与再投资需求有什么关系？','FlightSafety 有竞争优势，为什么增长仍需要大量资本投入？'][index];SourceReader.show($('reader'),{...sources[index],focus},'cn');if(!state.viewed.includes(index))state.viewed.push(index);save();$('read-status').textContent=`已打开 ${state.viewed.length} / 3 份材料，请核对内容后再继续。`;}catch(e){$('reader').textContent='暂时无法加载。请关闭后重试，或通过本页出处链接阅读公开信。'}}
document.querySelectorAll('[data-source]').forEach(b=>b.onclick=()=>openSource(Number(b.dataset.source),b));$('close-source').onclick=()=>$('source-dialog').close();$('source-dialog').addEventListener('close',excerpts);
feedback();show(state.step,false);if(state.saved)$('completion').textContent='已保存上次的理解，可以继续修订。';
})(typeof window==='undefined'?globalThis:window);
