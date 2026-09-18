# Design Modern WPF Apps

**Purpose:** Fluent 2 and modern WPF implementation guidance for Classroom Studio on .NET 8 `net8.0-windows`.

**Canonical source:** Notion skill: https://app.notion.com/p/3df48d094f1480e19a92f53c18191751
**Reference:** https://github.com/iNKORE-NET/UI.WPF.Modern

## Mandatory guidance

- Use maintainable XAML, reusable styles, theme-aware resources, and existing project conventions.
- Centralize semantic resources such as `App.Brush.Surface`, `App.Brush.Card`, `App.Brush.Accent`, `App.Brush.TextPrimary`, and `App.Brush.TextSecondary`.
- Keep light, dark, and high-contrast values in dictionaries; apply app overrides after library dictionaries.
- Prefer Fluent-aligned/native controls and clear navigation hierarchy. Use icons with accessible names/tooltips; do not use emoji as functional icons.
- Use modern window/backdrop features only when supported and always provide a solid-background fallback.
- Validate focus, hover, pressed, disabled, selected, validation, loading, empty, error, keyboard navigation, text scaling, contrast, and resize behavior.
- Avoid mixing UI frameworks or inventing package APIs; verify names against the installed version before implementation.

## Classroom Studio application

The status/settings experience must remain a separate, resizable window with the complete calibration editor, live-watch controls, Guard diagnostics, sync actions, and safe diagnostic controls. New cycle/orchestrator UI must not remove or hide those existing controls.
