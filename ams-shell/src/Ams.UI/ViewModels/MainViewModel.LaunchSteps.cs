using Ams.UI.Services;
using CommunityToolkit.Mvvm.Input;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    [RelayCommand]
    private void MarkLaunchSteps()
    {
        if (SelectedNode is null || SelectedNode.Type != "forLoop")
        {
            Log("Launch Steps: ابتدا یک For Loop را انتخاب کن");
            return;
        }
        Snapshot();
        LaunchStepsContract.Mark(Steps, SelectedNode);
        SelectedNode.RefreshSummary();
        MarkDirty();
        OnPropertyChanged(nameof(LaunchStepsStatus));
        Log("Launch Steps ثبت شد — فرزندان گروه در هر Launch یک‌بار و به‌ترتیب اجرا می‌شوند");
    }

    [RelayCommand]
    private void ClearLaunchSteps()
    {
        var group = LaunchStepsContract.Find(Steps);
        if (group is null)
        {
            Log("Launch Steps: گروهی ثبت نشده است");
            return;
        }
        Snapshot();
        group.Props[LaunchStepsContract.MarkerProperty] = false;
        group.RefreshSummary();
        MarkDirty();
        OnPropertyChanged(nameof(LaunchStepsStatus));
        Log("Launch Steps پاک شد");
    }

    public string LaunchStepsStatus
    {
        get
        {
            var group = LaunchStepsContract.Find(Steps);
            return group is null
                ? "گروهی تعیین نشده"
                : "گروه فعال: " + (string.IsNullOrWhiteSpace(group.Name) ? group.Summary : group.Name);
        }
    }
}
