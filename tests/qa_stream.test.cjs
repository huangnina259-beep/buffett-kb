const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const html=fs.readFileSync(path.join(__dirname,'../frontend/qa.html'),'utf8');
const start=html.indexOf('async function* readAnswerEvents');
const end=html.indexOf('async function sendMessage',start);
const ctx=vm.createContext({TextDecoder,JSON});
vm.runInContext(html.slice(start,end),ctx);
test('stream parser preserves Chinese across every byte boundary',async()=>{
 const text='data: '+JSON.stringify({type:'token',text:'护城河'})+'\n\ndata: '+JSON.stringify({type:'done',final_answer:'完成'})+'\n\n';
 const bytes=new TextEncoder().encode(text);let i=0,released=false;
 const body={getReader:()=>({read:async()=>i<bytes.length?{value:bytes.slice(i,++i),done:false}:{done:true},releaseLock:()=>released=true})};
 const events=[];for await(const event of ctx.readAnswerEvents(body))events.push(event);
 assert.equal(events[0].text,'护城河');assert.equal(events[1].final_answer,'完成');assert.ok(released);
});
test('source or model HTML is escaped before markdown is rendered',()=>{
 const start=html.indexOf('function formatText(');const end=html.indexOf('// ── CITATION TOOLTIP',start);
 vm.runInContext(html.slice(start,end),ctx);
 const output=ctx.formatText('<img src=x onerror=alert(1)> [来源1]',[{text:'" onmouseover="alert(1)',title:'<bad>'}],'msg-1');
 assert.ok(!output.includes('<img'));assert.ok(output.includes('&lt;img'));assert.ok(!output.includes('data-tip-body="" onmouseover='));
});
