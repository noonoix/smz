namespace Ams.UI.Services;

/// <summary>Sidecar/board connection lifecycle.</summary>
public enum BridgeState { Disconnected, Connecting, Connected }

/// <summary>
/// Transport to the AMS board. F6 starts with option B (bridge to the existing
/// Python runner) and migrates to option A (native C# port of ams_serial/ams_crypto)
/// before v1.0 — design doc §13.10. The C# port must reproduce the four rules
/// of §15.4 (ascending counter · persistent RX buffer · resync after loss ·
/// command-proportional timeouts).
/// </summary>
public interface IBoardBridge : IAsyncDisposable
{
    /// <summary>Raised for every protocol line/log from the sidecar (feeds the serial log panel).</summary>
    event EventHandler<string>? LineReceived;

    /// <summary>Raised when the connection lifecycle state changes.</summary>
    event EventHandler<BridgeState>? StateChanged;

    BridgeState State { get; }

    /// <summary>Firmware version reported by HELLO, e.g. "1.6".</summary>
    string? FirmwareVersion { get; }

    /// <summary>COM port the board answered on, e.g. "COM8" (AUTO is recommended, §14.3/§15.5).</summary>
    string? Port { get; }

    /// <summary>Opens the port and performs the encrypted HELLO handshake (§11).</summary>
    Task ConnectAsync(string portName, CancellationToken ct = default);

    /// <summary>
    /// Sends one command over the encrypted channel and returns the board reply.
    /// <paramref name="timeoutSeconds"/> must be proportional to the command's window
    /// for long-window commands (WSND/TRGSND/SCAL — §15.4 rule 4); null = bridge default (5s).
    /// </summary>
    Task<string> SendAsync(string command, double? timeoutSeconds = null, CancellationToken ct = default);

    /// <summary>
    /// Instant abort (v0.6.2): out-of-band HALT write that does NOT wait for the
    /// in-flight command's reply and does not take the command lock — used by Stop
    /// so a long listen (WSND/TRGSND) breaks immediately instead of after its window.
    /// </summary>
    Task SendAbortAsync();

    /// <summary>
    /// Streams a whole dense mouse path in ONE bridge operation (bridge.py v0.9.2 "send_path"):
    /// the sidecar writes each micro-step's MMOVE without waiting for per-point replies
    /// (a PING every 12 points drains the board's OKs), so the cursor glides at true hand
    /// cadence (recording-matched: median ~5 ms / ~3 px) instead of stepping.
    /// Throws InvalidOperationException("… unknown op") on an older bridge.py — callers then
    /// fall back to firmware-smoothstepped control points.
    /// </summary>
    Task<string> SendPathAsync(IReadOnlyList<(int X, int Y, int DelayMs)> points, CancellationToken ct = default);

    /// <summary>v0.9.43 — lists the real serial ports for the manual-connect picker
    /// ("COMx — description" labels). Starts the sidecar if needed; no board required.
    /// Default: empty list (fakes/tests).</summary>
    Task<IReadOnlyList<string>> ListPortsAsync(CancellationToken ct = default)
        => Task.FromResult<IReadOnlyList<string>>(Array.Empty<string>());

    /// <summary>Clean shutdown: HALT, then BYE, then close (§11.3).</summary>
    Task DisconnectAsync(CancellationToken ct = default);
}
