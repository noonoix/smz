# Phase One Validation Trigger

This change validates the synchronized normal, standalone and AutoCycle firmware sources after the generated telemetry commit.

Required checks:

- telemetry behavior contract
- AutoCycle byte parity
- portable runtime contracts
- Windows application build and TestRunner
- sensitive artifact guard
