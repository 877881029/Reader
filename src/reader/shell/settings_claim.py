from __future__ import annotations

import base64
import os
import subprocess
from collections.abc import Callable, Sequence
from ctypes import wintypes

SETTINGS_URI = "ms-settings:defaultapps?registeredAppUser=Reader"
PROTECTED_EXTENSIONS = (".pdf",)
_CREATE_NO_WINDOW = 0x08000000
_ASSOCF_NOTRUNCATE = 0x00000020
_ASSOCSTR_FRIENDLYAPPNAME = 4


def friendly_app_name(ext: str) -> str:
    if os.name != "nt":
        return ""
    import ctypes

    buf = ctypes.create_unicode_buffer(1024)
    size = wintypes.DWORD(1024)
    hr = ctypes.windll.shlwapi.AssocQueryStringW(
        _ASSOCF_NOTRUNCATE,
        _ASSOCSTR_FRIENDLYAPPNAME,
        ext,
        None,
        buf,
        ctypes.byref(size),
    )
    if hr != 0:
        return ""
    return buf.value


def _is_reader(name: str) -> bool:
    return name.strip().casefold() == "reader"


def claim_protected_defaults(
    *,
    extensions: Sequence[str] = PROTECTED_EXTENSIONS,
    query_app: Callable[[str], str] | None = None,
    open_settings: Callable[[str], None] | None = None,
    invoke_file_types: Callable[[list[str]], None] | None = None,
    close_settings: Callable[[], None] | None = None,
    sleep: Callable[[float], None] | None = None,
    timeout_s: float = 12,
    poll_s: float = 0.4,
    monotonic: Callable[[], float] | None = None,
) -> None:
    import time

    query = query_app or friendly_app_name
    needed = [ext for ext in extensions if not _is_reader(query(ext))]
    if not needed:
        return

    opener = open_settings or _open_settings
    invoker = invoke_file_types or _invoke_file_types
    closer = close_settings or _close_settings
    sleeper = sleep or time.sleep
    clock = monotonic or time.monotonic

    opener(SETTINGS_URI)
    try:
        deadline = clock() + timeout_s
        invoker(list(needed))
        while True:
            needed = [ext for ext in extensions if not _is_reader(query(ext))]
            if not needed:
                return
            if clock() >= deadline:
                return
            sleeper(poll_s)
    finally:
        closer()


def _open_settings(uri: str) -> None:
    if os.name != "nt":
        return
    os.startfile(uri)


def _invoke_file_types(exts: list[str]) -> None:
    joined = ",".join(exts)
    script = rf"""
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
function Get-SettingsWindow {{
  $root = [System.Windows.Automation.AutomationElement]::RootElement
  foreach ($name in @('Settings', '设置')) {{
    $cond = New-Object System.Windows.Automation.PropertyCondition(
      [System.Windows.Automation.AutomationElement]::NameProperty, $name)
    $el = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
    if ($null -ne $el) {{ return $el }}
  }}
  return $null
}}
$deadline = (Get-Date).AddSeconds(10)
$settings = $null
while ((Get-Date) -lt $deadline -and $null -eq $settings) {{
  Start-Sleep -Milliseconds 300
  $settings = Get-SettingsWindow
}}
if ($null -eq $settings) {{ exit 2 }}
$buttonType = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
  [System.Windows.Automation.ControlType]::Button)
$exts = '{joined}'.Split(',', [System.StringSplitOptions]::RemoveEmptyEntries)
foreach ($ext in $exts) {{
  $settings = Get-SettingsWindow
  if ($null -eq $settings) {{ continue }}
  $buttons = $settings.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonType)
  foreach ($b in $buttons) {{
    $n = $b.Current.Name
    if ([string]::IsNullOrEmpty($n)) {{ continue }}
    if (-not $n.StartsWith($ext)) {{ continue }}
    if ($n -match '(?i)Reader') {{ continue }}
    try {{
      $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
    }} catch {{}}
    break
  }}
}}
Start-Sleep -Milliseconds 600
$settings = Get-SettingsWindow
if ($null -ne $settings) {{
  $buttons = $settings.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonType)
  foreach ($b in $buttons) {{
    $n = $b.Current.Name
    if ($n -eq 'Set default' -or $n -eq '设为默认' -or $n -eq '设为默认值') {{
      try {{
        $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
      }} catch {{}}
    }}
  }}
}}
"""
    _run_sta_powershell(script)


def _close_settings() -> None:
    script = r"""
$ErrorActionPreference = 'SilentlyContinue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$root = [System.Windows.Automation.AutomationElement]::RootElement
$settings = $null
foreach ($name in @('Settings', '设置')) {
  $cond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty, $name)
  $settings = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
  if ($null -ne $settings) { break }
}
if ($null -eq $settings) { exit 0 }
$buttonType = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
  [System.Windows.Automation.ControlType]::Button)
$buttons = $settings.FindAll([System.Windows.Automation.TreeScope]::Descendants, $buttonType)
foreach ($want in @('Close Settings', '关闭设置', 'Close', '关闭')) {
  foreach ($b in $buttons) {
    if ($b.Current.Name -eq $want) {
      try {
        $b.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        exit 0
      } catch {}
    }
  }
}
"""
    _run_sta_powershell(script)


def _run_sta_powershell(script: str) -> None:
    if os.name != "nt":
        return
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    flags = _CREATE_NO_WINDOW if os.name == "nt" else 0
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-STA",
            "-WindowStyle",
            "Hidden",
            "-EncodedCommand",
            encoded,
        ],
        timeout=25,
        check=False,
        creationflags=flags,
    )
