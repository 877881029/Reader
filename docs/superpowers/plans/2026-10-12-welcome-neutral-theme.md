# Welcome Page Neutral Theme Implementation Plan

Status: Approved

**Spec:** `docs/superpowers/specs/2026-10-12-welcome-neutral-theme-design.md`

## Task 1: Neutral welcome palette

**RED** window tests: welcome stylesheet free of cobalt values; open button
background `#1f1d1a`; badge background `#f0ebe3`; `WelcomePage` exposes no
watermark (paint does not draw text). Update the old assertion that required
`background:#2563eb`.
**GREEN** palette constants in `welcome.py`, stylesheet built from them,
watermark removed, rule colour neutral. Screenshot check, then
`verify.ps1 -Release`, README/功能全解 note, STATUS, commit, push.