(function(){const t=document.createElement("link").relList;if(t&&t.supports&&t.supports("modulepreload"))return;for(const e of document.querySelectorAll('link[rel="modulepreload"]'))i(e);new MutationObserver(e=>{for(const r of e)if(r.type==="childList")for(const s of r.addedNodes)s.tagName==="LINK"&&s.rel==="modulepreload"&&i(s)}).observe(document,{childList:!0,subtree:!0});function l(e){const r={};return e.integrity&&(r.integrity=e.integrity),e.referrerPolicy&&(r.referrerPolicy=e.referrerPolicy),e.crossOrigin==="use-credentials"?r.credentials="include":e.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function i(e){if(e.ep)return;e.ep=!0;const r=l(e);fetch(e.href,r)}})();const o=document.querySelector("#app");if(!o)throw new Error("Missing #app mount point");o.innerHTML=`
  <section class="viewer-shell" data-bridge-ready="false">
    <header class="viewer-shell__header">Reader PPTX Visual Preview</header>
    <div class="viewer-shell__body">
      <aside class="viewer-shell__thumbs">Thumbnails placeholder</aside>
      <article class="viewer-shell__slide">Slide canvas placeholder</article>
    </div>
  </section>
`;
