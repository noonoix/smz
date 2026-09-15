namespace Ams.UI.Models;

/// <summary>The caller supplies why the shared Login/DC screen was reached; Lux cannot distinguish it.</summary>
public enum RecoveryEntryReason
{
    Login,
    Disconnect,
}

/// <summary>
/// Contract for entering the shared login recovery flow. A disconnect closes its popup with one
/// leading ESC; normal login starts the same shared flow directly. Detection remains side-effect free.
/// </summary>
public static class RecoveryEntryPolicy
{
    public const string DismissDisconnectPopupKey = "ESC";

    public static IReadOnlyList<string> PreludeKeys(RecoveryEntryReason reason) => reason switch
    {
        RecoveryEntryReason.Login => Array.Empty<string>(),
        RecoveryEntryReason.Disconnect => new[] { DismissDisconnectPopupKey },
        _ => throw new ArgumentOutOfRangeException(nameof(reason)),
    };
}
