const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const code=fs.readFileSync(path.join(__dirname,'../frontend/source-reader.js'),'utf8');
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.style={};this.textContent='';this.attributes={};this.value='';}
 append(...n){this.children.push(...n);}replaceChildren(...n){this.children=n;}setAttribute(k,v){this.attributes[k]=v;}focus(){}select(){}
 get innerHTML(){throw Error('unsafe HTML');}set innerHTML(v){throw Error('unsafe HTML');}
}
function allText(n){return (n.textContent||'')+n.children.map(allText).join(' ');}
function setup(fetch,storage=new Map()){
 const window={localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)}};
 const ctx={window,document:{createElement:t=>new Element(t)},fetch,AbortController,setTimeout,clearTimeout,navigator:{clipboard:{writeText:async()=>{}}},URL,Blob};vm.runInNewContext(code,ctx);return window.SourceReader;
}
const tick=()=>new Promise(r=>setImmediate(r));
const cn='这是中文原文，说明安全边际不能消除所有风险。',en='A margin of safety cannot eliminate every investment risk.';
function response(target,original=cn){const sourceLang=original===cn?'cn':'en',translation=target==='original'||target===sourceLang?null:(sourceLang==='cn'?en:cn);return {original,original_language:sourceLang,translation,target_language:target==='original'?sourceLang:target,source_file:'a.md',status:translation?'machine':'original',segments:[{original,translation,highlight:true,core:original}]};}
const ok=x=>({ok:true,json:async()=>x});
function button(root,text){if(root.tag==='button'&&root.textContent===text)return root;for(const child of root.children){const found=button(child,text);if(found)return found;}}
test('Chinese original switches to English only and bilingual, with correct pane content',async()=>{
 const reader=setup(async(u,o)=>ok(response(JSON.parse(o.body).target_language)));const root=new Element('div');reader.show(root,{text:cn,source_file:'a.md'},'cn');await tick();
 assert.ok(allText(root.children[2]).includes(cn));button(root,'English').onclick();await tick();assert.ok(allText(root.children[2]).includes(en));assert.ok(!allText(root.children[2]).includes(cn));
 button(root,'中英对照').onclick();await tick();assert.ok(allText(root.children[2]).includes(cn)&&allText(root.children[2]).includes(en));
 assert.equal(root.attributes.translate,'no');
});
test('slow English request cannot overwrite a switch back to Chinese',async()=>{
 let finish;const reader=setup(async(u,o)=>{const target=JSON.parse(o.body).target_language;return target==='original'?ok(response(target)):new Promise(r=>finish=()=>r(ok(response(target))));});const root=new Element('div');reader.show(root,{text:cn},'cn');await tick();button(root,'English').onclick();await tick();assert.ok(allText(root).includes('正在准备英文'));
 button(root,'中文').onclick();await tick();finish();await tick();assert.ok(!allText(root.children[2]).includes(en));assert.ok(allText(root.children[2]).includes(cn));
});
test('late response from a different citation is discarded',async()=>{
 const pending=[];const reader=setup(()=>new Promise(r=>pending.push(r))),root=new Element('div');reader.show(root,{text:cn,source_file:'a.md'},'cn');reader.show(root,{text:cn,source_file:'b.md'},'cn');
 pending[1](ok({...response('original'),original:cn+'新的引用。',segments:[{original:cn+'新的引用。',highlight:true}]}));await tick();pending[0](ok(response('original')));await tick();assert.ok(allText(root).includes('新的引用'));
});
test('missing or wrong-language English translation produces explicit failure, not mislabeled Chinese',async()=>{
 const reader=setup(async(u,o)=>{const target=JSON.parse(o.body).target_language;return ok(target==='original'?response(target):{...response(target),translation:cn});}),root=new Element('div');reader.show(root,{text:cn},'cn');await tick();button(root,'English').onclick();await tick();assert.ok(allText(root).includes('当前语言没有可显示的译文'));assert.ok(button(root,'重试'));assert.ok(!allText(root).includes('English · 译文'));
});
test('markup in original stays inert text and a real core is marked',async()=>{
 const original=en+' <img src=x onerror=alert(1)>';const data={...response('original',original),segments:[{original,highlight:true,core:en}]};const reader=setup(async()=>ok(data)),root=new Element('div');reader.show(root,{text:original},'en');await tick();assert.ok(allText(root).includes('<img'));const find=(n,tag)=>n.tag===tag||n.children.some(c=>find(c,tag));assert.ok(find(root,'mark'));
});
test('saving is explicit, keeps source metadata and notes, and deduplicates the same excerpt',async()=>{
 const storage=new Map(),reader=setup(async()=>ok(response('original')) ,storage),root=new Element('div');reader.show(root,{text:cn,title:'来源标题',author:'李录',year:2015,focus:'如何判断风险？'},'cn');await tick();assert.equal(storage.size,0);
 button(root,'收藏重点并记笔记').onclick();const form=root.children[4];form.children[0].children[0].value='先看永久损失';form.children[1].children[0].value='风险，安全边际';button(root,'保存摘录').onclick();button(root,'收藏重点并记笔记').onclick();button(root,'保存摘录').onclick();const rows=JSON.parse([...storage.values()][0]);assert.equal(rows.length,1);assert.equal(rows[0].author,'李录');assert.equal(rows[0].note,'先看永久损失');assert.match(reader.markdown(rows),/来源资料：a.md/);assert.match(reader.markdown(rows),/安全边际/);
 const library=new Element('div');reader.mountNotebook(library,'cn');assert.ok(allText(library).includes('来源标题'));library.children[0].value='不存在的主题';library.children[0].oninput();assert.ok(allText(library).includes('找到 0 条'));
});
