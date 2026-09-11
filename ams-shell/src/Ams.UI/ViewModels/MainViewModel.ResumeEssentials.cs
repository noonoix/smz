using Ams.UI.Services;
using CommunityToolkit.Mvvm.Input;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    [RelayCommand]
    private void MarkResumeEssentials()
    {
        if (SelectedNode is null || SelectedNode.Type != "randomPackage")
        {
            Log("Resume Essentials: ابتدا یک Random Package را انتخاب کن");
            return;
        }
        Snapshot();
        ResumeEssentialsContract.Mark(Steps, SelectedNode);
        SelectedNode.RefreshSummary();
        MarkDirty();
        Log("Resume Essentials ثبت شد — حالت بسته روی Shuffle All قفل شد");
    }

    [RelayCommand]
    private void ClearResumeEssentials()
    {
        var package = ResumeEssentialsContract.Find(Steps);
        if (package is null)
        {
            Log("Resume Essentials: بسته‌ای ثبت نشده است");
            return;
        }
        Snapshot();
        package.Props[ResumeEssentialsContract.MarkerProperty] = false;
        package.RefreshSummary();
        MarkDirty();
        Log("Resume Essentials پاک شد");
    }

    public string ResumeEssentialsStatus
    {
        get
        {
            var package = ResumeEssentialsContract.Find(Steps);
            return package is null
                ? "بسته‌ای تعیین نشده"
                : "بسته‌ی فعال: " + (string.IsNullOrWhiteSpace(package.Name) ? package.Summary : package.Name);
        }
    }
}
