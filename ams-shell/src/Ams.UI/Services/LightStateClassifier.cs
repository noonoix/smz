using Ams.UI.Models;

namespace Ams.UI.Services;

public enum LightStateClassificationKind
{
    Unknown,
    Invalid,
    Ambiguous,
    Candidate,
    Stable,
}

public sealed record LightStateClassification(
    LightStateClassificationKind Kind,
    double? Lux,
    LightStateProfile? Profile = null,
    double? Confidence = null,
    IReadOnlyList<LightStateProfile>? Matches = null)
{
    public static LightStateClassification Unknown(double? lux = null)
        => new(LightStateClassificationKind.Unknown, lux);
}

/// <summary>
/// Pure deterministic state machine for light profiles. Overlap is always explicit: profile order
/// never chooses a winner. StableDuration suppresses transients; Hysteresis only holds the already
/// stable state just outside its normal range.
/// </summary>
public sealed class LightStateClassifier
{
    private readonly IReadOnlyList<LightStateProfile> _profiles;
    private string? _candidateId;
    private DateTimeOffset? _candidateSince;
    private string? _stableId;

    public LightStateClassifier(IEnumerable<LightStateProfile> profiles)
        => _profiles = profiles?.ToArray() ?? throw new ArgumentNullException(nameof(profiles));

    public LightStateClassification Update(double? lux, DateTimeOffset at, bool sampleIsFresh = true)
    {
        if (!sampleIsFresh)
        {
            Reset();
            return LightStateClassification.Unknown(lux);
        }
        if (lux is not double value || !double.IsFinite(value) || value < 0)
        {
            Reset();
            return new LightStateClassification(LightStateClassificationKind.Invalid, lux);
        }

        var enabled = _profiles.Where(p => p.Enabled && p.IsValid).ToArray();
        var matches = enabled.Where(p => value >= p.LuxMin && value <= p.LuxMax).ToArray();
        if (matches.Length > 1)
        {
            Reset();
            return new LightStateClassification(
                LightStateClassificationKind.Ambiguous, value, Matches: matches);
        }

        if (matches.Length == 1)
        {
            var match = matches[0];
            if (_stableId == match.Id)
                return Stable(value, match);

            if (_candidateId != match.Id || _candidateSince is null || at < _candidateSince)
            {
                _candidateId = match.Id;
                _candidateSince = at;
                return Candidate(value, match);
            }

            if ((at - _candidateSince.Value).TotalMilliseconds < match.StableDurationMs)
                return Candidate(value, match);

            _stableId = match.Id;
            _candidateId = null;
            _candidateSince = null;
            return Stable(value, match);
        }

        var stable = enabled.FirstOrDefault(p => p.Id == _stableId);
        if (stable is not null
            && value >= Math.Max(0, stable.LuxMin - stable.HysteresisLux)
            && value <= stable.LuxMax + stable.HysteresisLux)
        {
            _candidateId = null;
            _candidateSince = null;
            return Stable(value, stable);
        }

        Reset();
        return LightStateClassification.Unknown(value);
    }

    public void Reset()
    {
        _candidateId = null;
        _candidateSince = null;
        _stableId = null;
    }

    private static LightStateClassification Candidate(double lux, LightStateProfile profile)
        => new(LightStateClassificationKind.Candidate, lux, profile, Confidence(lux, profile));

    private static LightStateClassification Stable(double lux, LightStateProfile profile)
        => new(LightStateClassificationKind.Stable, lux, profile, Confidence(lux, profile));

    private static double Confidence(double lux, LightStateProfile profile)
    {
        if (profile.LuxTolerance == 0) return lux == profile.LuxCenter ? 1 : 0;
        return Math.Clamp(1 - Math.Abs(lux - profile.LuxCenter) / profile.LuxTolerance, 0, 1);
    }
}
