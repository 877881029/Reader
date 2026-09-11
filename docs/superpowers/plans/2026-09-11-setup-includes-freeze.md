# Setup Includes Freeze Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One `setup.ps1` run installs the venv and freezes `dist\Reader\Reader.exe` by calling `build_windows.ps1`.

**Architecture:** Keep freeze logic in `build_windows.ps1`. `setup.ps1` invokes it after pip, then launches the frozen exe (or `-m reader` if `-SkipBuild`).

**Tech Stack:** PowerShell, existing PyInstaller script.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- Do not inline npm/PyInstaller into `setup.ps1`.
- Do not commit `dist/`.
- User asked to implement without extra approval gates.

---

### Task 1: Wire setup to freeze

- [x] Failing packaging test: setup calls `build_windows.ps1`, has `-SkipBuild`, no inlined PyInstaller
- [x] `setup.ps1` invoke + launch; README / 功能全解 / release notes
- [x] Full pytest (no extra freeze unless product binary changed); STATUS; push `origin/main`
