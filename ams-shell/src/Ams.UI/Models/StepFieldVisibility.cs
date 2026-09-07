namespace Ams.UI.Models;

/// <summary>v0.9.29 — pure visibility rule for step-dialog fields. HideWhenValue (v0.9.14)
/// hides a field while the dependency EQUALS the value; HideUnlessValue (new — for three-law
/// combos like forLoop.mode) hides it whenever the dependency is DIFFERENT, which is how the
/// count field can hide in BOTH time and infinite modes. Extracted for TestRunner (step 29).</summary>
public static class StepFieldVisibility
{
    public static bool FieldVisible(string? depValue, string? hideWhenValue, string? hideUnlessValue)
    {
        if (hideUnlessValue is not null)
            return string.Equals(depValue, hideUnlessValue, StringComparison.OrdinalIgnoreCase);
        if (hideWhenValue is not null)
            return !string.Equals(depValue, hideWhenValue, StringComparison.OrdinalIgnoreCase);
        return true;
    }
}
