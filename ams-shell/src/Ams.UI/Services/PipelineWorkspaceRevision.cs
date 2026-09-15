using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Ams.UI.Models;

namespace Ams.UI.Services;

/// <summary>
/// Canonical SHA-256 identity for all five pipeline tabs. UI-only fields and dictionary insertion
/// order are ignored; tab, step and child order remain significant.
/// </summary>
public static class PipelineWorkspaceRevision
{
    public static string Compute(PipelineWorkspace workspace)
    {
        ArgumentNullException.ThrowIfNull(workspace);
        using var stream = new MemoryStream();
        using (var writer = new Utf8JsonWriter(stream))
        {
            writer.WriteStartObject();
            writer.WriteNumber("format", PipelineWorkspace.FormatVersion);
            writer.WritePropertyName("tabs");
            writer.WriteStartArray();
            foreach (var tab in workspace.Tabs.OrderBy(x => x.Kind))
            {
                writer.WriteStartObject();
                writer.WriteString("kind", tab.Kind.ToString());
                writer.WritePropertyName("steps");
                writer.WriteStartArray();
                foreach (var node in tab.Steps) WriteNode(writer, node);
                writer.WriteEndArray();
                writer.WriteEndObject();
            }
            writer.WriteEndArray();
            writer.WriteEndObject();
        }
        return Convert.ToHexString(SHA256.HashData(stream.ToArray()));
    }

    private static void WriteNode(Utf8JsonWriter writer, StepNode node)
    {
        ArgumentNullException.ThrowIfNull(node);
        writer.WriteStartObject();
        writer.WriteString("type", node.Type ?? string.Empty);
        writer.WriteString("name", node.Name ?? string.Empty);
        writer.WriteNumber("delay", node.Delay);
        writer.WriteNumber("delayMax", node.DelayMax);
        writer.WriteBoolean("disabled", node.IsDisabled);
        writer.WritePropertyName("props");
        writer.WriteStartObject();
        foreach (var pair in node.Props.OrderBy(x => x.Key, StringComparer.Ordinal))
        {
            writer.WritePropertyName(pair.Key);
            WriteValue(writer, pair.Value);
        }
        writer.WriteEndObject();
        writer.WritePropertyName("children");
        writer.WriteStartArray();
        foreach (var child in node.Children) WriteNode(writer, child);
        writer.WriteEndArray();
        writer.WriteEndObject();
    }

    private static void WriteValue(Utf8JsonWriter writer, object? value)
    {
        if (value is null) { writer.WriteNullValue(); return; }
        var element = value is JsonElement json ? json : JsonSerializer.SerializeToElement(value);
        WriteElement(writer, element);
    }

    private static void WriteElement(Utf8JsonWriter writer, JsonElement element)
    {
        switch (element.ValueKind)
        {
            case JsonValueKind.Object:
                writer.WriteStartObject();
                foreach (var property in element.EnumerateObject().OrderBy(x => x.Name, StringComparer.Ordinal))
                {
                    writer.WritePropertyName(property.Name);
                    WriteElement(writer, property.Value);
                }
                writer.WriteEndObject();
                break;
            case JsonValueKind.Array:
                writer.WriteStartArray();
                foreach (var item in element.EnumerateArray()) WriteElement(writer, item);
                writer.WriteEndArray();
                break;
            case JsonValueKind.String:
                writer.WriteStringValue(element.GetString());
                break;
            case JsonValueKind.Number:
                writer.WriteRawValue(element.GetRawText(), skipInputValidation: false);
                break;
            case JsonValueKind.True:
                writer.WriteBooleanValue(true);
                break;
            case JsonValueKind.False:
                writer.WriteBooleanValue(false);
                break;
            case JsonValueKind.Null:
            case JsonValueKind.Undefined:
                writer.WriteNullValue();
                break;
            default:
                throw new InvalidOperationException("Unsupported pipeline property JSON kind.");
        }
    }
}
