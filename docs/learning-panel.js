'use strict';
let learningSeekSequence = 0;
function invalidateLearningSeek() { learningSeekSequence += 1; }
function renderLearningPanel(demo, chooseTrial, activeTrialIndex = 0) {
  let panel = document.getElementById('learning-panel');
  if (!panel) {
    panel = document.createElement('section');
    panel.id = 'learning-panel'; panel.className = 'learning-panel';
    (document.getElementById('project-explainer')||document.getElementById('detail-metrics')).after(panel);
  }
  const report = demo.learningReport;
  panel.hidden = !report?.stages?.length;
  panel.replaceChildren();
  if (panel.hidden) return;
  const heading = document.createElement('h3'); heading.textContent = report.title;
  const controls = document.createElement('div'); controls.className='learning-stages';
  controls.setAttribute('aria-label',report.controlLabel || '世界规则版本');
  const description = document.createElement('p'); description.className='learning-description';
  description.setAttribute('aria-live','polite');
  const codeArea = document.createElement('div'); codeArea.className='learning-code';
  const view = document.createElement('button'); view.type='button'; view.className='button small';
  view.textContent='查看这个阶段的轨迹 ↗';
  let selected = 0;
  const show = index => {
    selected=index; const stage=report.stages[index];
    [...controls.children].forEach((b,i)=>b.setAttribute('aria-pressed',String(i===index)));
    description.textContent=stage.description; codeArea.replaceChildren();
    for (const block of stage.blocks || []) {
      const details=document.createElement('details');
      const summary=document.createElement('summary'); summary.textContent=block.label;
      const pre=document.createElement('pre'); const code=document.createElement('code');
      code.textContent=block.code; pre.append(code); details.append(summary,pre); codeArea.append(details);
    }
    for (const item of stage.images || []) {
      const figure=document.createElement('figure'); figure.className='learning-figure';
      const link=document.createElement('a');link.href=item.src;link.target='_blank';link.rel='noopener noreferrer';
      const img=document.createElement('img');img.src=item.src;img.alt=item.alt;img.loading='lazy';
      const caption=document.createElement('figcaption');caption.textContent=item.caption || '点击查看完整图表';
      link.append(img);figure.append(link,caption);codeArea.append(figure);
    }
  };
  report.stages.forEach((stage,i)=>{
    const button=document.createElement('button');button.type='button';button.textContent=stage.title;
    button.addEventListener('click',()=>report.syncWithTrial ? chooseTrial(stage.trialIndex) : show(i)); controls.append(button);
  });
  view.addEventListener('click',()=>{
    const stage=report.stages[selected];
    chooseTrial(stage.trialIndex);
    const token=++learningSeekSequence;
    const video=document.getElementById('detail-video');
    const seek=()=>{if(token===learningSeekSequence && Number.isFinite(video.duration))video.currentTime=Math.min(stage.videoSeconds,Math.max(0,video.duration-.05));};
    if(video.readyState>0)seek();else video.addEventListener('loadedmetadata',seek,{once:true});
    video.scrollIntoView({behavior:'smooth',block:'nearest'});
  });
  panel.append(heading,controls,description,codeArea,view);
  show(report.syncWithTrial ? Math.max(0,report.stages.findIndex(s=>s.trialIndex===activeTrialIndex)) : 0);
}
