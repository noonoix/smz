namespace Ams.UI.Models;

/// <summary>
/// Windows Virtual-Key codes (decimal). The board firmware expects decimal VK codes
/// (ams_board.ino → vk_to_hid). Verified against the firmware mapping table.
/// </summary>
public static class KeyMap
{
    public static readonly IReadOnlyDictionary<string, int> VK = BuildVk();

    /// <summary>Modifier names → VK. Used by the Keystroke dialog checkboxes.</summary>
    public static readonly IReadOnlyDictionary<string, int> Modifiers = new Dictionary<string, int>
    {
        ["Ctrl"] = 162,   // VK_LCONTROL (firmware also accepts 0x11)
        ["Shift"] = 160,  // VK_LSHIFT
        ["Alt"] = 164,    // VK_LMENU
        ["Win"] = 91,     // VK_LWIN
    };

    public static IReadOnlyList<string> KeyNames { get; } = VK.Keys.ToArray();

    private static IReadOnlyDictionary<string, int> BuildVk()
    {
        var d = new Dictionary<string, int>();
        for (char c = 'A'; c <= 'Z'; c++) d[c.ToString()] = c;        // 65-90
        for (int i = 0; i <= 9; i++) d[i.ToString()] = 48 + i;        // 0-9
        for (int f = 1; f <= 12; f++) d["F" + f] = 111 + f;           // F1-F12 = 112-123
        d["ENTER"] = 13; d["ESC"] = 27; d["SPACE"] = 32; d["TAB"] = 9; d["BACKSPACE"] = 8;
        d["DELETE"] = 46; d["INSERT"] = 45; d["HOME"] = 36; d["END"] = 35;
        d["PGUP"] = 33; d["PGDN"] = 34;
        d["LEFT"] = 37; d["UP"] = 38; d["RIGHT"] = 39; d["DOWN"] = 40;
        d["CAPS LOCK"] = 20; d["NUM LOCK"] = 144; d["SCROLL LOCK"] = 145;
        d["PRINT SCREEN"] = 44; d["BREAK"] = 19;
        for (int i = 0; i <= 9; i++) d["NUMPAD" + i] = 96 + i;        // 96-105
        d[","] = 188; d["-"] = 189; d["."] = 190; d["/"] = 191;
        d[";"] = 186; d["="] = 187; d["["] = 219; d["]"] = 221;
        d["\\"] = 220; d["'"] = 222; d["`"] = 192;
        return d;
    }
}
