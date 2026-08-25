import "./style.css";

const app = document.querySelector<HTMLDivElement>("#app");

if (!app) {
  throw new Error("Missing #app mount point");
}

app.innerHTML = `
  <section class="viewer-shell" data-bridge-ready="false">
    <header class="viewer-shell__header">Reader PPTX Visual Preview</header>
    <div class="viewer-shell__body">
      <aside class="viewer-shell__thumbs">Thumbnails placeholder</aside>
      <article class="viewer-shell__slide">Slide canvas placeholder</article>
    </div>
  </section>
`;
