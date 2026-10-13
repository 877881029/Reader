import { afterEach, describe, expect, it, vi } from "vitest";
import { COPILOT_TERMINAL_THEME, TERMINAL_FONT } from "./theme";
import { startTerminal, type TerminalBridge } from "./terminal";

type Handler<T> = (value: T) => void;

class FakeTerminal {
  static last: FakeTerminal | null = null;
  options: Record<string, unknown>;
  cols = 80;
  rows = 24;
  opened: HTMLElement | null = null;
  written: string[] = [];
  addons: unknown[] = [];
  dataHandler: Handler<string> | null = null;
  binaryHandler: Handler<string> | null = null;
  resizeHandler: Handler<{ cols: number; rows: number }> | null = null;
  keyHandler: ((event: KeyboardEvent) => boolean) | null = null;
  selection = "";
  disposed = false;
  focused = false;

  constructor(options: Record<string, unknown>) {
    this.options = options;
    FakeTerminal.last = this;
  }
  loadAddon(addon: unknown): void {
    this.addons.push(addon);
  }
  open(element: HTMLElement): void {
    this.opened = element;
  }
  write(data: string): void {
    this.written.push(data);
  }
  onData(handler: Handler<string>) {
    this.dataHandler = handler;
    return { dispose: () => undefined };
  }
  onBinary(handler: Handler<string>) {
    this.binaryHandler = handler;
    return { dispose: () => undefined };
  }
  onResize(handler: Handler<{ cols: number; rows: number }>) {
    this.resizeHandler = handler;
    return { dispose: () => undefined };
  }
  attachCustomKeyEventHandler(handler: (event: KeyboardEvent) => boolean): void {
    this.keyHandler = handler;
  }
  hasSelection(): boolean {
    return this.selection.length > 0;
  }
  getSelection(): string {
    return this.selection;
  }
  clearSelection(): void {
    this.selection = "";
  }
  focus(): void {
    this.focused = true;
  }
  dispose(): void {
    this.disposed = true;
  }
}

class FakeFit {
  fits = 0;
  fit(): void {
    this.fits += 1;
  }
}

function fakeBridge() {
  const outputListeners: Handler<string>[] = [];
  const bridge: TerminalBridge = {
    ready: vi.fn(),
    input: vi.fn(),
    resize: vi.fn(),
    copyText: vi.fn(),
    output: {
      connect: (cb: Handler<string>) => outputListeners.push(cb),
      disconnect: (cb: Handler<string>) => {
        const index = outputListeners.indexOf(cb);
        if (index >= 0) outputListeners.splice(index, 1);
      },
    },
  };
  return { bridge, emit: (data: string) => outputListeners.forEach((cb) => cb(data)), outputListeners };
}

function start() {
  const root = document.createElement("div");
  document.body.replaceChildren(root);
  const { bridge, emit, outputListeners } = fakeBridge();
  const fit = new FakeFit();
  const controller = startTerminal(root, bridge, {
    Terminal: FakeTerminal as never,
    createFit: () => fit as never,
  });
  return { root, bridge, emit, outputListeners, fit, controller, term: FakeTerminal.last! };
}

function key(init: KeyboardEventInit): KeyboardEvent {
  return new KeyboardEvent("keydown", init);
}

afterEach(() => {
  document.body.replaceChildren();
});

describe("Copilot terminal theme", () => {
  it("uses the Copilot light surface and GitHub Light ANSI colours", () => {
    expect(COPILOT_TERMINAL_THEME.background).toBe("#f6f2ee");
    expect(COPILOT_TERMINAL_THEME.cursorAccent).toBe("#f6f2ee");
    expect(COPILOT_TERMINAL_THEME.foreground).toBe("#3d2b5a");
    expect(COPILOT_TERMINAL_THEME.black).toBe("#3d2b5a");
    expect(COPILOT_TERMINAL_THEME.cursor).toBe("#2848a9");
    expect(COPILOT_TERMINAL_THEME.selectionBackground).toBe("#ddd5ee");
    expect(COPILOT_TERMINAL_THEME.red).toBe("#cf222e");
    expect(COPILOT_TERMINAL_THEME.blue).toBe("#0969da");
    expect(COPILOT_TERMINAL_THEME.brightGreen).toBe("#1a7f37");
    expect(TERMINAL_FONT.fontFamily).toContain("Cascadia Mono");
    expect(TERMINAL_FONT.fontSize).toBe(12);
    expect(TERMINAL_FONT.fontWeight).toBe("normal");
    expect(TERMINAL_FONT.lineHeight).toBe(1.25);
  });
});

describe("startTerminal", () => {
  it("opens with theme, fits, reports size and focuses", () => {
    const { root, bridge, fit, term } = start();
    expect(term.opened).toBe(root);
    expect(term.options.theme).toBe(COPILOT_TERMINAL_THEME);
    expect(term.addons).toContain(fit);
    expect(fit.fits).toBeGreaterThan(0);
    expect(bridge.ready).toHaveBeenCalledWith(80, 24);
    expect(term.focused).toBe(true);
  });

  it("pipes keystrokes, binary input, resizes and shell output", () => {
    const { bridge, emit, term } = start();
    term.dataHandler?.("dir\r");
    term.binaryHandler?.("\x1b[M");
    expect(bridge.input).toHaveBeenNthCalledWith(1, "dir\r");
    expect(bridge.input).toHaveBeenNthCalledWith(2, "\x1b[M");
    term.resizeHandler?.({ cols: 120, rows: 40 });
    expect(bridge.resize).toHaveBeenCalledWith(120, 40);
    emit("hello\r\n");
    expect(term.written).toEqual(["hello\r\n"]);
  });

  it("copies selection on Ctrl+C, otherwise lets Ctrl+C interrupt; leaves paste to the browser", () => {
    const { bridge, term } = start();
    expect(term.keyHandler?.(key({ key: "c", ctrlKey: true }))).toBe(true);
    expect(bridge.copyText).not.toHaveBeenCalled();

    term.selection = "copied";
    expect(term.keyHandler?.(key({ key: "c", ctrlKey: true }))).toBe(false);
    expect(bridge.copyText).toHaveBeenCalledWith("copied");
    expect(term.hasSelection()).toBe(false);

    term.selection = "again";
    expect(term.keyHandler?.(key({ key: "C", ctrlKey: true, shiftKey: true }))).toBe(false);
    expect(bridge.copyText).toHaveBeenLastCalledWith("again");

    expect(term.keyHandler?.(key({ key: "v", ctrlKey: true }))).toBe(false);
    expect(term.keyHandler?.(key({ key: "V", ctrlKey: true, shiftKey: true }))).toBe(false);
    expect(term.keyHandler?.(new KeyboardEvent("keyup", { key: "c", ctrlKey: true }))).toBe(true);
  });

  it("disposes terminal and stops writing output", () => {
    const { emit, outputListeners, term, controller } = start();
    controller.dispose();
    controller.dispose();
    expect(term.disposed).toBe(true);
    expect(outputListeners).toHaveLength(0);
    emit("late");
    expect(term.written).toEqual([]);
  });
});