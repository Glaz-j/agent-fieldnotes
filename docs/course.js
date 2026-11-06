'use strict';
// Legacy shared experiment URLs continue to open their original record.
if (/^#(?:demo-|gallery$|method$|routes$)/.test(location.hash) && !location.pathname.includes('/learn/')) location.replace('gallery.html'+location.hash);
const progressKey='agent-fieldnotes-course-v1';
function readProgress(){try{return JSON.parse(localStorage.getItem(progressKey)||'[]').filter(x=>Number.isInteger(x)&&x>=1&&x<=9)}catch{return []}}
const complete=document.querySelector('#lesson-complete');
if(complete){const id=Number(complete.dataset.lesson);complete.checked=readProgress().includes(id);complete.addEventListener('change',()=>{const set=new Set(readProgress());complete.checked?set.add(id):set.delete(id);try{localStorage.setItem(progressKey,JSON.stringify([...set]));document.querySelector('#progress-status').textContent='已保存到此浏览器。'}catch{document.querySelector('#progress-status').textContent='浏览器未允许保存；本次勾选仍有效。'}})}
const saved=readProgress();document.querySelectorAll('[data-chapter]').forEach(el=>{if(saved.includes(Number(el.dataset.chapter))){el.classList.add('done');el.querySelector('.arrow').textContent='✓'}});
const count=document.querySelector('#progress-count');if(count)count.textContent=saved.length+' / 9 章已完成';
for(const pre of document.querySelectorAll('article pre')){const button=document.createElement('button');button.type='button';button.className='copy-code';button.textContent='复制代码';button.addEventListener('click',async()=>{try{await navigator.clipboard.writeText(pre.querySelector('code').textContent);button.textContent='已复制'}catch{button.textContent='请选中代码复制'}});pre.append(button)}
const nav=document.querySelector('.course-nav details');if(nav&&matchMedia('(max-width:680px)').matches)nav.open=false;
