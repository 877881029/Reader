import mermaid from "mermaid";

let initialized = false;
let renderCounter = 0;

function ensureInitialized(): void {
  if (initialized) {
    return;
  }
  mermaid.initialize({
    startOnLoad: false,
    securityLevel: "strict",
    theme: "neutral",
    suppressErrorRendering: true,
  });
  initialized = true;
}

function buildErrorSection(source: string): HTMLElement {
  const section = document.createElement("section");
  section.className = "mermaid-error";

  const title = document.createElement("strong");
  title.textContent = "图表无法渲染";

  const pre = document.createElement("pre");
  const code = document.createElement("code");
  code.textContent = source;
  pre.append(code);

  section.append(title, pre);
  return section;
}

export async function renderMermaidBlocks(root: HTMLElement): Promise<void> {
  ensureInitialized();
  const blocks = Array.from(root.querySelectorAll<HTMLElement>("pre > code.language-mermaid"));

  await Promise.all(
    blocks.map(async (codeBlock) => {
      const source = codeBlock.textContent ?? "";
      const pre = codeBlock.parentElement;
      if (!pre || pre.tagName !== "PRE") {
        return;
      }

      try {
        const renderResult = await mermaid.render(`reader-mermaid-${renderCounter++}`, source);
        const section = document.createElement("section");
        section.className = "mermaid-rendered";
        section.innerHTML = renderResult.svg;
        pre.replaceWith(section);
      } catch {
        pre.replaceWith(buildErrorSection(source));
      }
    }),
  );
}
