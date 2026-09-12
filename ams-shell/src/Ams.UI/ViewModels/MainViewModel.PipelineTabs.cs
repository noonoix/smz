using System.Collections.ObjectModel;
using System.IO;
using Ams.UI.Models;
using Ams.UI.Services;
using CommunityToolkit.Mvvm.Input;

namespace Ams.UI.ViewModels;

public partial class MainViewModel
{
    private PipelineWorkspace _pipelineWorkspace = new();
    private PipelineTabDocument? _activePipelineTab;
    private bool _pipelineInitialized;

    public ObservableCollection<PipelineTabDocument> PipelineTabs => _pipelineWorkspace.Tabs;
    public PipelineTabDocument? ActivePipelineTab => _activePipelineTab;
    public string ActivePipelineTitle => _activePipelineTab?.Title ?? "Main";
    public bool IsLaunchPipeline => _activePipelineTab?.Kind == PipelineKind.Launch;

    public void InitializePipelineTabs()
    {
        if (_pipelineInitialized) return;
        _pipelineInitialized = true;
        var main = _pipelineWorkspace[PipelineKind.Main];
        CopyTree(Steps, main.Steps);
        _activePipelineTab = main;
        OnPropertyChanged(nameof(PipelineTabs));
        OnPropertyChanged(nameof(ActivePipelineTab));
        OnPropertyChanged(nameof(ActivePipelineTitle));
        OnPropertyChanged(nameof(IsLaunchPipeline));
    }

    [RelayCommand]
    private void SwitchPipeline(PipelineTabDocument? tab)
    {
        if (tab is null || ReferenceEquals(tab, _activePipelineTab) || IsRunning) return;
        InitializePipelineTabs();
        CaptureActivePipeline();
        _activePipelineTab = tab;
        LoadActivePipeline();
        OnPropertyChanged(nameof(ActivePipelineTab));
        OnPropertyChanged(nameof(ActivePipelineTitle));
        OnPropertyChanged(nameof(IsLaunchPipeline));
        Log("pipeline tab: " + tab.Title);
    }

    internal PipelineWorkspace CapturePipelineWorkspaceForExport()
    {
        InitializePipelineTabs();
        CaptureActivePipeline();
        return _pipelineWorkspace;
    }

    private void CaptureActivePipeline()
    {
        if (_activePipelineTab is null) return;
        CopyTree(Steps, _activePipelineTab.Steps);
        _activePipelineTab.IsDirty |= _dirty;
    }

    private void LoadActivePipeline()
    {
        Steps.Clear();
        if (_activePipelineTab is not null) CopyTree(_activePipelineTab.Steps, Steps);
        SelectedNodes = new();
        SelectedNode = null;
        _collapsed.Clear();
        _undo.Clear();
        _redo.Clear();
        Renumber();
    }

    private static void CopyTree(IEnumerable<StepNode> source, ICollection<StepNode> destination)
    {
        destination.Clear();
        foreach (var node in StepTreeSerializer.Restore(StepTreeSerializer.Snapshot(source)))
            destination.Add(node);
    }

    [RelayCommand]
    private void NewPipelineWorkspace()
    {
        if (!ConfirmDiscard()) return;
        _pipelineWorkspace = new PipelineWorkspace();
        _activePipelineTab = _pipelineWorkspace[PipelineKind.Main];
        _currentFile = null;
        _dirty = false;
        LoadActivePipeline();
        OnPropertyChanged(nameof(PipelineTabs));
        OnPropertyChanged(nameof(ActivePipelineTab));
        OnPropertyChanged(nameof(ActivePipelineTitle));
        OnPropertyChanged(nameof(IsLaunchPipeline));
        UpdateFileText();
        Log("new pipeline workspace");
    }

    [RelayCommand]
    private void OpenPipelineWorkspace()
    {
        if (!ConfirmDiscard()) return;
        var dialog = new Microsoft.Win32.OpenFileDialog { Filter = "AMS pipeline (*.amsj)|*.amsj" };
        if (dialog.ShowDialog() != true) return;
        try
        {
            var json = File.ReadAllText(dialog.FileName);
            try { _pipelineWorkspace = PipelineWorkspaceSerializer.Deserialize(json); }
            catch (InvalidDataException) { _pipelineWorkspace = PipelineWorkspace.FromLegacy(DocumentService.Load(dialog.FileName)); }
            _activePipelineTab = _pipelineWorkspace[PipelineKind.Main];
            _currentFile = dialog.FileName;
            _dirty = false;
            LoadActivePipeline();
            foreach (var tab in _pipelineWorkspace.Tabs) tab.IsDirty = false;
            OnPropertyChanged(nameof(PipelineTabs));
            OnPropertyChanged(nameof(ActivePipelineTab));
            OnPropertyChanged(nameof(ActivePipelineTitle));
        OnPropertyChanged(nameof(IsLaunchPipeline));
            UpdateFileText();
            Log("pipeline workspace opened: " + dialog.FileName);
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show("بازکردن Pipeline ناموفق بود: " + ex.Message,
                "Open Pipeline", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
        }
    }

    [RelayCommand]
    private void SavePipelineWorkspace() => SavePipelineWorkspaceCore(false);

    [RelayCommand]
    private void SavePipelineWorkspaceAs() => SavePipelineWorkspaceCore(true);

    private void SavePipelineWorkspaceCore(bool saveAs)
    {
        InitializePipelineTabs();
        CaptureActivePipeline();
        var path = _currentFile;
        if (saveAs || string.IsNullOrWhiteSpace(path))
        {
            var dialog = new Microsoft.Win32.SaveFileDialog
            {
                Filter = "AMS pipeline (*.amsj)|*.amsj",
                FileName = "autocycle.amsj",
            };
            if (dialog.ShowDialog() != true) return;
            path = dialog.FileName;
        }
        try
        {
            File.WriteAllText(path!, PipelineWorkspaceSerializer.Serialize(_pipelineWorkspace));
            _currentFile = path;
            _dirty = false;
            foreach (var tab in _pipelineWorkspace.Tabs) tab.IsDirty = false;
            UpdateFileText();
            Log("pipeline workspace saved: " + path);
        }
        catch (Exception ex)
        {
            System.Windows.MessageBox.Show("ذخیره‌ی Pipeline ناموفق بود: " + ex.Message,
                "Save Pipeline", System.Windows.MessageBoxButton.OK, System.Windows.MessageBoxImage.Error);
        }
    }
}
