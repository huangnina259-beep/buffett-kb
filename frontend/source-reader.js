/* Source evidence is always rendered as text, never executable markup. */
(function () {
  const pending=new Map(), STORE='compounder.readings.v1';
  const el=(tag,text,className)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(className)n.className=className;return n;};
  function tidy(text){return String(text||'').replace(/\r\n?/g,'\n').replace(/(^|\n)[ \t]*\d{1,4}[ \t]*(?=\n|$)/g,'$1').split(/\n\s*\n/).map(p=>p.replace(/\s+/g,' ').trim().replace(/([\u4e00-\u9fff，。；：！？、]) +(?=[\u4e00-\u9fff，。；：！？、])/g,'$1')).filter(Boolean).join('\n\n');}
  function language(text){return (text.match(/[\u4e00-\u9fff]/g)||[]).length>Math.max(10,(text.match(/[A-Za-z]/g)||[]).length/4)?'cn':'en';}
  function reading(src,target){
    const payload={source_file:src.source_file||'',excerpt:src.text||src.full_context||'',target_language:target,focus:(src.focus||'').slice(0,1200)};
    const key=JSON.stringify(payload);
    if(!pending.has(key)){
      const controller=new AbortController();const timer=setTimeout(()=>controller.abort(),65000);
      pending.set(key,fetch('/api/source-reading',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload),signal:controller.signal})
        .then(async r=>{if(!r.ok)throw new Error(r.status===422?'unverified':'translation');return r.json();})
        .catch(e=>{pending.delete(key);throw e;}).finally(()=>clearTimeout(timer)));
    }
    return pending.get(key);
  }
  function marked(parent,text,core){
    const index=core?text.indexOf(core):-1;
    if(index<0){parent.textContent=text;return;}
    if(index)parent.append(el('span',text.slice(0,index)));
    parent.append(el('mark',core));
    if(index+core.length<text.length)parent.append(el('span',text.slice(index+core.length)));
  }
  function records(){try{const list=JSON.parse(window.localStorage.getItem(STORE)||'[]');return Array.isArray(list)?list.filter(x=>x&&typeof x.id==='string'&&typeof x.original==='string'):[];}catch(e){return [];}}
  function writeRecords(list){window.localStorage.setItem(STORE,JSON.stringify(list));}
  function recordId(file,original){return JSON.stringify([file,original]);}
  const selectedId=result=>recordId(result.source_file,result.segments?.find(x=>x.highlight)?.original||result.original);
  function show(root,src,uiLang){
    const identity={};root._readingIdentity=identity;
    const english=uiLang==='en', t=(cn,en)=>english?en:cn;
    let mode=english?'en':'cn',revision=0,expanded=false,selected=null;
    root.className=[...new Set(((root.className||'')+' sr-reader').split(/\s+/).filter(Boolean))].join(' ');root.setAttribute('translate','no'); // Browser translation must not replace the English pane.
    const controls=el('div',null,'sr-tabs'),body=el('div',null,'sr-content');
    body.setAttribute('aria-live','polite');
    const buttons={};
    for(const [choice,label] of [['cn','中文'],['en','English'],['both',t('中英对照','Bilingual')]]){
      const b=el('button',label);b.type='button';b.onclick=()=>{mode=choice;render();};buttons[choice]=b;controls.append(b);
    }
    const context=el('div',null,'sr-answer-context');
    if(src.focus){context.append(el('small',t('引用对应的回答或问题','Answer or question connected to this citation')),el('p',src.focus));}
    const actions=el('div',null,'sr-actions'),save=el('button',t('收藏重点并记笔记','Save focus & note'));
    const library=el('a',t('我的摘录','My excerpts'));library.href='/static/notes.html'+(english?'?lang=en':'');
    actions.append(save,library);
    if(src.url&&/^https:\/\//i.test(src.url)){const link=el('a',t('来源页面 ↗','Source website ↗'));link.href=src.url;link.target='_blank';link.rel='noopener noreferrer';actions.append(link);}
    const form=el('div',null,'sr-note-form');form.hidden=true;
    const noteLabel=el('label',t('我的理解：这段话如何改变我的判断？','My understanding: how does this change my judgment?'));
    const note=el('textarea');note.rows=3;note.maxLength=4000;noteLabel.append(note);
    const tagsLabel=el('label',t('主题标签（用逗号分隔）','Topic tags (comma separated)'));const tags=el('input');tags.maxLength=160;tagsLabel.append(tags);
    const confirm=el('button',t('保存摘录','Save excerpt')),notice=el('p',null,'sr-muted');notice.setAttribute('role','status');
    form.append(noteLabel,tagsLabel,confirm,el('small',t('仅保存在此浏览器。可在“我的摘录”导出备份。','Saved only in this browser. Export a backup from My excerpts.')));
    save.onclick=()=>{if(!selected)return;form.hidden=!form.hidden;if(!form.hidden){const old=records().find(x=>x.id===selectedId(selected));note.value=old?.note||'';tags.value=(old?.tags||[]).join(', ');note.focus();}};
    confirm.onclick=()=>{
      if(!selected)return;
      const focus=selected.segments?.find(x=>x.highlight);
      const original=focus?.original||selected.original,translation=focus?.translation||null;
      const id=selectedId(selected),list=records(),existing=list.find(x=>x.id===id);
      const item={id,source_file:selected.source_file,title:src.title||src.label||selected.source_file.replace(/_/g,' ').replace(/\.md$/,''),author:src.author||'',year:src.year||'',focus:src.focus||'',core:focus?.core||'',translated_core:focus?.translated_core||'',original,translation:translation||existing?.translation||null,original_language:selected.original_language,status:translation?selected.status:(existing?.status||selected.status),note:note.value.trim(),tags:tags.value.split(/[,，]/).map(x=>x.trim()).filter(Boolean),saved_at:existing?.saved_at||new Date().toISOString(),url:/^https:\/\//i.test(src.url||'')?src.url:''};
      try{writeRecords([item,...list.filter(x=>x.id!==id)]);notice.textContent=t('已保存，可在“我的摘录”回看。','Saved. Find it in My excerpts.');form.hidden=true;}catch(e){notice.textContent=t('浏览器未能保存，请复制摘录备份。','Browser storage failed. Copy your excerpt to keep it.');}
    };
    root.replaceChildren(controls,context,body,actions,form,notice);
    function section(parent,lang,text,isOriginal,core){
      const box=el('section',null,'sr-language');box.lang=lang==='cn'?'zh-CN':'en';box.setAttribute('translate','no');
      box.append(el('h4',(lang==='cn'?'中文':'English')+' · '+(isOriginal?t('原文','Original'):t('译文','Translation'))));
      const prose=el('div',null,'sr-prose');marked(prose,text,core);box.append(prose);parent.append(box);
    }
    function display(result){
      selected=result;save.disabled=false;body.replaceChildren();
      const badge=result.status==='reviewed'?t('译文已对照原文核对','Translation checked against source'):result.status==='machine'?t('自动译文 · 待校对','Machine translation · not reviewed'):t('原始资料 · 完整句子节选','Source · sentence-based excerpt');
      body.append(el('p',badge,'sr-status'));
      const segments=result.segments||[{original:result.original,translation:result.translation,highlight:true,core:''}];
      const hasFocus=Boolean(src.focus);
      body.append(el('h3',hasFocus?t('阅读重点','Reading focus'):t('引用节选','Source excerpt')));
      if(hasFocus)body.append(el('p',t('根据当前观点自动定位；请展开上下文核对，不代表原作者的重点标记。','Automatically located for this passage. Check the context; highlighting is not from the author.'),'sr-muted'));
      if(result.aligned===false)body.append(el('p',t('此译文的分段与原文不同，当前以完整节选对照。','Paragraph boundaries differ; this view compares the complete excerpt.'),'sr-muted'));
      if(result.boundary_repaired)body.append(el('p',t('已从原资料补齐首尾句。','Boundary sentences restored from the source.'),'sr-muted'));
      if(result.leading_omitted||result.trailing_omitted)body.append(el('p',t('过长的首尾残句已略去。','Overlong incomplete boundary sentences omitted.'),'sr-muted'));
      const visible=expanded?segments:segments.filter(x=>x.highlight);
      for(const part of visible){
        const pair=el('div',null,'sr-pair'+(mode==='both'?' sr-bilingual':'')+(part.highlight?' sr-focus':''));
        const sourceLang=result.original_language,other=sourceLang==='cn'?'en':'cn';
        if(mode==='both'){
          for(const lang of ['cn','en'])section(pair,lang,lang===sourceLang?part.original:part.translation,lang===sourceLang,lang===sourceLang?part.core:part.translated_core);
        }else section(pair,mode,mode===sourceLang?part.original:part.translation,mode===sourceLang,mode===sourceLang?part.core:part.translated_core);
        if(part.highlight&&result.translation)pair.append(el('small',t('高亮根据当前观点自动定位；中英文以整段对应。','Highlights are located for this topic; the two languages correspond by paragraph.'),'sr-muted'));
        body.append(pair);
      }
      if(segments.length>1){const toggle=el('button',expanded?t('收起上下文','Collapse context'):t('展开引用上下文','Expand citation context'));toggle.setAttribute('aria-expanded',String(expanded));toggle.onclick=()=>{expanded=!expanded;display(result);};body.append(toggle);}
      body.append(el('p',t('这是原资料的节选；译文帮助理解，核对请以原文为准。','This is an excerpt. Translation supports reading; the original is authoritative.'),'sr-muted'));
      const copy=el('button',t('复制重点与出处','Copy focus & source'));copy.onclick=async()=>{
        const part=segments.find(x=>x.highlight)||segments[0];const text=[src.title||result.source_file,[src.author,src.year].filter(Boolean).join(' · '),part.original,part.translation||'',src.url||''].filter(Boolean).join('\n\n');
        try{await navigator.clipboard.writeText(text);notice.textContent=t('已复制重点与出处。','Copied focus and source.');}catch(e){const field=el('textarea');field.value=text;field.readOnly=true;notice.replaceChildren(el('span',t('请选中以下内容复制：','Select and copy:')),field);field.select();}
      };body.append(copy);
    }
    async function render(){
      const current=++revision;selected=null;save.disabled=true;form.hidden=true;
      const fresh=()=>root._readingIdentity===identity&&current===revision;
      for(const choice of Object.keys(buttons))buttons[choice].setAttribute('aria-pressed',String(choice===mode));
      body.replaceChildren(el('p',t('正在定位完整引用…','Locating the complete excerpt…'),'sr-status'));body.setAttribute('aria-busy','true');
      let original;
      try{
        original=await reading(src,'original');if(!fresh())return;
        if(mode===original.original_language){display(original);return;}
        const target=mode==='both'?(original.original_language==='cn'?'en':'cn'):mode;
        body.replaceChildren(el('p',t(`正在准备${target==='en'?'英文':'中文'}译文…首次可能需要几十秒，切换原文可立即阅读。`,`Preparing ${target==='en'?'English':'Chinese'} translation… The first request may take a little while. Switch to the original to read immediately.`),'sr-status'));
        if(mode==='both')section(body,original.original_language,original.original,true,'');
        const result=await reading(src,target);if(!fresh())return;
        // A missing or wrong-language translation must never masquerade as English/Chinese.
        if(!result.translation||language(result.translation)!==target||result.target_language!==target)throw new Error('translation');
        display(result);
      }catch(e){
        if(!fresh())return;
        body.replaceChildren(el('p',e.message==='unverified'?t('这条引用暂时无法可靠定位。可查看保存的节选，或重新提问获取新引用。','This citation could not be reliably located. Read the saved excerpt or ask again for a fresh citation.'):t('译文暂未生成成功。当前语言没有可显示的译文。','Translation is unavailable. No translation is shown for this language.'),'sr-error'));
        const retry=el('button',t('重试','Retry'));retry.onclick=render;body.append(retry);
        const fallback=el('details');fallback.append(el('summary',t('查看原文节选','Read original excerpt')));section(fallback,original?.original_language||language(tidy(src.text||'')),original?.original||tidy(src.text||''),true,'');body.append(fallback);
      }finally{if(fresh())body.setAttribute('aria-busy','false');}
    }
    render();
  }
  function markdown(list){return list.map(x=>['## '+x.title,[x.author,x.year].filter(Boolean).join(' · '),'来源资料：'+x.source_file,'关联问题／观点：'+(x.focus||'—'),'原文：\n\n'+x.original,x.translation?'译文（'+(x.status==='reviewed'?'已核对':'自动翻译，待校对')+'）：\n\n'+x.translation:'','我的理解：\n\n'+(x.note||'—'),'标签：'+(x.tags||[]).join(', '),x.url||''].filter(Boolean).join('\n\n')).join('\n\n---\n\n');}
  function mountNotebook(root,lang){
    const en=lang==='en',t=(cn,enText)=>en?enText:cn;
    root.replaceChildren();const search=el('input');search.type='search';search.placeholder=t('搜索摘录、笔记或标签','Search excerpts, notes or tags');search.setAttribute('aria-label',search.placeholder);
    const exportButton=el('button',t('导出全部摘录','Export all excerpts')),message=el('p',null,'sr-muted'),list=el('div');root.append(search,exportButton,message,list);
    exportButton.onclick=()=>{const rows=records();if(!rows.length){message.textContent=t('还没有可导出的摘录。','No excerpts to export yet.');return;}const url=URL.createObjectURL(new Blob([markdown(rows)],{type:'text/markdown;charset=utf-8'}));const a=el('a');a.href=url;a.download='compounder-excerpts.md';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
    function render(){list.replaceChildren();const query=search.value?.toLowerCase()||'';const rows=records().filter(x=>JSON.stringify(x).toLowerCase().includes(query));message.textContent=t(`找到 ${rows.length} 条摘录。仅保存在此浏览器，清理浏览器数据前请导出备份。`,`${rows.length} excerpts. Stored only in this browser; export before clearing browser data.`);
      if(!rows.length){list.append(el('p',t('从问答引用或案例材料中，点击“收藏重点并记笔记”开始。','Start with “Save focus & note” in a Q&A citation or case reading.')));return;}
      for(const item of rows){const card=el('article',null,'sr-saved');card.append(el('h2',item.title),el('p',[item.author,item.year].filter(Boolean).join(' · '),'sr-muted'));if(item.focus)card.append(el('p',item.focus,'sr-answer-context'));
        const original=el('blockquote',null,'sr-prose');marked(original,item.original,item.core);original.setAttribute('translate','no');card.append(el('h3',t('原文','Original')),original);
        if(item.translation){const translated=el('blockquote',null,'sr-prose');marked(translated,item.translation,item.translated_core);card.append(el('h3',item.status==='reviewed'?t('译文 · 已核对','Translation · checked'):t('自动译文 · 待校对','Machine translation · not reviewed')),translated);}
        if(/^https:\/\//i.test(item.url||'')){const link=el('a',t('核对来源页面 ↗','Check source website ↗'));link.href=item.url;link.target='_blank';link.rel='noopener noreferrer';card.append(link);}
        const label=el('label',t('我的理解','My understanding')),note=el('textarea');note.value=item.note||'';note.rows=3;note.maxLength=4000;label.append(note);
        const tagsLabel=el('label',t('主题标签','Topic tags')),tags=el('input');tags.value=(item.tags||[]).join(', ');tags.maxLength=160;tagsLabel.append(tags);
        const save=el('button',t('保存笔记','Save note')),remove=el('button',t('移除此摘录','Remove excerpt')),status=el('span');status.setAttribute('role','status');
        save.onclick=()=>{try{writeRecords(records().map(x=>x.id===item.id?{...x,note:note.value.trim(),tags:tags.value.split(/[,，]/).map(v=>v.trim()).filter(Boolean)}:x));status.textContent=t('已保存','Saved');}catch(e){status.textContent=t('保存失败，请导出备份','Save failed; export a backup');}};
        remove.onclick=()=>{try{writeRecords(records().filter(x=>x.id!==item.id));render();}catch(e){status.textContent=t('删除失败','Could not remove');}};
        card.append(label,tagsLabel,save,remove,status);list.append(card);
      }
    }search.oninput=render;render();
  }
  window.SourceReader={show,tidy,mountNotebook,markdown};
})();
