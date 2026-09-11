using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>v0.9.67 document contract for the one Resume Essentials random package.</summary>
public static class ResumeEssentialsContract
{
    public const string MarkerProperty = "resumeEssentials";

    public static void Mark(IList<StepNode> roots, StepNode package)
    {
        if (package.Type != "randomPackage")
            throw new InvalidOperationException("Resume Essentials باید یک Random Package باشد.");

        foreach (var node in Walk(roots))
            if (node.Type == "randomPackage") node.Props[MarkerProperty] = ReferenceEquals(node, package);

        // Essentials must run every enabled item exactly once in a fresh order.
        package.Props[MarkerProperty] = true;
        package.Props["mode"] = "shuffleAll";
        package.Props["minCount"] = package.Children.Count;
        package.Props["maxCount"] = package.Children.Count;
    }

    public static StepNode? Find(IList<StepNode> roots)
        => Walk(roots).FirstOrDefault(n => n.Type == "randomPackage" && PropEx.GetBool(n.Props, MarkerProperty));

    public static IReadOnlyList<string> Validate(IList<StepNode> roots)
    {
        var errors = new List<string>();
        var packages = Walk(roots)
            .Where(n => n.Type == "randomPackage" && PropEx.GetBool(n.Props, MarkerProperty))
            .ToList();
        if (packages.Count > 1)
            errors.Add("فقط یک بسته می‌تواند Resume Essentials باشد.");
        foreach (var package in packages)
        {
            if (PropEx.GetString(package.Props, "mode", "shuffleAll") != "shuffleAll")
                errors.Add("Resume Essentials فقط با حالت Shuffle All مجاز است.");
            if (!package.Children.Any(c => !c.IsDisabled))
                errors.Add("Resume Essentials حداقل به یک مورد فعال نیاز دارد.");
        }
        return errors;
    }

    private static IEnumerable<StepNode> Walk(IEnumerable<StepNode> nodes)
    {
        foreach (var node in nodes)
        {
            yield return node;
            foreach (var child in Walk(node.Children)) yield return child;
        }
    }
}
