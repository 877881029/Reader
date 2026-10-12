# Browser Tab Design

Status: Implemented
Progress ledger: `docs/STATUS.md`

## Background

The `+` menu lists **Browser** as a disabled placeholder. The user asked to
implement it: a lightweight web page tab inside Reader, Copilot-panel style.

## Scope

- `+` → **Browser** opens a `浏览器` tab (`BrowserPage`, object name
  `browserPage`): toolbar with back / forward / reload buttons and an address
  bar (`browserAddress`), plus a `QWebEngineView`.
- Address normalisation (`normalize_address`):
  - empty → nothing;
  - `http`, `https`, `file` URLs load as-is;
  - text without spaces that contains a dot or is `localhost[:port]` → `https://…`
    (`http://` for localhost);
  - anything else (including `javascript:`/`data:`/other schemes) → Bing search.
- Isolation: its own off-the-record `QWebEngineProfile` (no disk cookies or
  cache), no WebChannel, separate from the offline Markdown/PPTX viewers whose
  network blocking stays unchanged. Disposal swaps in an inert page, then
  releases page and profile (same pattern as `MarkdownVisualView`).
- Tab title follows the page title (fallback `浏览器`); the address bar follows
  URL changes. `Ctrl+F` find works through the existing WebEngine path.
  Browser tabs are not written to recent files and never prompt on close.
- Initial page `about:blank` with the address bar focused.

## Non-goals

- Bookmarks, history UI, downloads, multiple profiles, dev tools.

## Acceptance

- Browser menu item enabled; triggering it adds one browser tab with focus in
  the address bar.
- `normalize_address` cases above hold.
- Entering a local `file://` URL loads it and updates the tab title.
- Closing the tab disposes the page without prompting.