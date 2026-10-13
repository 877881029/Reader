# Terminal Theme Tuning Design

Status: Approved
Progress ledger: `docs/STATUS.md`

## Background

Side-by-side with the Copilot app terminal, Reader's terminal text looks heavy
and too large. Colours sampled from the user's screenshot of the Copilot
terminal: background `#f6f2ee`, text `#3d2b5a`, cursor `#2848a9`; glyph
height ~17 px versus Reader's ~20 px.

## Scope

- Theme: background/cursorAccent `#f6f2ee`, foreground `#3d2b5a`, cursor
  `#2848a9`, selection `#ddd5ee`; ANSI palette unchanged (GitHub Light) except
  `black` follows the foreground (`#3d2b5a`) so default-coloured prompts match.
- Font: Cascadia Mono 12px, weight normal, line height 1.25.
- Page/viewport background and Qt page background follow `#f6f2ee`; padding
  10px top, 16px left.

## Acceptance

- Theme constants and CSS updated (web tests), Python page background and
  real WebEngine body colour `rgb(246, 242, 238)`; side-by-side screenshot.