import type { ITheme } from "@xterm/xterm";

/** Copilot light surface with the GitHub Light ANSI palette. */
export const COPILOT_TERMINAL_THEME: ITheme = {
  background: "#fbf9f5",
  foreground: "#1f1d1a",
  cursor: "#1f1d1a",
  cursorAccent: "#fbf9f5",
  selectionBackground: "#e9e3d9",
  black: "#24292f",
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
  fontSize: 13,
  lineHeight: 1.2,
};