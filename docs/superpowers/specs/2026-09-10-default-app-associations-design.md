# Default App Associations

Date: 2026-09-10  
Status: Implemented (HKCU Classes + Capabilities + OpenWithList; PDF UserChoice still UCPD-locked)  
Progress ledger: `docs/STATUS.md`

## 1. Goal

Double-clicking Reader-supported documents opens **Reader**, not Word / PowerPoint / Excel / Acrobat, for the current Windows user.

Do **not** change `hit_test_local`, `begin_window_move`, or `nativeEvent`.

## 2. Decisions

| Topic | Choice |
|---|---|
| Scope | All current Reader suffixes: `.docx` `.pptx` `.xlsx` `.md` `.pdf` `.json` `.yaml` `.yml` `.xml` |
| Hive | HKCU only (no HKLM, no admin) |
| ProgID | Keep `Reader.Document`; also set `HKCU\Software\Classes\<ext>` default to that ProgID |
| UserChoice | Best-effort **delete** existing `FileExts\<ext>\UserChoice` and `UserChoiceLatest` so Word’s `.md` override and similar keys stop winning. Do not forge hashes. |
| Default Apps | Register `Software\RegisteredApplications` + `Software\Reader\Capabilities\FileAssociations` so Reader appears in Settings |
| Notify | `SHChangeNotify(SHCNE_ASSOCCHANGED)` after real registry writes |
| Settings UI | Do not pop Settings on every launch |

Windows 11 may still protect some types (especially `.pdf`) via UCPD. Those stay best-effort; HKCU Classes + Capabilities still apply.

This supersedes the v1 “Open with only / never claim defaults” rule.

## 3. Testing

- Fake registry: each suffix’s Classes default is `Reader.Document`; Capabilities lists every suffix; UserChoice keys are deleted; OpenWithProgids still written; no Settings process launched
- README no longer lists “抢当系统默认打开方式” as out of scope
