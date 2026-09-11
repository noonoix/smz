// v0.9.67 — shared primitives for code-built Play Options controls.
global using System.IO;
global using System.Windows.Controls.Primitives;

// The WPF project intentionally enables WinForms for screen/cursor services. Explicit
// aliases keep code-built WPF controls deterministic instead of relying on ambiguous
// simple names imported by the generated global usings.
global using Binding = System.Windows.Data.Binding;
global using Button = System.Windows.Controls.Button;
global using CheckBox = System.Windows.Controls.CheckBox;
global using FlowDirection = System.Windows.FlowDirection;
global using FontFamily = System.Windows.Media.FontFamily;
global using HorizontalAlignment = System.Windows.HorizontalAlignment;
global using MessageBox = System.Windows.MessageBox;
global using Orientation = System.Windows.Controls.Orientation;
global using TextBox = System.Windows.Controls.TextBox;
