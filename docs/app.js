'use strict';
const $ = (s) => document.querySelector(s);
const sourceNames = { published_policy: '本机运行 · 作者公开策略', authored: '本机运行 · 模型编写的控制器', fresh: '本机新跑 Agent', replay: '公开轨迹回放', demonstration: '本机复演 · 人类示范', vla: '本机 VLA 推理', baseline: '传统控制基线', online_learning: '本机在线学习 · 无 LLM' };
const routeNames = { skill_reuse: 'Agent + 操作经验复用', spatial_memory: '视觉几何 + 空间记忆', learned: '学习策略 + 脚本编排', planner: 'Agent + 运动规划', navigation: 'Agent + 步态控制', flight: 'Agent + 飞行控制', vision: '视觉 Agent', active_perception: '主动选视角 + 扩散策略', vla: 'VLA 策略', control: '经典 / 脚本控制', coding: '代码生成 Agent', world_model: '可执行世界模型 + 规划', latent_world_model: '学习动力学 + 滚动规划', skill_adaptation: 'Agent + 示范技能修改', demonstration: '示范动作重放', demonstration_transfer: '示范轨迹迁移', online_learning: '神经细胞自动机 + 在线学习' };
const state = { data: null, collectionScope: null, scope: 'embodied', quick: 'all', selected: null, trial: 0, opener: null, returnHash: '' };
routeNames.reference_motion = 'Agent + 示范动作参考';
const escapeHTML = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const resultLabel = (t) => t.statusLabel || (t.success === true ? '成功' : t.success === false ? '未达成' : '未按成功判定');
const badge = (name, cls='') => `<span class="badge ${cls}">${escapeHTML(name)}</span>`;
const trialName = (t, i) => t.label || `轨迹 ${String(t.originalTrialNumber||i+1).padStart(2,'0')}`;
const mediaPath = (p) => { if (typeof p !== 'string' || !p.startsWith('media/') || p.includes('..')) throw new Error('Invalid media reference'); return p; };
const sourceURL = (p) => { const u = new URL(p); if (u.protocol !== 'https:') throw new Error('Invalid source URL'); return u.href; };
// Public trial numbers are one-based and follow the evidence index's fixed order.
function parseDemoHash(hash) {
  const match = /^#demo-([^?]+)(?:\?(.*))?$/.exec(hash); if (!match) return null;
  try {
    const raw = new URLSearchParams(match[2] || '').get('trial');
    const number = raw !== null && /^[1-9]\d*$/.test(raw) ? Number(raw) : 1;
    return { id: decodeURIComponent(match[1]), trial: Number.isSafeInteger(number) ? number - 1 : 0, explicitTrial:raw!==null&&/^[1-9]\d*$/.test(raw)&&Number.isSafeInteger(number) };
  } catch { return null; }
}
function trialHash(id, index) {
  if(index<0)return `#demo-${encodeURIComponent(id)}`;
  const trial=state.data?.demos.find(d=>d.id===id)?.trials[index];
  return `#demo-${encodeURIComponent(id)}?trial=${trial?.originalTrialNumber||index+1}`;
}
function setPageHash(hash, mode = 'replace') {
  const url = new URL(location.href); url.hash = hash;
  if (url.href !== location.href) history[mode === 'push' ? 'pushState' : 'replaceState'](history.state, '', url.href);
}
function currentTrialURL() {
  const url = new URL(location.href); url.search = ''; url.hash = trialHash(state.selected.id, state.trial); return url.href;
}
function updateShareLink() {
  $('#trial-link').value = currentTrialURL(); $('#manual-trial-link').hidden = true;
  $('#copy-trial-link').setAttribute('aria-expanded', 'false');
  const url = new URL(location.href);
  $('#share-scope').textContent = ['localhost', '127.0.0.1', '[::1]', '::1'].includes(url.hostname) ? '本机链接' : url.protocol === 'file:' ? '本地文件链接' : '当前站点链接';
  $('#share-status').textContent = '接收者需要能访问当前站点地址。';
  $('#copy-trial-link').textContent=state.trial<0?'复制项目链接':'复制当前轨迹链接';
}
async function copyTrialLink() {
  if (!state.selected) return;
  const url = currentTrialURL();
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable');
    await navigator.clipboard.writeText(url);
    if (state.selected && currentTrialURL() === url) $('#share-status').textContent = '已复制，可直接打开这条轨迹。';
  } catch {
    if (!state.selected || currentTrialURL() !== url) return;
    $('#manual-trial-link').hidden = false; $('#copy-trial-link').setAttribute('aria-expanded', 'true');
    $('#share-status').textContent = '自动复制不可用，请手动复制下方链接。';
    $('#trial-link').focus(); $('#trial-link').select();
  }
}
function syncFromLocation() {
  if (!state.data) return;
  const route = parseDemoHash(location.hash), demo = route && state.data.demos.find(d => d.id === route.id);
  const notice = $('#curation-notice');
  if (notice) notice.hidden = !route || !!demo;
  if (!demo) {
    if ($('#demo-dialog').open) $('#demo-dialog').close();
    return;
  }
  let trial=0;
  if(route.explicitTrial){
    trial=demo.trials.findIndex((t,i)=>(t.originalTrialNumber||i+1)===route.trial+1);
  }
  if (!demo.trials.length || trial<0){
    openDemo(demo.id,null,{noTrial:true,hiddenTrialNumber:route.explicitTrial?route.trial+1:null,history:'none'});return;
  }
  if ($('#demo-dialog').open && state.selected?.id === demo.id && state.trial === trial) return;
  if ($('#demo-dialog').open && state.selected?.id === demo.id) selectTrial(trial, false);
  else openDemo(demo.id, null, { trial, history: 'none' });
}
function onDialogClose() {
  if ($('#demo-dialog').open) return; // A subsequent hash navigation may already have reopened it.
  $('#detail-video').pause(); document.body.classList.remove('modal-open');
  if (state.selected && parseDemoHash(location.hash)?.id === state.selected.id) setPageHash(state.returnHash);
  if (state.opener?.isConnected) state.opener.focus();
  state.selected = null; state.opener = null;
  updateAgentJump();
}
function agentStartMarker() {
  const trial = state.selected?.trials[state.trial];
  const value = trial?.video ? trial.agentStartSeconds : null;
  return typeof value === 'number' && Number.isFinite(value) && value >= 0 ? value : null;
}
function updateAgentJump() {
  const marker = agentStartMarker(), video = $('#detail-video');
  const ready = video.readyState > 0 && Number.isFinite(video.duration) && video.duration > 0;
  const valid = marker !== null && (!ready || marker <= video.duration);
  $('#agent-jump-controls').hidden = !valid;
  $('#jump-to-agent').disabled = !valid || !ready;
}
function jumpToAgent() {
  updateAgentJump();
  if ($('#jump-to-agent').disabled) return;
  const video = $('#detail-video');
  video.pause();
  try {
    video.currentTime = Math.min(agentStartMarker(), Math.max(0, video.duration - 0.001));
    $('#agent-seek-status').textContent = '已跳到模型动作；点击视频播放继续。';
  } catch {
    $('#agent-seek-status').textContent = '暂时无法跳转，请等待视频加载后再试。';
  }
}
function init(data, collectionScope) {
  state.data = data;
  state.collectionScope = collectionScope;
  state.scope = collectionScope.defaultScope;
  $('#scope-filter').value = state.scope;
  $('#scope-filter').addEventListener('change',()=>{state.scope=$('#scope-filter').value;renderCards();});
  const featured = data.demos.find(d=>d.id===data.featured) || data.demos[0];
  const heroTrial = featured.trials.find(t=>t.success) || featured.trials[0];
  $('#hero-video').src = mediaPath(heroTrial.video); $('#hero-video').poster = mediaPath(heroTrial.poster || featured.poster);
  $('#hero-metrics').innerHTML = (featured.heroMetrics || featured.metrics.slice(0,3)).map(m=>`<div><strong>${escapeHTML(m.value)}</strong><span>${escapeHTML(m.label)}</span></div>`).join('');
  $('#hero-note').textContent = featured.heroNote || '单集验证；录像按仿真帧率播放，省略模型等待时间。';
  $('#hero-project-label').textContent=data.feature.label;
  $('#hero-project-title').textContent=data.feature.title;
  $('#hero-video').setAttribute('aria-label',data.feature.videoLabel);
  $('#hero-open').setAttribute('aria-label','打开 '+featured.title+' 项目详情');
  const n = data.demos.reduce((a,d)=>a+d.trials.length,0);
  $('#collection-count').textContent = `${data.projects.length} 个项目 · ${n} 段成果演示`;
  $('#updated-date').textContent = `最近整理 ${data.updated} · 具身智能能力探索`;
  for (const [selector,key,names] of [['#route-filter','route',routeNames],['#engine-filter','engine',{}],['#source-filter','source',sourceNames],['#task-filter','task',{}]]) {
    const values = [...new Set(data.demos.map(d=>d[key]))];
    for(const val of values) { const op=document.createElement('option');op.value=val;op.textContent=names[val]||val;$(selector).append(op); }
    $(selector).addEventListener('change',renderCards);
  }
  $('#hero-detail').onclick = (e)=>openDemo(featured.id,e.currentTarget); $('#hero-open').onclick = (e)=>openDemo(featured.id,e.currentTarget);
  document.querySelectorAll('[data-quick]').forEach(b=>b.onclick=()=>{state.quick=b.dataset.quick;document.querySelectorAll('[data-quick]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',x===b?'true':'false')});renderCards();});
  $('#reset-filters').onclick=()=>resetFilters(); $('#empty-reset').onclick=()=>resetFilters('all');
  $('#experiment-search').addEventListener('input',renderCards);
  $('#experiment-sort').addEventListener('change',renderCards);
  $('#close-dialog').onclick=()=>$('#demo-dialog').close();
  $('#demo-dialog').addEventListener('close',onDialogClose);
  $('#demo-dialog').addEventListener('click',e=>{if(e.target===$('#demo-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  $('#trial-select').onchange=e=>selectTrial(Number(e.target.value)); $('#next-trial').onclick=()=>selectTrial((state.trial+1)%state.selected.trials.length);
  $('#copy-trial-link').onclick=copyTrialLink;
  $('#jump-to-agent').onclick=jumpToAgent;
  $('.detail-view').append($('#decision-template').content.cloneNode(true));
  $('#detail-video').addEventListener('loadedmetadata',syncDecision);
  $('#detail-video').addEventListener('loadedmetadata',updateAgentJump);
  $('#detail-video').addEventListener('durationchange',updateAgentJump);
  $('#detail-video').addEventListener('timeupdate',syncDecision);
  window.addEventListener('hashchange',syncFromLocation); window.addEventListener('popstate',syncFromLocation);
  renderCards();
  syncFromLocation();
}
function resetFilters(scope=state.collectionScope.defaultScope){state.scope=scope;$('#scope-filter').value=scope;state.quick='all';document.querySelectorAll('[data-quick]').forEach(b=>{const active=b.dataset.quick==='all';b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});document.querySelectorAll('.select-filters select').forEach(s=>s.value='all');$('#experiment-search').value='';$('#experiment-sort').value='catalog';renderCards();}
function inCollectionScope(demo){return state.scope==='all'||!Object.hasOwn(state.collectionScope.outsideEmbodied,demo.id);}
function renderCards(){
  window.HoverPreviews?.stop();
  const tokens=$('#experiment-search').value.normalize('NFKC').toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
  const matchedVersions=state.data.demos.filter(d=>{
    if(!inCollectionScope(d))return false;
    const project=state.data.projects.find(p=>p.id===d.projectId);
    const searchable=[project?.title,project?.summary,d.id,d.title,d.shortDescription,d.description,d.model,d.task,d.engine,routeNames[d.route],sourceNames[d.source],d.projectBrief?.technicalRoute,d.projectBrief?.modelRole,d.projectBrief?.result].filter(Boolean).join(' ').normalize('NFKC').toLocaleLowerCase();
    if(!tokens.every(token=>searchable.includes(token)))return false;
    if(state.quick==='fresh'&&d.source!=='fresh')return false;
    if(state.quick==='multi'&&(project?.demoCount||d.trials.length)<2)return false;
    return [['#route-filter','route'],['#engine-filter','engine'],['#source-filter','source'],['#task-filter','task']].every(([s,k])=>$(s).value==='all'||$(s).value===d[k]);
  });
  const filtered=state.data.projects.map(project=>{
    const matches=matchedVersions.filter(d=>project.memberIds.includes(d.id));
    const representative=matches.find(d=>d.id===project.representativeId)||matches[0];
    return representative?{...representative,group:project}:null;
  }).filter(Boolean);
  if($('#experiment-sort').value==='newest'){
    const added=p=>Math.max(...p.memberIds.map(id=>state.data.demos.findIndex(d=>d.id===id)));
    filtered.sort((a,b)=>added(b.group)-added(a.group));
  }
  $('#result-count').textContent=`${state.collectionScope.labels[state.scope]} · ${filtered.length} 个项目 · ${filtered.reduce((a,d)=>a+d.group.demoCount,0)} 段成果演示`;
  $('#scope-description').textContent=state.collectionScope.descriptions[state.scope];
  $('#empty-state').hidden=filtered.length>0;
  $('#demo-grid').innerHTML=filtered.map(d=>{
    const p=d.group,index=state.data.projects.findIndex(x=>x.id===p.id)+1;
    const previewIndex=d.id===p.representativeId?d.trials.findIndex(t=>t.originalTrialNumber===p.previewTrialNumber):0;
    const trial=d.trials[Math.max(0,previewIndex)];
    const preview=d.id===p.representativeId?p.preview:{poster:trial.poster||d.poster,video:trial.video,start:trial.agentStartSeconds||0,alt:d.imageAlt||d.title+' 仿真画面'};
    const hover=` data-hover-preview="${escapeHTML(mediaPath(preview.video))}" data-preview-start="${Number(preview.start)||0}"`;
    return `<article class="demo-card" tabindex="0" role="button" aria-label="打开 ${escapeHTML(p.title)}，${p.demoCount} 段成果演示" data-project="${escapeHTML(p.id)}" data-demo="${escapeHTML(d.id)}" data-start-trial="${Math.max(0,previewIndex)}"><div class="card-image"${hover}><img src="${escapeHTML(mediaPath(preview.poster))}" alt="${escapeHTML(preview.alt)}" loading="lazy"><span class="card-index">PROJECT ${String(index).padStart(2,'0')}</span><span class="card-play" aria-hidden="true">▶</span><span class="card-engine">${escapeHTML(d.engine)}</span><span class="hover-preview-hint" aria-hidden="true">悬停预览</span></div><div class="card-body"><div class="badges">${badge(sourceNames[d.source]||d.source,d.source)}${badge(routeNames[d.route]||d.route)}</div><h3>${escapeHTML(p.title)}</h3><p class="project-card-scene">${escapeHTML(d.title)}</p><p>${escapeHTML(p.summary)}</p><div class="card-bottom"><div><strong>${p.demoCount} 段演示</strong>${p.memberIds.length>1?p.memberIds.length+' 种版本 / 场景':'精选成果回放'}</div><span aria-hidden="true">↗</span></div></div></article>`;
  }).join('');
  document.querySelectorAll('[data-demo]').forEach(card=>{const open=()=>openDemo(card.dataset.demo,card,{trial:Number(card.dataset.startTrial)||0});card.onclick=open;card.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open();}};});
}
function renderProjectVersions(d){
  const project=state.data.projects.find(p=>p.id===d.projectId);
  $('#project-versions').hidden=!project||project.memberIds.length<2;
  $('#project-family-title').textContent=project?.title||d.title;
  $('#project-versions-summary').textContent=project?`${project.memberIds.length} 种版本 / 场景 · ${project.demoCount} 段成果`:'';
  $('#project-version-list').innerHTML=(project?.memberIds||[]).map(id=>{
    const version=state.data.demos.find(c=>c.id===id),selected=id===d.id;
    return `<button type="button" class="project-version ${selected?'selected':''}" data-version="${escapeHTML(id)}" aria-pressed="${selected}" aria-label="切换到 ${escapeHTML(version.versionLabel)}"><img src="${escapeHTML(mediaPath(version.poster))}" alt="" loading="lazy"><span>${escapeHTML(version.versionLabel)}</span><small>${version.trials.length} 段演示</small></button>`;
  }).join('');
  document.querySelectorAll('[data-version]').forEach(b=>b.onclick=()=>openDemo(b.dataset.version,null,{history:'replace'}));
}
function renderProjectExplainer(d){
  const b=d.projectBrief,panel=$('#project-explainer');
  panel.hidden=!b;
  if(!b){panel.innerHTML='';return;}
  panel.innerHTML=`<section class="brief-section"><h3><span>01</span>技术路线</h3><p>${escapeHTML(b.technicalRoute)}</p><p class="brief-role">${escapeHTML(b.modelRole)}</p></section><section class="brief-section"><h3><span>02</span>模型如何控制机器人</h3><ol class="control-loop">${b.controlLoop.map(s=>`<li><div><strong>${escapeHTML(s.label)}</strong>${escapeHTML(s.text)}</div></li>`).join('')}</ol></section><section class="brief-section brief-result"><h3><span>03</span>这次做成了什么</h3><p>${escapeHTML(b.result)}</p><p class="brief-limitation"><strong>实现条件：</strong>${escapeHTML(b.limitation)}</p><p class="brief-watch"><strong>看回放时关注：</strong>${escapeHTML(b.watchFor)}</p><p class="brief-display">${escapeHTML(b.displayNote)}</p></section>`;
}
function openDemo(id,opener,options={}){
  window.HoverPreviews?.stop();
  const d=state.data.demos.find(x=>x.id===id);if(!d)return;
  if(!$('#demo-dialog').open)state.returnHash=parseDemoHash(location.hash)?'':location.hash;
  state.selected=d;state.opener=opener||($('#demo-dialog').open?state.opener:null);$('#hero-video').pause();
  $('#dialog-kicker').textContent=`PROJECT ${String(state.data.projects.findIndex(p=>p.id===d.projectId)+1).padStart(2,'0')} / ${d.engine}`;
  $('#detail-route').textContent=d.projectBrief?.familyTitle||routeNames[d.route]||d.route;$('#dialog-title').textContent=d.title;$('#dialog-description').textContent=d.projectBrief?.summary||d.description;
  renderProjectExplainer(d);$('#detail-evidence').open=false;
  renderProjectVersions(d);
  $('#detail-original-description').textContent=d.description;
  $('#detail-badges').innerHTML=badge(sourceNames[d.source]||d.source,d.source)+badge(d.model||d.controller)+badge(d.input);
  $('#detail-metrics').innerHTML=d.metrics.map(m=>`<div><dt>${escapeHTML(m.label)}</dt><dd>${escapeHTML(m.value)}</dd></div>`).join('');
  const related=(d.relatedDemos||[]).filter(r=>state.data.demos.some(item=>item.id===r.id));
  const review=d.publicationReview;
  $('#detail-notes').innerHTML=(review?`<li><strong>本案例关注：</strong>${escapeHTML(review.mechanism)}</li><li><strong>解释边界：</strong>${escapeHTML(review.limitation)}</li>`:'')+d.notes.map(n=>`<li>${escapeHTML(n)}</li>`).join('')+related.map(r=>`<li><a href="${escapeHTML(trialHash(r.id,0))}">${escapeHTML(r.label||'查看关联实验')}</a></li>`).join('')+(review?.evidence||[]).map(p=>`<li><a href="${escapeHTML(p)}" target="_blank" rel="noopener">查看本案例的整理证据 ↗</a></li>`).join('');
  $('#detail-source').href=sourceURL(d.sourceUrl);$('#detail-source').textContent=(d.sourceLabel||'查看开源项目')+' ↗';
  $('#detail-playback-note').textContent=d.playbackNote||'录像按仿真帧率播放，省略模型等待时间。';
  $('#trial-select').disabled=!d.trials.length;
  $('#trial-select').innerHTML=(options.noTrial||!d.trials.length?'<option value="" disabled selected>请选择可展示轨迹</option>':'')+d.trials.map((t,i)=>`<option value="${i}">${escapeHTML(trialName(t,i))} · ${resultLabel(t)}</option>`).join('');
  $('#trial-dots').innerHTML=d.trials.map((t,i)=>`<button class="trial-dot ${t.success===false?'failed':t.success==null?'unknown':''}" data-trial="${i}" aria-label="${escapeHTML(trialName(t,i))}，${resultLabel(t)}" title="${escapeHTML(trialName(t,i))} · ${resultLabel(t)}">${t.originalTrialNumber||i+1}</button>`).join('');
  document.querySelectorAll('[data-trial]').forEach(b=>b.onclick=()=>selectTrial(Number(b.dataset.trial)));
  const project=state.data.projects.find(p=>p.id===d.projectId);
  const preferred=project?.representativeId===d.id?d.trials.findIndex(t=>t.originalTrialNumber===project.previewTrialNumber):0;
  const trial=Number.isInteger(options.trial)&&options.trial>=0&&options.trial<d.trials.length?options.trial:Math.max(0,preferred);
  const noTrial=options.noTrial||!d.trials.length;
  $('#next-trial').disabled=noTrial?!d.trials.length:d.trials.length<2;
  if(noTrial)showProjectWithoutTrial(d,options.hiddenTrialNumber);else selectTrial(trial,false);
  if(options.history!=='none')setPageHash(trialHash(d.id,noTrial?-1:trial),options.history==='replace'?'replace':'push');
  document.body.classList.add('modal-open');if(!$('#demo-dialog').open)$('#demo-dialog').showModal();
  const versions=$('#project-version-list'),activeVersion=versions.querySelector?.('.selected');
  if(activeVersion)versions.scrollLeft=Math.max(0,activeVersion.offsetLeft-(versions.clientWidth-activeVersion.offsetWidth)/2);
  if (typeof renderLearningPanel === 'function') renderLearningPanel(noTrial?{...d,learningReport:null}:d, i => selectTrial(i), state.trial);
}
function showProjectWithoutTrial(d,hiddenTrialNumber){
  state.trial=-1;
  if(typeof invalidateLearningSeek==='function')invalidateLearningSeek();
  const v=$('#detail-video');v.pause();v.removeAttribute('src');v.removeAttribute('poster');v.hidden=true;v.load();
  let empty=$('#detail-video-empty');
  if(!empty){empty=document.createElement('p');empty.id='detail-video-empty';empty.className='detail-video-empty';empty.setAttribute('role','status');v.after(empty);}
  empty.hidden=false;
  empty.textContent=hiddenTrialNumber?`原轨迹 ${hiddenTrialNumber} 已从回放列表隐藏；项目介绍仍保留。${d.trials.length?'请从下方选择其他可展示记录。':'当前暂无完整回放。'}`:'项目介绍保留，当前暂无完整回放；异常或未运行轨迹未在本页播放。';
  $('#detail-playback-note').textContent='当前页面只播放精选成果。请从轨迹列表选择其他演示。';
  $('#trial-details').innerHTML='';$('#agent-seek-status').textContent='';renderDecisions({});updateAgentJump();updateShareLink();
}
function selectTrial(i,updateHash=true){
  const d=state.selected;if(!d||!Number.isInteger(i)||i<0||i>=d.trials.length)return;
  const returningFromHidden=state.trial<0;
  if(typeof invalidateLearningSeek === 'function')invalidateLearningSeek();
  const t=d.trials[i];state.trial=i;const v=$('#detail-video');v.pause();
  let empty=$('#detail-video-empty');
  if(!empty){empty=document.createElement('p');empty.id='detail-video-empty';empty.className='detail-video-empty';empty.setAttribute('role','status');v.after(empty);}
  const hasVideo=typeof t.video==='string'&&t.video.length>0;
  v.hidden=!hasVideo;empty.hidden=hasVideo;
  if(hasVideo){v.src=mediaPath(t.video);v.poster=mediaPath(t.poster||d.poster);}
  else{v.removeAttribute('src');v.removeAttribute('poster');empty.textContent=`${resultLabel(t)} · 暂无可播放录像。`;}
  v.load();$('#trial-select').value=String(i);
  $('#agent-seek-status').textContent='';updateAgentJump();
  document.querySelectorAll('[data-trial]').forEach(b=>{const active=Number(b.dataset.trial)===i;b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));});
  $('#detail-playback-note').textContent=hasVideo?[d.playbackNote||'录像按仿真帧率播放，省略模型等待时间。',t.replayNote||''].filter(Boolean).join(' '):(t.replayNote||'完成状态与记录说明见下方。');
  const info=[resultLabel(t)];if(t.seed!==undefined)info.push(`${t.seedLabel||'重置种子'} ${t.seed}`);if(t.benchmarkSeed!==undefined)info.push(`任务集种子 ${t.benchmarkSeed}`);if(t.goalIndex!==undefined)info.push(`目标索引 ${t.goalIndex}`);if(t.taskId!==undefined)info.push(`Task ${String(t.taskId).padStart(2,'0')}`);if(t.init!==undefined)info.push(`初始状态 ${t.init}`);if(t.steps!==undefined)info.push(`${t.steps} ${t.stepLabel||'控制步'}`);if(t.calls!==undefined)info.push(`${t.calls} 次有效决策`);if(t.attempts!==undefined)info.push(`${t.attempts} 次调用尝试`);if(t.wallSeconds!==undefined)info.push(`墙钟 ${Math.round(t.wallSeconds)} 秒`);if(t.note)info.push(t.note);
  $('#trial-details').innerHTML=info.map(x=>`<span>${escapeHTML(x)}</span>`).join('');
  renderDecisions(t);
  if((d.learningReport?.syncWithTrial||returningFromHidden) && typeof renderLearningPanel === 'function')renderLearningPanel(d, j=>selectTrial(j),i);
  if(updateHash)setPageHash(trialHash(d.id,i));
  updateShareLink();
}
function renderDecisions(trial){
  const rows=trial.video?(trial.decisions||[]):[];$('#decision-panel').hidden=rows.length===0;
  $('#decision-buttons').innerHTML=rows.map((row,i)=>`<button class="decision-button" data-decision="${i}" aria-label="跳到决策 ${row.number}" aria-pressed="false" disabled>${String(row.number).padStart(2,'0')}</button>`).join('');
  document.querySelectorAll('[data-decision]').forEach(b=>b.onclick=()=>{
    const v=$('#detail-video');if(!v.readyState)return;
    v.pause();v.currentTime=rows[Number(b.dataset.decision)].videoSeconds+0.001;syncDecision();
  });
  syncDecision();
}
function syncDecision(){
  if(!state.selected)return;
  const rows=state.selected.trials[state.trial]?.decisions||[];if(!rows.length)return;
  const v=$('#detail-video');let current=-1;
  rows.forEach((row,i)=>{if(v.currentTime+0.0001>=row.videoSeconds)current=i;});
  document.querySelectorAll('[data-decision]').forEach(b=>{
    b.disabled=v.readyState===0;const active=Number(b.dataset.decision)===current;
    b.classList.toggle('selected',active);b.setAttribute('aria-pressed',String(active));
  });
  if(current<0){$('#decision-detail').textContent='初始化阶段：模型尚未发出第一条驾驶指令。';return;}
  const row=rows[current];const signed=n=>`${n>=0?'+':''}${n.toFixed(2)}`;
  $('#decision-detail').innerHTML=`<strong>决策 ${row.number} · 仿真 ${row.simulationSeconds.toFixed(1)} 秒</strong><p>前进指令 ${signed(row.forward)} · 转向指令 ${signed(row.turn)} · 请求持续 ${row.requestedDuration.toFixed(1)} 秒</p><p>本次执行后距目标 ${row.errorAfterCm.toFixed(2)} cm · 模型响应 ${row.modelSeconds.toFixed(1)} 秒</p>`;
}
Promise.all(['data/showcase.json','data/showcase-scope.json'].map(path=>fetch(path,{cache:'no-store'}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();}))).then(([data,scope])=>init(data,scope)).catch(e=>{console.error(e);$('#demo-grid').innerHTML='<p class="error-message">实验索引暂时无法载入，请通过网页服务打开本站后重试。</p>';$('#result-count').textContent='实验索引载入失败';});
