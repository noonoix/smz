using Ams.UI.Models;

namespace Ams.UI.ViewModels;

/// <summary>
/// Drag/drop moves for conditional heads. An If head, its Else marker, and its End If marker
/// are one unit; the existing editor must not reject the head before it can be moved.
/// </summary>
public partial class MainViewModel
{
    public bool IsConditionalDragNode(StepNode node) => IsIfElseHead(node);

    public void MoveConditionalDragNode(StepNode node, StepNode? target, string mode)
    {
        if (!IsIfElseHead(node)) return;
        if (target is not null)
        {
            if (ReferenceEquals(node, target)) return;
            for (var p = target; p is not null; p = p.Parent)
                if (ReferenceEquals(p, node)) return;
        }

        var sourceList = node.Parent?.Children ?? Steps;
        int sourceIndex = sourceList.IndexOf(node);
        if (sourceIndex < 0) return;

        var (elseIndex, endIfIndex) = LocateElseMarkersForUi(sourceList, sourceIndex);
        var moveSet = new List<StepNode> { node };
        if (elseIndex >= 0 && elseIndex < sourceList.Count) moveSet.Add(sourceList[elseIndex]);
        if (endIfIndex >= 0 && endIfIndex < sourceList.Count) moveSet.Add(sourceList[endIfIndex]);
        if (target is not null && moveSet.Contains(target)) return;

        StepNode? appendParent = null;
        StepNode? prependParent = null;

        if (target is not null)
        {
            if (IsNextMarker(target) || IsEndIfMarker(target))
            {
                if (mode != "after")
                {
                    var owner = FindClosingMarkerOwner(target, out var elseBranch);
                    if (owner is not null)
                    {
                        if (elseBranch is not null && moveSet.Contains(elseBranch)) return;
                        for (var p = owner; p is not null; p = p.Parent)
                            if (moveSet.Contains(p)) return;
                        appendParent = elseBranch ?? owner;
                    }
                }
            }
            else if (IsElseMarker(target))
            {
                var owner = FindElseMarkerOwner(target);
                if (owner is not null)
                {
                    for (var p = owner; p is not null; p = p.Parent)
                        if (moveSet.Contains(p)) return;
                    if (mode == "before") appendParent = owner;
                    else if (mode == "after") prependParent = target;
                    else appendParent = target;
                }
            }
            else if ((mode == "into" || mode == "after") && StepDefinitions.AcceptsChildren(target))
            {
                for (var p = target; p is not null; p = p.Parent)
                    if (moveSet.Contains(p)) return;
                // Dropping on the body of a container must append to its existing children;
                // this is the 1.1.3 case rather than inserting at 1.1.1.
                appendParent = target;
            }
        }

        Snapshot();
        foreach (var moved in moveSet)
        {
            if (!(moved.Parent?.Children ?? Steps).Remove(moved)) return;
            moved.Parent = null;
        }

        if (appendParent is not null)
        {
            foreach (var moved in moveSet)
            {
                moved.Parent = appendParent;
                appendParent.Children.Add(moved);
            }
        }
        else if (prependParent is not null)
        {
            for (int i = moveSet.Count - 1; i >= 0; i--)
            {
                moveSet[i].Parent = prependParent;
                prependParent.Children.Insert(0, moveSet[i]);
            }
        }
        else if (target is null)
        {
            foreach (var moved in moveSet) Steps.Add(moved);
        }
        else
        {
            var list = target.Parent?.Children ?? Steps;
            int index = list.IndexOf(target);
            if (index < 0)
            {
                foreach (var moved in moveSet) Steps.Add(moved);
            }
            else
            {
                int at = mode == "before" ? index : index + 1;
                foreach (var moved in moveSet)
                {
                    moved.Parent = target.Parent;
                    list.Insert(at++, moved);
                }
            }
        }

        Renumber();
        MarkDirty();
        Log("moved conditional block: " + node.Summary);
    }
}
