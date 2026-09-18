# Classroom Studio Development Rules

## Design skills are mandatory

When creating, developing, reviewing, or editing any Classroom Studio UI, WPF screen, status window, calibration editor, settings surface, navigation shell, control, theme, or layout, apply both documented skills:

1. [`design-professional-windows-ui`](design-skills/design-professional-windows-ui.md)
2. [`design-modern-wpf-apps`](design-skills/design-modern-wpf-apps.md)

These rules are mandatory for UI changes, not optional suggestions. Preserve complete existing functionality while improving presentation.

## Source and sandbox fallback

The GitHub copies in `docs/design-skills/` are the project-local canonical snapshots. If either skill is unavailable in the active sandbox/session, the agent **must retrieve and read the corresponding file from this repository before designing or editing Classroom Studio**. The agent must not silently substitute a generic UI approach.

If the repository snapshot is missing or stale, consult the canonical Notion URLs recorded in the skill files, then update the GitHub snapshot before continuing. Do not claim the skill was applied unless it was available locally or successfully retrieved from GitHub/Notion.

## UI preservation gate

Before merging any UI change, verify that existing calibration, profile editing, default-setting, live-watch, Guard sync, diagnostic authorization, cycle status, and macro/workspace functionality still exists. A redesign that removes an existing control or changes its safety semantics fails this gate.

## Validation gate

Build the actual .NET 8 WPF project and check light/dark/high-contrast behavior, 1280×720 and 1920×1080 layouts, narrow resize, 125%/150% DPI, keyboard focus/tab order, Persian localization, empty/offline/error states, and non-executing/fail-closed behavior where applicable.
