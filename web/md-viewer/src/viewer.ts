import { renderMarkdown } from "./markdown";
import { renderMermaidBlocks } from "./mermaid";

export interface MarkdownBridge {
  sourceUrl: string;
  viewerReady(): void;
  viewerError(message: string): void;
  wikiExists(target: string, callback: (exists: boolean) => void): void;
  openWiki(target: string): void;
}

export interface MarkdownController {
  destroy(): void;
}

const remoteLinkPattern = /^(https?|wss?):/i;
const controllers = new WeakMap<HTMLElement, MarkdownController>();
const WIKI_EXISTS_TIMEOUT_MS = 2000;

export async function startViewer(
  root: HTMLElement,
  source: string,
  sourceUrl: string,
  bridge: MarkdownBridge,
  signal?: AbortSignal,
): Promise<MarkdownController> {
  controllers.get(root)?.destroy();

  let active = true;
  const cleanup: Array<() => void> = [];
  const pendingWikiResolvers: Array<() => void> = [];
  let readyEmitted = false;

  const controller: MarkdownController = {
    destroy: () => {
      if (!active) {
        return;
      }
      active = false;

      for (const dispose of cleanup.splice(0)) {
        dispose();
      }
      for (const resolvePending of pendingWikiResolvers.splice(0)) {
        resolvePending();
      }

      root.replaceChildren();
      if (controllers.get(root) === controller) {
        controllers.delete(root);
      }
    },
  };
  controllers.set(root, controller);

  if (signal?.aborted) {
    controller.destroy();
    return controller;
  }

  const abortHandler = () => controller.destroy();
  signal?.addEventListener("abort", abortHandler, { once: true });
  cleanup.push(() => signal?.removeEventListener("abort", abortHandler));

  root.classList.add("markdown-document");
  const { fragment, wikiLinks } = renderMarkdown(source, sourceUrl);
  root.replaceChildren(fragment);

  for (const anchor of Array.from(root.querySelectorAll<HTMLAnchorElement>("a[href]"))) {
    const href = anchor.getAttribute("href") ?? "";
    if (!remoteLinkPattern.test(href)) {
      continue;
    }
    const onClick = (event: MouseEvent) => {
      event.preventDefault();
    };
    anchor.addEventListener("click", onClick);
    cleanup.push(() => anchor.removeEventListener("click", onClick));
  }

  const wikiChecks = wikiLinks.map(
    ({ element, target }) =>
      new Promise<void>((resolve) => {
        let settled = false;
        let timeoutId: ReturnType<typeof setTimeout> | null = null;

        const clearWikiTimeout = () => {
          if (timeoutId === null) {
            return;
          }
          clearTimeout(timeoutId);
          timeoutId = null;
        };

        const resolveOnce = () => {
          if (settled) {
            return;
          }
          settled = true;
          clearWikiTimeout();
          resolve();
        };
        pendingWikiResolvers.push(resolveOnce);

        const settleWikiExists = (exists: boolean) => {
          if (settled || !active) {
            resolveOnce();
            return;
          }
          element.classList.remove("is-pending");
          element.classList.toggle("is-resolved", exists);
          element.classList.toggle("is-missing", !exists);
          resolveOnce();
        };

        const onClick = (event: MouseEvent) => {
          event.preventDefault();
          if (!active) {
            return;
          }
          bridge.openWiki(target);
        };
        element.addEventListener("click", onClick);
        cleanup.push(() => element.removeEventListener("click", onClick));

        timeoutId = setTimeout(() => {
          settleWikiExists(false);
        }, WIKI_EXISTS_TIMEOUT_MS);

        try {
          bridge.wikiExists(target, (exists: boolean) => {
            settleWikiExists(Boolean(exists));
          });
        } catch {
          settleWikiExists(false);
        }
      }),
  );

  await Promise.all([renderMermaidBlocks(root), Promise.all(wikiChecks)]);

  if (active && !readyEmitted) {
    readyEmitted = true;
    bridge.viewerReady();
  }

  return controller;
}
