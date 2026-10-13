# Terminal DECRQM Crash Fix Implementation Plan

Status: Approved

**Spec:** `docs/superpowers/specs/2026-10-13-terminal-decrqm-fix-design.md`

## Task 1
RED: WebEngine DECRQM reply + alternate-buffer test and static bundle guard
against the current bundle. GREEN: `vite.config.ts` `minify: false`, rebuild;
manual `ghcp` reproduction renders the CLI; release gate; install; docs.