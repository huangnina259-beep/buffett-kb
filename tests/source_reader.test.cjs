const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../frontend/source-reader.js'),'utf8');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.style={};this.textContent='';this.attributes={};}
 append(...nodes){this.children.push(...nodes);} prepend(...nodes){this.children.unshift(...nodes);}
 replaceChildren(...nodes){this.children=nodes;} setAttribute(k,v){this.attributes[k]=v;}
 get innerHTML(){throw new Error('HTML injection must not be used');} set innerHTML(v){throw new Error('HTML injection must not be used');}
}
function allText(node){return node.textContent+node.children.map(allText).join(' ');}
function setup(fetch){const ctx={window:{},document:{createElement:t=>new Element(t)},fetch,Map,JSON,encodeURIComponent};vm.runInNewContext(code,ctx);return ctx.window.SourceReader;}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
test('late translation cannot overwrite a newly opened source',async()=>{
 const pending=[];const reader=setup(()=>new Promise(resolve=>pending.push(resolve)));const root=new Element('div');
 reader.show(root,{source_file:'a.md',text:'First English source with sufficient text.'},'cn');
 reader.show(root,{source_file:'b.md',text:'Second English source with sufficient text.'},'cn');
 pending[1]({ok:true,json:async()=>({translation:'新译文',original:'Second',status:'reviewed'})});await tick();
 pending[0]({ok:true,json:async()=>({translation:'过期译文',original:'First',status:'machine'})});await tick();
 assert.ok(allText(root).includes('新译文'));assert.ok(!allText(root).includes('过期译文'));
});
test('source and translated HTML remain literal text, original remains switchable',async()=>{
 const reader=setup(async()=>({ok:true,json:async()=>({translation:'<img src=x onerror=alert(1)>',original:'Original evidence',status:'machine'})}));const root=new Element('div');
 reader.show(root,{source_file:'a.md',text:'Original evidence'},'cn');await tick();
 assert.ok(allText(root).includes('<img'));assert.ok(allText(root).includes('待校对'));
 root.children[0].children[1].onclick();await tick();assert.ok(allText(root).includes('Original evidence'));
});
test('translation failure preserves original evidence and offers retry',async()=>{
 const reader=setup(async()=>({ok:false}));const root=new Element('div');reader.show(root,{source_file:'a.md',text:'Original remains readable'},'cn');await tick();
 assert.ok(allText(root).includes('Original remains readable'));assert.ok(allText(root).includes('重试译文'));
});
