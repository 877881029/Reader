import type { ITheme } from "@xterm/xterm";

/** Copilot terminal colours (sampled) with the GitHub Light ANSI palette. */
export const COPILOT_TERMINAL_THEME: ITheme = {
  background: "#f6f2ee",
  foreground: "#3d2b5a",
  cursor: "#2848a9",
  cursorAccent: "#f6f2ee",
  selectionBackground: "#ddd5ee",
  black: "#3d2b5a",
  red: "#cf222e",
  green: "#116329",
  yellow: "#4d2d00",
  blue: "#0969da",
  magenta: "#8250df",
  cyan: "#1b7c83",
  white: "#6e7781",
  brightBlack: "#57606a",
  brightRed: "#a40e26",
  brightGreen: "#1a7f37",
  brightYellow: "#633c01",
  brightBlue: "#218bff",
  brightMagenta: "#a475f9",
  brightCyan: "#3192aa",
  brightWhite: "#8c959f",
};

export const TERMINAL_FONT = {
  fontFamily: '"Cascadia Mono", Consolas, "Courier New", monospace',
  fontSize: 12,
  fontWeight: "normal" as const,
  lineHeight: 1.25,
};