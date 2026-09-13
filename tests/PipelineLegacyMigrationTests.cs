using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.CompilerServices;
using Ams.UI.Models;
using Ams.UI.Services;

namespace Ams.Tests;

internal static class PipelineLegacyMigrationTests
{
    [ModuleInitializer]
    internal static void Run()
    {
        var path = Path.Combine(Path.GetTempPath(), "ams-legacy-pipeline-" + Guid.NewGuid().ToString("N") + ".amsj");
        try
        {
            var loop = new StepNode
            {
                Type = "forLoop",
                Props = new Dictionary<string, object?>
                {
                    ["mode"] = "count",
                    ["count"] = 1,
                },
            };
            loop.Children.Add(Key("keyDown", "A"));
            loop.Children.Add(Key("keyUp", "A"));
            loop.Children.Add(Key("keystroke", "B"));
            var next = new StepNode
            {
                Type = "comment",
                Props = new Dictionary<string, object?> { ["text"] = "Next" },
            };
            DocumentService.Save(path, new[] { loop, next });
            var legacyJson = File.ReadAllText(path);

            var rejectedAsPipeline = false;
            try { PipelineWorkspaceSerializer.Deserialize(legacyJson); }
            catch (InvalidDataException) { rejectedAsPipeline = true; }
            Require(rejectedAsPipeline,
                "legacy { app, version, steps } document was accepted as an empty native pipeline");

            var migrated = PipelineWorkspace.FromLegacy(DocumentService.Load(path), PipelineKind.Main);
            Require(migrated[PipelineKind.Main].Steps.Count == 2
                    && CountAll(migrated[PipelineKind.Main].Steps) == 5,
                "legacy roots were not migrated losslessly into the requested tab");
            Require(migrated[PipelineKind.Launch].Steps.Count == 0
                    && migrated[PipelineKind.LaunchRecovery].Steps.Count == 0
                    && migrated[PipelineKind.MainRecovery].Steps.Count == 0
                    && migrated[PipelineKind.ResumeEssentials].Steps.Count == 0,
                "legacy migration populated unrelated pipeline tabs");

            var nativeJson = PipelineWorkspaceSerializer.Serialize(migrated);
            var roundTrip = PipelineWorkspaceSerializer.Deserialize(nativeJson);
            Require(roundTrip[PipelineKind.Main].Steps.Count == 2
                    && CountAll(roundTrip[PipelineKind.Main].Steps) == 5,
                "native pipeline round-trip lost migrated steps");
        }
        finally
        {
            if (File.Exists(path)) File.Delete(path);
        }
    }

    private static StepNode Key(string type, string key)
        => new()
        {
            Type = type,
            Props = new Dictionary<string, object?>
            {
                ["key"] = key,
                ["keyboardBoard"] = "default",
            },
        };

    private static int CountAll(IEnumerable<StepNode> roots)
    {
        var count = 0;
        foreach (var root in roots)
        {
            count++;
            count += CountAll(root.Children);
        }
        return count;
    }

    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException("Pipeline legacy migration regression: " + message);
    }
}
