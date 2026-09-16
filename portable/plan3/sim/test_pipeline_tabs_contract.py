#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[3]
model = (root / "ams-shell/src/Ams.UI/Models/PipelineWorkspace.cs").read_text(encoding="utf-8")
viewmodel = (root / "ams-shell/src/Ams.UI/ViewModels/MainViewModel.PipelineTabs.cs").read_text(encoding="utf-8")
serializer = (root / "ams-shell/src/Ams.UI/Services/PipelineWorkspaceSerializer.cs").read_text(encoding="utf-8")
spec = (root / "docs/light-guard-phase7-tab-migration.md").read_text(encoding="utf-8")
matrix = (root / "docs/light-guard-phase7-transition-matrix.md").read_text(encoding="utf-8")

# The visible order is the Guard optical profile order, followed by Resumable.
for kind in (
    "Desktop",
    "LoginOrDc",
    "CharacterDashboard",
    "EnteringGameLoading",
    "Game",
    "Targeted",
    "Resumable",
):
    assert f"Kind = PipelineKind.{kind}" in model

for filename in (
    "desktop_steps.txt",
    "login_or_dc_steps.txt",
    "character_dashboard_steps.txt",
    "entering_game_loading_steps.txt",
    "game_steps.txt",
    "targeted_steps.txt",
    "resumable_steps.txt",
):
    assert filename in model

# Old names remain source-compatible, but are not visible tabs or migration targets.
for alias in ("Launch = Desktop", "LaunchRecovery = LoginOrDc", "MainRecovery = Targeted", "Main = Game", "ResumeEssentials = Resumable"):
    assert alias in model
assert "LegacyPipelines" in model and "legacyPipelines" in serializer
assert "pipelineVersion" in serializer and "FixParents" in serializer
assert "currentNames" in serializer and "FormatVersion" in serializer

# Switching tabs keeps the existing editor state isolated and clears undo selection state.
assert "SelectedNodes = new()" in viewmodel
assert "_undo.Clear()" in viewmodel and "_redo.Clear()" in viewmodel
assert "CopyTree(_activePipelineTab.Steps, Steps)" in viewmodel

# Migration is preservation-only until an explicit transition mapping is approved.
for title in (
    "`Desktop`",
    "`Login / DC`",
    "`Character Dashboard`",
    "`Entering Game / Loading`",
    "`Game`",
    "`Targeted`",
    "`Resumable`",
):
    assert title in spec
assert "legacyPipelines" in spec
assert "no old Step is silently deleted or reassigned" in spec
assert "do not by themselves authorize automatic execution" in spec

# The approved matrix keeps stages 1–5 ordered, treats Targeted as a side-state,
# and sends DC from the active game context back to stage 2.
for phrase in (
    "strictly ordered",
    "fall back to stage 2",
    "independent `DC` Classroom Studio context",
    "It is not stage 6",
    "DC has priority",
    "one-shot execution",
):
    assert phrase in matrix
for stage in (
    "`desktop` / `Desktop`",
    "`login-or-dc` / `Login / DC`",
    "`character-dashboard` / `Character Dashboard`",
    "`entering-game-loading` / `Entering Game / Loading`",
    "`game` / `Game`",
):
    assert stage in matrix

print("pipeline tabs migration contract: seven tabs, ordered stages, DC fallback, and Targeted side-state verified")
