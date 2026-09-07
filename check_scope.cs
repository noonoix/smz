// Quick sanity: FlatStepRow fields are NOT serialized to .amsj
// Scope fields are computed on-the-fly in Renumber() from StepNode tree structure
// So .amsj version 0.7 is correct — no schema change
Console.WriteLine("Scope fields are UI-only; .amsj schema unchanged.");
