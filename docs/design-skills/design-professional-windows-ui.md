# Design Professional Windows UI

**Purpose:** Professional UI/UX guidance for Classroom Studio, a .NET 8 `net8.0-windows` WPF desktop application.

**Canonical source:** Notion skill: https://app.notion.com/p/3df48d094f14802fb5d2ce4978a6a1d9
**Upstream reference:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill (release 2.13.0)

## Mandatory guidance

- Preserve the existing WPF/MVVM/navigation conventions.
- Define a semantic design system before adding screens: surfaces, text, accent, success, warning, error, spacing, typography, radii, elevation, icons, and motion.
- Keep theme values in resource dictionaries and use `DynamicResource` where runtime theme changes are possible; do not scatter literal colors through views.
- Design default, hover, pressed, focus-visible, disabled, selected, validation, loading, empty, offline, permission-denied, and destructive states.
- Support keyboard navigation, logical tab order, visible focus, resizing, DPI scaling, long Persian strings, high contrast, and reduced motion.
- Prefer native desktop behavior and restrained layouts over mobile-like pages, decorative gradients, or dense unstructured card walls.
- Verify representative layouts at 1280×720, 1920×1080, narrow resize, 125% and 150% scaling, keyboard-only use, and light/dark themes.

## Required design deliverable

For a new or edited screen, document: design direction, tokens, screen/interaction map, reusable components and states, WPF implementation files, and a validation checklist.
