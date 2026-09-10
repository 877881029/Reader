# Default App Associations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Reader the current-user default app for every suffix it already opens.

**Architecture:** Extend `register_open_with` to set HKCU Classes defaults, register Default Apps capabilities, and delete stale UserChoice keys. Launch-time shell integration already calls this. UCPD-locked `.pdf` is claimed through the official Settings page for Reader (`SystemSettings.exe` is allowed to write UserChoice).

**Tech Stack:** Python `winreg`, `SHChangeNotify`, UI Automation via Windows PowerShell STA, pytest.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- HKCU only. Do not forge UserChoice hashes. Do not open Settings when `.pdf` already defaults to Reader. Do not disable UCPD.

---

### Task 1: Registry claim + tests

- [x] Failing tests for Classes default, Capabilities, UserChoice delete
- [x] Implement in `associate.py`; update README
- [x] Apply to this machine’s `dist\Reader\Reader.exe`

### Task 2: Freeze

- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS

### Task 3: Claim UCPD-locked PDF via Settings

**Files:**
- Create: `src/reader/shell/settings_claim.py`
- Modify: `src/reader/shell/associate.py`
- Test: `tests/test_settings_claim.py`, `tests/test_associate.py`

**Interfaces:**
- Consumes: `register_open_with` after real HKCU writes
- Produces: `claim_protected_defaults(...)`; `friendly_app_name(ext: str) -> str`

- [x] Failing tests: skip Settings when PDF is already Reader; open Reader defaults URI and invoke `.pdf` otherwise; close Settings on failure; injected claimer runs from `register_open_with`
- [x] Implement `claim_protected_defaults` + Settings UI adapters; call after real `register_open_with`
- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS
