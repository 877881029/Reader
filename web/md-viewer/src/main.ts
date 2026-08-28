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

function disposeViewer(): void {
  if (disposed) {
    return;
  }
  disposed = true;
  abortController?.abort();
  abortController = null;
  viewerController?.destroy();
  viewerController = null;
}

window.readerMdDispose = disposeViewer;
window.addEventListener("pagehide", disposeViewer);
window.addEventListener("beforeunload", disposeViewer);

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

  try {
    abortController = new AbortController();
    const response = await fetch(bridge.sourceUrl);
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
  } catch {
    bridge.viewerError(BOOTSTRAP_ERROR_MESSAGE);
  }
}

void bootstrap();
