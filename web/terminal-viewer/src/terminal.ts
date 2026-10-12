import { FitAddon } from "@xterm/addon-fit";
import { Terminal } from "@xterm/xterm";
import { COPILOT_TERMINAL_THEME, TERMINAL_FONT } from "./theme";

type Listener<T> = (value: T) => void;

export interface TerminalBridge {
  ready(cols: number, rows: number): void;
  input(data: string): void;
  resize(cols: number, rows: number): void;
  copyText(text: string): void;
  output: { connect(cb: Listener<string>): void; disconnect?(cb: Listener<string>): void };
}

export interface TerminalController {
  readonly terminal: Terminal;
  fit(): void;
  dispose(): void;
}

export interface TerminalDeps {
  Terminal: typeof Terminal;
  createFit: () => FitAddon;
}

const defaultDeps: TerminalDeps = { Terminal, createFit: () => new FitAddon() };

export function startTerminal(
  root: HTMLElement,
  bridge: TerminalBridge,
  deps: TerminalDeps = defaultDeps,
): TerminalController {
  const terminal = new deps.Terminal({
    theme: COPILOT_TERMINAL_THEME,
    ...TERMINAL_FONT,
    cursorBlink: true,
    scrollback: 5000,
  });
  const fitAddon = deps.createFit();
  terminal.loadAddon(fitAddon);
  terminal.open(root);
  let disposed = false;

  const fit = (): void => {
    if (disposed) return;
    try {
      fitAddon.fit();
    } catch {
      // Hidden or zero-size containers cannot be measured yet.
    }
  };
  fit();

  const subscriptions = [
    terminal.onData((data) => bridge.input(data)),
    terminal.onBinary((data) => bridge.input(data)),
    terminal.onResize(({ cols, rows }) => bridge.resize(cols, rows)),
  ];

  // Ctrl+C copies a selection (otherwise it interrupts); paste stays native.
  terminal.attachCustomKeyEventHandler((event) => {
    if (event.type !== "keydown" || !event.ctrlKey || event.altKey) return true;
    const key = event.key.toLowerCase();
    if (key === "c" && (event.shiftKey || terminal.hasSelection())) {
      if (terminal.hasSelection()) {
        bridge.copyText(terminal.getSelection());
        terminal.clearSelection();
      }
      return false;
    }
    if (key === "v") return false;
    return true;
  });

  const onOutput: Listener<string> = (data) => {
    if (!disposed) terminal.write(data);
  };
  bridge.output.connect(onOutput);

  const ResizeObserverCtor = globalThis.ResizeObserver;
  const observer = ResizeObserverCtor ? new ResizeObserverCtor(() => fit()) : null;
  observer?.observe(root);

  bridge.ready(terminal.cols, terminal.rows);
  terminal.focus();

  return {
    terminal,
    fit,
    dispose() {
      if (disposed) return;
      disposed = true;
      observer?.disconnect();
      bridge.output.disconnect?.(onOutput);
      for (const subscription of subscriptions) subscription.dispose();
      terminal.dispose();
    },
  };
}