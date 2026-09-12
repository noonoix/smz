using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>Document contract for one ordered Launch Steps group shared by initial start and Auto Resume.</summary>
public static class LaunchStepsContract
{
    public const string MarkerProperty = "launchSteps";

    public static void Mark(IList<StepNode> roots, StepNode group)
    {
        if (group.Type != "forLoop")
            throw new InvalidOperationException("Launch Steps باید یک For Loop باشد تا استپ‌ها به‌ترتیب اجرا شوند.");

        foreach (var node in Walk(roots))
            if (node.Type == "forLoop") node.Props[MarkerProperty] = ReferenceEquals(node, group);
        group.Props[MarkerProperty] = true;
    }

    public static StepNode? Find(IList<StepNode> roots)
        => Walk(roots).FirstOrDefault(n => n.Type == "forLoop" && PropEx.GetBool(n.Props, MarkerProperty));

    public static IReadOnlyList<string> Validate(IList<StepNode> roots)
    {
        var errors = new List<string>();
        var groups = Walk(roots)
            .Where(n => n.Type == "forLoop" && PropEx.GetBool(n.Props, MarkerProperty))
            .ToList();
        if (groups.Count > 1)
            errors.Add("فقط یک گروه می‌تواند Launch Steps باشد.");
        foreach (var group in groups)
            if (!group.Children.Any(c => !c.IsDisabled))
                errors.Add("Launch Steps حداقل به یک استپ فعال نیاز دارد.");
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
