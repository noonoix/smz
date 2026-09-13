using System;

namespace Ams.UI.Views;

/// <summary>Ensures the shared error-policy controls are created when OptionsDialog is
/// embedded in MainWindow. Embedded settings never raise OnContentRendered.</summary>
public partial class OptionsDialog
{
    protected override void OnInitialized(EventArgs e)
    {
        base.OnInitialized(e);
        if (_errorPolicyUiAdded) return;
        _errorPolicyUiAdded = true;
        AddErrorPolicyControls();
    }
}
