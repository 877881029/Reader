# Default App Associations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Reader the current-user default app for every suffix it already opens.

**Architecture:** Extend `register_open_with` to set HKCU Classes defaults, register Default Apps capabilities, and delete stale UserChoice keys. Launch-time shell integration already calls this.

**Tech Stack:** Python `winreg`, `SHChangeNotify`, pytest.

## Global Constraints

- Do not change `hit_test_local`, `begin_window_move`, or `nativeEvent`.
- HKCU only. Do not forge UserChoice hashes. Do not open Settings on every launch.

---

### Task 1: Registry claim + tests

- [x] Failing tests for Classes default, Capabilities, UserChoice delete
- [x] Implement in `associate.py`; update README
- [x] Apply to this machine’s `dist\Reader\Reader.exe`

### Task 2: Freeze

- [x] Full pytest; freeze; smoke; desktop shortcut; STATUS
