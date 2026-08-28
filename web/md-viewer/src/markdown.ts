import MarkdownIt from "markdown-it";
export interface WikiLink {
  element: HTMLAnchorElement;
  target: string;
}

const wikiLinkRuleName = "reader-wikilink";
const wikiClassName = "wiki-link is-pending";

function createWikiLinkRule() {
  return (state: any, silent: boolean): boolean => {
    if (state.linkLevel > 0) {
      return false;
    }

    const start = state.pos;
    if (start + 4 > state.posMax) {
      return false;
    }
    if (state.src.charCodeAt(start) !== 0x5b || state.src.charCodeAt(start + 1) !== 0x5b) {
      return false;
    }

    const end = state.src.indexOf("]]", start + 2);
    if (end < 0 || end > state.posMax) {
      return false;
    }

    const inner = state.src.slice(start + 2, end);
    const separator = inner.indexOf("|");
    const rawTarget = separator >= 0 ? inner.slice(0, separator) : inner;
    const rawAlias = separator >= 0 ? inner.slice(separator + 1) : "";
    const target = rawTarget.trim();
    const alias = separator >= 0 ? rawAlias.trim() : target;

    if (!target || !alias) {
      return false;
    }

    if (silent) {
      return false;
    }

    const open = state.push("link_open", "a", 1);
    open.attrSet("class", wikiClassName);
    open.attrSet("data-wiki-target", target);

    const text = state.push("text", "", 0);
    text.content = alias;

    state.push("link_close", "a", -1);
    state.pos = end + 2;
    return true;
  };
}

function isRelativeAssetPath(value: string): boolean {
  if (!value) {
    return false;
  }
  if (value.startsWith("//") || value.startsWith("#")) {
    return false;
  }
  return !/^[a-zA-Z][a-zA-Z\d+.-]*:/.test(value);
}

const parser = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: false,
  breaks: false,
}).enable(["table", "strikethrough"]);

parser.inline.ruler.before("link", wikiLinkRuleName, createWikiLinkRule());

function wrapTables(fragment: DocumentFragment): void {
  const tables = fragment.querySelectorAll("table");
  for (const table of tables) {
    if (table.parentElement?.classList.contains("table-scroll")) {
      continue;
    }
    const wrapper = document.createElement("div");
    wrapper.className = "table-scroll";
    table.parentNode?.insertBefore(wrapper, table);
    wrapper.append(table);
  }
}

function rewriteRelativeImages(fragment: DocumentFragment, sourceUrl: string): void {
  const images = fragment.querySelectorAll<HTMLImageElement>("img[src]");
  for (const image of images) {
    const rawSource = image.getAttribute("src")?.trim() ?? "";
    if (!isRelativeAssetPath(rawSource)) {
      continue;
    }
    try {
      image.src = new URL(rawSource, sourceUrl).href;
    } catch {
      // Keep original source when URL base or path is invalid.
    }
  }
}

export function renderMarkdown(source: string, sourceUrl: string): {
  fragment: DocumentFragment;
  wikiLinks: WikiLink[];
} {
  const template = document.createElement("template");
  template.innerHTML = parser.render(source);

  rewriteRelativeImages(template.content, sourceUrl);
  wrapTables(template.content);

  const wikiLinks = Array.from(
    template.content.querySelectorAll<HTMLAnchorElement>("a.wiki-link[data-wiki-target]"),
  ).map((element) => ({
    element,
    target: element.dataset.wikiTarget ?? "",
  }));

  return { fragment: template.content, wikiLinks };
}
