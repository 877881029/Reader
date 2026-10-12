# Welcome Page Neutral Theme Design

Status: Implemented
Progress ledger: `docs/STATUS.md`

## Background

The welcome page uses saturated cobalt for the accent bar, primary and
secondary buttons, every recent-file badge, list selection and a large ghost
"R" watermark. The user finds it too busy and wants the calm, monochrome look
of the GitHub Copilot app. Layout stays exactly as it is.

## Scope (colours and type only)

- Neutral palette on the existing paper background: ink `#1f1d1a`, secondary
  text `#5f5850`, muted text `#8f877d`, hairline `#e6dfd4`, surface `#fbf9f5`,
  hover `#f0ebe3`, selected `#e9e3d9`, focus border `#b9b0a3`.
- Primary 打开文件: ink fill, paper text; hover `#3a3631`.
- Secondary 新建 Markdown: transparent, hairline border, ink text, hover fill.
- Accent bar: ink. Divider rule: hairline. Ghost "R" watermark removed.
- Recent cards: surface fill, hairline border, hover/selected neutral fills.
- Badges: neutral chip (hover colour fill, secondary text), no blue.
- Fonts: Segoe UI family for all UI text; brand keeps its size/weight.

## Non-goals

- No layout, spacing, sizing or behaviour change; no change to other pages,
  document rendering, code highlighting or the title chrome.

## Acceptance

- Welcome stylesheet and painting contain no cobalt (`#2563eb`, `#1d4ed8`,
  `#1e40af`, `#eaf0ff`, `rgba(37, 99, 235`).
- Primary button background is the ink colour; badges use the neutral chip.
- No watermark glyph is painted.