import { startViewer, type MarkdownBridge, type MarkdownController } from "./viewer";
import "./style.css";

const BOOTSTRAP_ERROR_MESSAGE = "Markdown 视觉预览启动失败，请切换文本模式重试。";

declare global {
  interface Window {
    qt?: {
      webChannelTransport?: unknown;
    };
    QWebChannel?: new (
      transport: unknown,
      callback: (channel: { objects: { bridge: MarkdownBridge } }) => void,
    ) => unknown;
    readerMdDispose?: () => void;
  }
}

const rootElement = document.querySelector<HTMLElement>("#app");

if (!rootElement) {
  throw new Error("viewer mount #app is missing");
}
const root = rootElement;

root.classList.add("markdown-document");
let disposed = false;
let viewerController: MarkdownController | null = null;
let abortController: AbortController | null = null;
const onPageHide = () => disposeViewer();
const onBeforeUnload = () => disposeViewer();

function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

function disposeViewer(): void {
  if (disposed) {
    return;
  }
  disposed = true;
  window.removeEventListener("pagehide", onPageHide);
  window.removeEventListener("beforeunload", onBeforeUnload);
  window.readerMdDispose = undefined;
  abortController?.abort();
  abortController = null;
  viewerController?.destroy();
  viewerController = null;
}

window.readerMdDispose = disposeViewer;
window.addEventListener("pagehide", onPageHide);
window.addEventListener("beforeunload", onBeforeUnload);

async function bootstrap(): Promise<void> {
  const bridge = await new Promise<MarkdownBridge>((resolve, reject) => {
    const transport = window.qt?.webChannelTransport;
    const QWebChannelCtor = window.QWebChannel;
    if (!transport || !QWebChannelCtor) {
      reject(new Error("qt webchannel unavailable"));
      return;
    }
    new QWebChannelCtor(transport, (channel) => {
      resolve(channel.objects.bridge);
    });
  });
  if (disposed) {
    return;
  }

  try {
    abortController = new AbortController();
    const response = await fetch(bridge.sourceUrl, { signal: abortController.signal });
    if (!response.ok) {
      throw new Error(`fetch failed: ${response.status}`);
    }
    const source = await response.text();
    if (disposed) {
      return;
    }
    viewerController = await startViewer(root, source, bridge.sourceUrl, bridge, abortController.signal);
    if (disposed) {
      viewerController.destroy();
      viewerController = null;
    }
  } catch (error) {
    if (disposed || isAbortError(error)) {
      return;
    }
    bridge.viewerError(BOOTSTRAP_ERROR_MESSAGE);
  }
}

void bootstrap();
