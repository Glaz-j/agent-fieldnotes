'use strict';
// A single, lazy video at a time; both galleries use this delegated controller.
(() => {
  let active=null, pending=null, hoverTimer;
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');
  const validSource=src=>typeof src==='string'&&src.startsWith('media/')&&!src.includes('..');
  function stop(){
    clearTimeout(hoverTimer);pending=null;
    const old=active;active=null;
    if(!old)return;
    clearTimeout(old.timeout);old.observer?.disconnect();
    old.host.classList.remove('is-preview-playing');
    if(old.hint)old.hint.textContent='悬停预览';
    old.video.pause();old.video.removeAttribute('src');old.video.load();old.video.remove();
  }
  function start(host){
    if(!host.isConnected||document.hidden||reducedMotion.matches||!validSource(host.dataset.hoverPreview))return;
    const video=document.createElement('video');
    video.className='hover-preview-video';video.muted=true;video.defaultMuted=true;
    video.playsInline=true;video.preload='auto';video.disablePictureInPicture=true;
    video.tabIndex=-1;video.setAttribute('aria-hidden','true');
    const session={host,video,hint:host.querySelector('.hover-preview-hint'),start:0,end:6};
    active=session;
    const current=()=>active===session;
    const failed=()=>{if(current())stop();};
    const play=()=>{const promise=video.play();if(promise)promise.catch(failed);};
    video.addEventListener('loadedmetadata',()=>{
      if(!current())return;
      const requested=Number(host.dataset.previewStart)||0;
      const duration=Number.isFinite(video.duration)?video.duration:requested+6;
      session.start=Math.max(0,Math.min(requested,Math.max(0,duration-.15)));
      session.end=Math.min(duration,session.start+6);
      video.currentTime=session.start;play();
    },{once:true});
    video.addEventListener('playing',()=>{
      if(!current())return;
      clearTimeout(session.timeout);host.classList.add('is-preview-playing');
      if(session.hint)session.hint.textContent='静音预览';
    });
    const rewind=()=>{if(current()){video.currentTime=session.start;if(video.paused)play();}};
    video.addEventListener('timeupdate',()=>{if(current()&&video.currentTime>=session.end)rewind();});
    video.addEventListener('ended',rewind);video.addEventListener('error',failed);
    if(session.hint)session.hint.textContent='加载预览…';
    session.timeout=setTimeout(failed,12000);
    if(typeof IntersectionObserver!=='undefined'){
      session.observer=new IntersectionObserver(entries=>{if(current()&&!entries[0].isIntersecting)stop();});
      session.observer.observe(host);
    }
    host.append(video);video.src=host.dataset.hoverPreview;video.load();
  }
  function schedule(host){
    if(active?.host===host||pending===host)return;
    stop();
    if(!host||reducedMotion.matches||document.hidden)return;
    pending=host;
    hoverTimer=setTimeout(()=>{pending=null;start(host);},180);
  }
  function hostFor(node){
    return node instanceof Element?node.closest('.demo-card,.catalog-preview-card')?.querySelector('[data-hover-preview]'):null;
  }
  document.addEventListener('pointerover',event=>{
    if(event.pointerType!=='mouse')return;
    const host=hostFor(event.target);
    if(host!==hostFor(event.relatedTarget))schedule(host);
  });
  document.addEventListener('pointerout',event=>{
    const host=hostFor(event.target);
    if(host&&host!==hostFor(event.relatedTarget))stop();
  });
  document.addEventListener('pointerdown',stop,true);
  document.addEventListener('click',stop,true);
  document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});
  window.addEventListener('blur',stop);window.addEventListener('pagehide',stop);
  reducedMotion.addEventListener('change',stop);
  window.HoverPreviews=Object.freeze({stop});
})();
