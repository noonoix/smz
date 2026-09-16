# Classroom Studio Windows Companion MCP

A separate local Windows companion for software-only Classroom Studio inspection and export validation. It uses Windows UI Automation and a stdio JSON-RPC MCP transport so the WPF process stays isolated.

## Safe v0.1 boundary

The allow-list is limited to launch/attach, window listing, status/control/text inspection, screenshots, an explicit application-log reader, the software-side `Combined Guard` export into a staging directory, and bundle file/revision/SHA-256 validation.

There is no serial, USB, HID, firmware flashing, board reset, actuator, keyboard, mouse, Guard ON/OFF, Run/Stop, driver-install, or release-publish operation. `click_control` applies the same deny policy, and the export tool invokes only the specifically named Combined Guard export control.

## Running

```powershell
dotnet build tools/ClassroomStudio.Companion/ClassroomStudio.Companion.csproj -c Release
dotnet run --project tools/ClassroomStudio.Companion/ClassroomStudio.Companion.csproj -- "C:\Path\ClassroomStudio.exe"
```

The process reads MCP JSON-RPC messages from stdin and writes Content-Length framed responses to stdout. Audit records are written to `%LOCALAPPDATA%\\ClassroomStudio\\companion-audit.jsonl`.

## Export validation flow

1. Start Classroom Studio with `launch_classroom_studio` or attach to an existing process.
2. Use `read_status`, `find_control`, or `read_visible_text` to confirm the Phase 7 card, six profiles, and Combined Guard export control.
3. Call `export_combined_bundle_to_staging` with an empty staging directory.
4. Call `verify_bundle_manifest` and `verify_sha256_manifest`.

This validates software output only. It never connects to or copies files onto a Pico/Arduino and is not hardware acceptance or production release validation.
