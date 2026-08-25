import "./style.css";
import { startViewer, type ViewerBridge } from "./viewer";

interface ReaderViewerBridge extends ViewerBridge {
  sourceUrl: string;
  testFailSlide?: number;
}

declare global {
  interface Window {
    qt?: { webChannelTransport: unknown };
    readerPptxDispose?: () => void;
    QWebChannel?: new (
      transport: unknown,
      callback: (channel: { objects: { bridge: ReaderViewerBridge } }) => void,
    ) => object;
  }
}

const app = document.querySelector<HTMLElement>("#app");

if (!app) {
  throw new Error("viewer mount #app is missing");
}
const mount = app;
const abortController = new AbortController();
let activeController: Awaited<ReturnType<typeof startViewer>>;
let disposed = false;

function disposeViewer(): void {
  if (disposed) {
    return;
  }
  disposed = true;
  window.removeEventListener("pagehide", disposeViewer);
  window.removeEventListener("beforeunload", disposeViewer);
  abortController.abort();
  activeController?.destroy();
  activeController = undefined;
}

window.readerPptxDispose = disposeViewer;
window.addEventListener("pagehide", disposeViewer, { once: true });
window.addEventListener("beforeunload", disposeViewer, { once: true });

function showBootstrapError(message: string): void {
  mount.className = "viewer-bootstrap-error";
  mount.textContent = message;
}

function isFileUrl(sourceUrl: string): boolean {
  try {
    return new URL(sourceUrl).protocol === "file:";
  } catch {
    return false;
  }
}

if (!window.qt?.webChannelTransport || !window.QWebChannel) {
  showBootstrapError("Reader bridge unavailable");
} else {
  new window.QWebChannel(window.qt.webChannelTransport, ({ objects }) => {
    const bridge = objects.bridge;
    if (!isFileUrl(bridge.sourceUrl)) {
      const message = "Reader requires a local file URL";
      showBootstrapError(message);
      bridge.viewerError(message);
      return;
    }

    void startViewer(mount, bridge.sourceUrl, bridge, {
      testFailSlide: bridge.testFailSlide,
      signal: abortController.signal,
    })
      .then((controller) => {
        if (disposed) {
          controller?.destroy();
          return;
        }
        activeController = controller;
      })
      .catch((error: unknown) => {
        showBootstrapError(error instanceof Error ? error.message : String(error));
      });
  });
}
