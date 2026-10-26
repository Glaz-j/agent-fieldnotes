'use strict';
(function () {
  const labels = {success:'任务操作',diagnostic:'技能改写',completed:'连续控制',reference:'方法参考'};
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const normalize = value => String(value ?? '').normalize('NFKC').toLocaleLowerCase();
  function matchesQuery(text, query) { return normalize(query).trim().split(/\s+/).filter(Boolean).every(t => normalize(text).includes(t)); }
  function filterFamilies(data, state) {
    return data.families.map(family => ({...family,cards:family.cards.filter(card => {
      const text = [family.title,family.question,card.title,card.model,card.engine,card.input,card.task,card.shortDescription,card.sourceLabel,card.cardValue,card.projectBrief?.technicalRoute,card.projectBrief?.modelRole,card.projectBrief?.result,card.signals.map(s=>labels[s]).join(' '),data.mechanisms.find(m=>m.id===card.mechanism)?.title].join(' ');
      return (state.view==='all'||card.scope===state.view) && (state.mechanism==='all'||card.mechanism===state.mechanism) && (state.source==='all'||card.source===state.source) && (state.status==='all'||card.signals.includes(state.status)) && matchesQuery(text,state.query);
    })})).filter(family => family.cards.length);
  }
  if (typeof module !== 'undefined' && module.exports) module.exports={filterFamilies,matchesQuery,escape};
  if (typeof document === 'undefined') return;
  const $ = selector => document.querySelector(selector);
  const state = {view:'embodied',layout:'cards',query:'',mechanism:'all',source:'all',status:'all'};
  let data;
  const cardLink = (card,project) => './#demo-'+encodeURIComponent(card.id)+(project?.representativeId===card.id?'?trial='+project.previewTrialNumber:'');
  function previewCard(card,family,project) {
    const b=card.projectBrief,mechanism=data.mechanisms.find(m=>m.id===card.mechanism)?.title||'';
    const preview=card.id===project.representativeId?project.preview:card.preview;
    const poster=preview?.poster;
    const valid=typeof poster==='string'&&poster.startsWith('media/')&&!poster.includes('..');
    const image=valid?`<img src="${escape(poster)}" alt="${escape(preview.alt)}" loading="lazy" decoding="async">`:'<span class="preview-placeholder">实验场景</span>';
    const video=preview?.video;
    const hover=typeof video==='string'&&video.startsWith('media/')&&!video.includes('..')?` data-hover-preview="${escape(video)}" data-preview-start="${Number(preview.start)||0}"`:'';
    const link=cardLink(card,project);
    return `<article class="catalog-preview-card" data-project="${escape(project.id)}" data-card="${escape(card.id)}"><a class="catalog-preview-media"${hover} href="${link}" aria-label="观看 ${escape(project.title)}">${image}<span class="preview-engine">${escape(card.engine)}</span><span class="preview-play" aria-hidden="true">▶</span><span class="preview-count">${project.demoCount} 段演示</span>${hover?'<span class="hover-preview-hint" aria-hidden="true">悬停预览</span>':''}</a><div class="catalog-preview-body"><div class="preview-kicker"><span>${project.memberIds.length>1?project.memberIds.length+' 种版本 / 场景':'精选成果'}</span><span>${escape(mechanism)}</span></div><h3><a href="${link}">${escape(project.title)}</a></h3><p class="project-card-scene">${escape(card.title)}</p><p class="preview-summary">${escape(project.summary)}</p><div class="preview-role"><span>如何控制</span><p>${escape(b?.modelRole||card.model||card.input)}</p></div><div class="preview-result"><span>代表演示做成了什么</span><p>${escape(b?.result||card.cardValue)}</p></div><div class="preview-footer"><span>${escape(card.sourceLabel)}</span><a class="catalog-project-link" href="${link}">观看全部成果 <span aria-hidden="true">↗</span></a></div></div></article>`;
  }
  function row(card) {
    const mechanism = data.mechanisms.find(m=>m.id===card.mechanism).title;
    const flags = card.signals.map(s=>`<span class="catalog-tag ${['failure','interrupted'].includes(s)?'warn':''}">${escape(labels[s])}</span>`).join('');
    const review=card.review;
    const evidence=(review?.evidence||[]).map(p=>`<li><a href="${escape(p)}" target="_blank" rel="noopener">查看整理证据 ↗</a></li>`).join('');
    const notes = card.notes.length ? `<details class="row-notes"><summary>查看条件、局限与证据</summary><ul>${review?`<li><strong>解释边界：</strong>${escape(review.limitation)}</li>`:''}${card.notes.map(n=>`<li>${escape(n)}</li>`).join('')}${evidence}</ul></details>` : '';
    const b=card.projectBrief;
    const route=b?`<div class="catalog-explanation"><p><strong>技术路线</strong>${escape(b.technicalRoute)}</p><p class="catalog-role">${escape(b.modelRole)}</p><details class="row-notes"><summary>查看观察 → 决策 → 执行 → 反馈</summary>${b.controlLoop.map(s=>`<p><strong>${escape(s.label)}</strong>${escape(s.text)}</p>`).join('')}</details></div>`:`<span class="catalog-tag">${escape(mechanism)}</span><p>${escape(card.input||card.shortDescription)}</p>`;
    const result=b?`<div class="catalog-explanation"><p>${escape(b.result)}</p><p class="catalog-limit"><strong>解释边界</strong>${escape(b.limitation)}</p></div>`:`<strong>${escape(card.cardValue||'见原记录')}</strong>`;
    return `<tr><td data-label="项目 / 版本"><a href="${cardLink(card)}">${escape(card.title)} ↗</a><p class="catalog-small">${escape(card.engine)}</p><p class="catalog-small">${escape(card.model||'见原记录')}</p><a class="catalog-project-link" href="${cardLink(card)}">${card.records?'看录像与项目解读':'看项目解读'} →</a></td><td data-label="技术路线与控制">${route}</td><td data-label="本机结果与边界">${result}<div class="catalog-small">${flags}</div>${notes}</td><td data-label="来源与回放">${escape(card.sourceLabel)}<p class="catalog-small">${card.records} 条可展示记录${card.displaySummary?.hiddenRecords?` / 原有 ${card.displaySummary.originalRecords} 条`:''}</p></td></tr>`;
  }
  function render() {
    window.HoverPreviews?.stop();
    document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===state.view)));
    document.querySelectorAll('[data-layout]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.layout===state.layout)));
    $('#catalog-layout').hidden=state.view==='pending';
    document.querySelectorAll('.published-filter').forEach(node=>node.hidden=state.view==='pending');
    $('#expand-projects').hidden=$('#collapse-projects').hidden=state.view==='pending'||state.layout==='cards';
    if (state.view==='pending') {
      const pending=data.pending.filter(p=>matchesQuery([p.title,p.status,p.note].join(' '),state.query));
      $('#catalog-results').innerHTML=`<div class="pending-grid">${pending.map(p=>`<article class="pending-card"><span class="catalog-tag">${escape(p.status)}</span><h3>${escape(p.title)}</h3><p>${escape(p.note)}</p></article>`).join('')}</div>`;
      $('#catalog-result-count').textContent=`${pending.length} 项准备与待办 · 不计入已上架卡片数`;
      $('#catalog-empty').hidden=pending.length>0; return;
    }
    const families=filterFamilies(data,state);
    const cards=families.reduce((n,f)=>n+f.cards.length,0), records=families.reduce((n,f)=>n+f.cards.reduce((a,c)=>a+c.records,0),0);
    const expanded=new Set([...document.querySelectorAll('.project-group[open]')].map(n=>n.id));
    const queryActive=state.query.trim()||state.mechanism!=='all'||state.source!=='all'||state.status!=='all';
    $('#catalog-results').innerHTML=state.layout==='cards'?`<div class="catalog-preview-grid">${families.map(f=>{const p=data.projects.find(p=>p.id===f.id);const c=f.cards.find(c=>c.id===p.representativeId)||f.cards[0];return previewCard(c,f,p);}).join('')}</div>`:families.map(f=>`<details class="project-group" id="project-${escape(f.id)}" ${queryActive||expanded.has('project-'+f.id)||location.hash==='#project-'+f.id?'open':''}><summary><div class="project-summary-copy"><h3>${escape(f.title)}</h3><p>${escape(f.question)}</p></div><div class="project-count"><strong>${f.cards.length} 种版本 / 场景</strong>${f.cards.reduce((a,c)=>a+c.records,0)} 段成果演示</div></summary><div class="project-table-wrap"><table class="project-table"><thead><tr><th scope="col">项目 / 版本</th><th scope="col">技术路线与控制</th><th scope="col">本机结果与边界</th><th scope="col">来源与回放</th></tr></thead><tbody>${f.cards.map(row).join('')}</tbody></table></div></details>`).join('');
    $('#catalog-result-count').textContent=`${families.length} 个项目 · ${state.layout==='details'?cards+' 种版本 / 场景 · ':''}${records} 段演示`;
    $('#catalog-empty').hidden=cards>0;
  }
  function openHash() {
    if (!/^#project-[a-z0-9-]+$/.test(location.hash)) return;
    const family=data.families.find(f=>'#project-'+f.id===location.hash);
    if (!family) return;
    state.view=family.cards[0].scope;state.layout='details'; render();
    const node=document.getElementById(location.hash.slice(1)); if(node){node.open=true;node.scrollIntoView({block:'start'});}
  }
  fetch('data/experiment-catalog.json',{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.json();}).then(value=>{
    data=value;
    state.view=data.defaultView||'embodied';
    $('#catalog-stats').innerHTML=[['精选项目',data.counts.projects],['收录版本',data.counts.cards],['精彩演示',data.counts.records],['技术路线',data.mechanisms.length]].map(([label,n])=>`<div><dt>${escape(label)}</dt><dd>${n}</dd></div>`).join('');
    $('#catalog-date').textContent='整理于 '+data.updatedAt.slice(0,10)+' · 以保存记录为准';
    $('#study-links').innerHTML=data.learningPath.map(p=>`<li><a href="${cardLink(p)}">${escape(p.title)} ↗</a><p>${escape(p.reason)}</p></li>`).join('');
    $('#mechanism-filter').innerHTML+=[...data.mechanisms].map(m=>`<option value="${escape(m.id)}">${escape(m.title)}</option>`).join('');
    $('#catalog-source').innerHTML+=Object.entries(data.sources).map(([id,label])=>`<option value="${escape(id)}">${escape(label)}</option>`).join('');
    document.querySelectorAll('[data-view]').forEach(b=>{const count=b.dataset.view==='all'?data.counts.projects:b.dataset.view==='pending'?data.counts.pending:data.counts.projectsByScope[b.dataset.view]||0;b.hidden=data.curatedPublic&&count===0;b.textContent+=` · ${count}`;b.onclick=()=>{state.view=b.dataset.view;render();};});
    document.querySelectorAll('[data-layout]').forEach(b=>b.onclick=()=>{state.layout=b.dataset.layout;render();});
    $('#catalog-search').addEventListener('input',()=>{state.query=$('#catalog-search').value;render();});
    for(const [id,key] of [['#mechanism-filter','mechanism'],['#catalog-source','source'],['#catalog-status','status']])$(id).addEventListener('change',()=>{state[key]=$(id).value;render();});
    $('#catalog-reset').onclick=()=>{state.query='';state.mechanism=state.source=state.status='all';$('#catalog-search').value='';['#mechanism-filter','#catalog-source','#catalog-status'].forEach(id=>$(id).value='all');render();};
    $('#expand-projects').onclick=()=>document.querySelectorAll('.project-group').forEach(n=>n.open=true);
    $('#collapse-projects').onclick=()=>document.querySelectorAll('.project-group').forEach(n=>n.open=false);
    window.addEventListener('hashchange',openHash);render();openHash();
  }).catch(error=>{console.error(error);$('#catalog-result-count').textContent='目录载入失败，请刷新或通过本机网页服务打开。';});
})();
