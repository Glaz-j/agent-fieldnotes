'use strict';
// Legacy shared experiment URLs continue to open their original record.
if (/^#(?:demo-|gallery$|method$|routes$)/.test(location.hash) && !location.pathname.includes('/learn/')) location.replace('gallery.html'+location.hash);
const lessonCount=Number(document.body.dataset.lessonCount)||16;
const progressKey='agent-fieldnotes-course-v1';
function readProgress(){try{return [...new Set(JSON.parse(localStorage.getItem(progressKey)||'[]'))].filter(x=>Number.isInteger(x)&&x>=1&&x<=lessonCount)}catch{return []}}
const complete=document.querySelector('#lesson-complete');
if(complete){const id=Number(complete.dataset.lesson);complete.checked=readProgress().includes(id);complete.addEventListener('change',()=>{const set=new Set(readProgress());complete.checked?set.add(id):set.delete(id);try{localStorage.setItem(progressKey,JSON.stringify([...set]));document.querySelector('#progress-status').textContent='已保存到此浏览器。'}catch{document.querySelector('#progress-status').textContent='浏览器未允许保存；本次勾选仍有效。'}})}
const saved=readProgress();document.querySelectorAll('[data-chapter]').forEach(el=>{if(saved.includes(Number(el.dataset.chapter))){el.classList.add('done');el.querySelector('.arrow').textContent='✓'}});
const count=document.querySelector('#progress-count');if(count)count.textContent=saved.length+' / '+lessonCount+' 章已完成';
for(const pre of document.querySelectorAll('article pre')){const button=document.createElement('button');button.type='button';button.className='copy-code';button.textContent='复制代码';button.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(pre.querySelector('code').textContent);button.textContent='已复制'}catch{button.textContent='请选中代码复制'}});pre.append(button)}
const nav=document.querySelector('.course-nav details');
if(nav){if(matchMedia('(max-width:680px)').matches){nav.open=false}else{const current=nav.querySelector('[aria-current=page]');const sidebar=nav.closest('.course-nav');if(current&&sidebar)sidebar.scrollTop=Math.max(0,current.offsetTop-sidebar.clientHeight/2)}}

// Readers choose when to play; a single film plays at a time.
for(const figure of document.querySelectorAll('.lesson-demo')){
  const video=figure.querySelector('video');
  video.addEventListener('play',()=>{document.querySelectorAll('video').forEach(other=>{if(other!==video)other.pause()})});
  const buttons=[...figure.querySelectorAll('[data-seek]')];
  for(const button of buttons){button.addEventListener('click',()=>{
    const seek=()=>{video.currentTime=Number(button.dataset.seek);video.scrollIntoView({block:'center'});video.play().catch(()=>{})};
    if(video.readyState>=1)seek();else{video.addEventListener('loadedmetadata',seek,{once:true});video.load()}
  })}
  video.addEventListener('timeupdate',()=>{
    let active=null;for(const button of buttons){if(Number(button.dataset.seek)<=video.currentTime)active=button}
    for(const button of buttons){if(button===active)button.setAttribute('aria-current','true');else button.removeAttribute('aria-current')}
  });
}
