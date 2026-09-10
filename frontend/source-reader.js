/* Shared bilingual citation viewer. All document and model text stays textContent. */
(function () {
  const pending = new Map();
  function tidy(text) {
    return String(text || '').replace(/\r\n?/g,'\n').replace(/^\s*(?:\d{1,4}|[-_* ]{3,})\s*$/gm,'')
      .split(/\n\s*\n/).map(block => {
        const lines=block.split('\n');
        const table=lines.some(line => /\d/.test(line) && (/\S\s{3,}\S/.test(line)||/[|\t]/.test(line)));
        const list=lines.some(line=>/^\s*(?:[-*•]|\d+[.)])\s/.test(line));
        return table||list ? block.trim() : block.replace(/\s+/g,' ').trim();
      }).filter(Boolean).join('\n\n');
  }
  function language(text) {
    return (text.match(/[\u4e00-\u9fff]/g)||[]).length > Math.max(10,(text.match(/[A-Za-z]/g)||[]).length/4) ? 'cn':'en';
  }
  function reading(src,target) {
    const key=JSON.stringify([src.source_file,src.text,target]);
    if (!pending.has(key)) pending.set(key,fetch('/api/source-reading',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({source_file:src.source_file,excerpt:src.text,target_language:target})
    }).then(async r=>{if(!r.ok)throw new Error('unavailable');return r.json();}).catch(e=>{pending.delete(key);throw e;}));
    return pending.get(key);
  }
  function show(root,src,uiLang) {
    const identity={}; root._readingIdentity=identity;
    let mode=uiLang;
    const original=tidy(src.text||src.full_context||'');
    const originalLanguage=language(original);
    const source={...src,text:src.text||src.full_context||''};
    const english=uiLang==='en';
    const labels={cn:'中文',en:'English',both:english?'Side by side':'中英对照'};
    const controls=document.createElement('div');
    controls.style.cssText='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:14px';
    const body=document.createElement('div');
    const buttons={};
    root.replaceChildren(controls,body);
    for(const choice of ['cn','en','both']) {
      const b=document.createElement('button');b.type='button';b.textContent=labels[choice];
      b.style.cssText='padding:6px 12px;border:1px solid #bcae91;border-radius:5px;background:transparent;cursor:pointer;color:inherit';
      b.onclick=()=>{mode=choice;render();};buttons[choice]=b;controls.append(b);
    }
    if (src.url && /^https:\/\//i.test(src.url)) {
      const link=document.createElement('a');link.textContent=english?'Source website':'已有来源页面';
      link.href=src.url;link.target='_blank';link.rel='noopener noreferrer';controls.append(link);
    }
    function section(label,text) {
      const box=document.createElement('section');box.style.marginBottom='20px';
      const heading=document.createElement('div');heading.textContent=label;heading.style.cssText='font-size:12px;font-weight:600;margin-bottom:8px;color:#756344';
      const content=document.createElement('div');content.textContent=text;content.style.cssText='white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.85';
      box.append(heading,content);body.append(box);
    }
    const originalLabel=(originalLanguage==='cn'?'中文':'English')+(english?' · Original excerpt':' · 原文节选');
    let revision=0;
    async function render() {
      const current=++revision;
      for(const choice of Object.keys(buttons)){buttons[choice].setAttribute('aria-pressed',String(choice===mode));buttons[choice].style.background=choice===mode?'#eee7d9':'transparent';}
      body.replaceChildren();
      if(mode===originalLanguage){
        section(originalLabel,original);
        if(source.source_file) {
          try {const result=await reading(source,mode);if(root._readingIdentity===identity&&current===revision){body.replaceChildren();section(originalLabel,result.original||original);}}catch(e){}
        }
        return;
      }
      const target=mode==='both'?(originalLanguage==='cn'?'en':'cn'):mode;
      const waiting=document.createElement('p');waiting.textContent=english?'Preparing translation. You can read the original below.':'正在准备译文，下面的原文可先阅读。';waiting.style.fontSize='12px';body.append(waiting);section(originalLabel,original);
      if(!source.source_file){waiting.textContent=english?'Translation is unavailable for this older citation. The original is preserved.':'这条历史引用暂时无法匹配译文，原文仍可阅读。';return;}
      try {
        const result=await reading(source,target);
        if(root._readingIdentity!==identity||current!==revision)return;
        body.replaceChildren();
        const status=result.status==='reviewed'?(english?'Translation · checked against source':'译文 · 已对照原文核对'):(english?'Machine translation · not yet reviewed':'机器译文 · 待校对');
        section((target==='cn'?'中文':'English')+' · '+status,result.translation||original);
        if(mode==='both')section(originalLabel,result.original||original);
        const note=document.createElement('p');note.style.cssText='font-size:11px;color:#777';note.textContent=english?'Translation supports reading; the source remains authoritative.':'译文帮助理解，引用核对请以原文为准。';body.append(note);
      } catch(e) {
        if(root._readingIdentity!==identity||current!==revision)return;
        waiting.textContent=english?'Translation is temporarily unavailable. The original is still available.':'译文暂不可用，原文仍可阅读。';
        const retry=document.createElement('button');retry.textContent=english?'Retry translation':'重试译文';retry.onclick=render;body.prepend(retry);
      }
    }
    render();
  }
  window.SourceReader={show,tidy};
})();
