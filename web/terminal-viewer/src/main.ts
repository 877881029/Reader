import "@xterm/xterm/css/xterm.css";
import "./style.css";
import { startTerminal, type TerminalBridge, type TerminalController } from "./terminal";

declare global {
  interface Window {
    qt?: { webChannelTransport?: unknown };
    QWebChannel?: new (
      transport: unknown,
      callback: (channel: { objects: { bridge: TerminalBridge } }) => void,
    ) => unknown;
    readerTerminal?: TerminalController;
    readerTerminalText?: () => string;
  }
}

const root = document.querySelector<HTMLElement>("#app");
if (!root) {
  throw new Error("terminal mount #app is missing");
}

const transport = window.qt?.webChannelTransport;
const QWebChannelCtor = window.QWebChannel;
if (transport && QWebChannelCtor) {
  new QWebChannelCtor(transport, (channel) => {
    const controller = startTerminal(root, channel.objects.bridge);
    window.readerTerminal = controller;
    // Plain buffer text, used by Reader's integration tests.
    window.readerTerminalText = () => {
      const buffer = controller.terminal.buffer.active;
      const lines: string[] = [];
      for (let index = 0; index < buffer.length; index += 1) {
        lines.push(buffer.getLine(index)?.translateToString(true) ?? "");
      }
      return lines.join("\n");
    };
    window.addEventListener("pagehide", () => controller.dispose(), { once: true });
  });
}