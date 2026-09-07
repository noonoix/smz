using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;

namespace Ams.UI.Services;

/// <summary>
/// Native embedded-picture extractor for .amk files (v0.8.2 — the missing puzzle piece).
///
/// Why: the python toolkit decoder does not reliably extract the Search Picture images
/// (user report: an imported findImage step had NO picture). The binary format carries the
/// picture INSIDE the TYPE 2 record as a BMPN field — layout fully reverse-engineered from
/// the sample files (pic/desktop/daroon1.amk):
///
///   BMPN = 'W' <04> <width:i32> · 'H' <04> <height:i32> · 'PB' <04> <bpp:i32 (=32)>
///          · "PIX\0" <pixLen:i32> <pixels: BGRA, 4 bytes/px>
///
/// (BMPN[44..] is byte-identical to the record's PIX field in every sample; one BMPN per
/// TYPE 2 record in all observed files — AMK stores OR-pictures as separate records.)
///
/// Images are written as PNG into <amkname>_images/ next to the .amk — persistent,
/// because findImage steps reference those files at run time. The scan order (file order)
/// matches the importer's pre-order walk of TYPE 2 records (SUB payloads are stored inline,
/// so both orders agree), so the Nth extracted image belongs to the Nth findImage node.
/// </summary>
public static class AmkImageExtractor
{
    private static readonly byte[] NPMB = { (byte)'N', (byte)'P', (byte)'M', (byte)'B' };   // "NPMB" in the binary

    /// <summary>Extracts every embedded Search-Picture image as PNG. Returns written paths
    /// in file order. Never throws — malformed candidates are skipped (false-positive guard).</summary>
    public static List<string> ExtractImages(string amkPath, string imgDir, Action<string>? log = null)
    {
        var written = new List<string>();
        byte[] data;
        try { data = File.ReadAllBytes(amkPath); }
        catch (Exception ex) { log?.Invoke("native extractor: cannot read file: " + ex.Message); return written; }

        try { Directory.CreateDirectory(imgDir); }
        catch (Exception ex) { log?.Invoke("native extractor: cannot create " + imgDir + ": " + ex.Message); return written; }

        string baseName = Path.GetFileNameWithoutExtension(amkPath);
        int pos = 0, n = 0;
        while ((pos = IndexOf(data, NPMB, pos)) >= 0)
        {
            int p = pos + 4;
            if (p + 4 > data.Length) break;
            int len = BitConverter.ToInt32(data, p); p += 4;
            if (len < 44 || p + len > data.Length) { pos = p; continue; }

            // self-validating header: 'W' <04> <w> 'H' <04> <h> 'PB' <04> <32> "PIX\0" <pixLen>
            // Note: "PIX\0" = 0x58 0x49 0x50 0x00 (X I P NUL) — NOT P-I-X reversed
            bool headerOk = data[p] == (byte)'W' && data[p + 4] == 4
                         && data[p + 12] == (byte)'H' && data[p + 16] == 4
                         && data[p + 24] == (byte)'P' && data[p + 25] == (byte)'B' && data[p + 28] == 4
                         && data[p + 36] == (byte)'X' && data[p + 37] == (byte)'I'
                         && data[p + 38] == (byte)'P' && data[p + 39] == 0;
            if (!headerOk) { pos = p; continue; }

            int w = BitConverter.ToInt32(data, p + 8);
            int h = BitConverter.ToInt32(data, p + 20);
            int bpp = BitConverter.ToInt32(data, p + 32);
            int pixLen = BitConverter.ToInt32(data, p + 40);
            if (w < 1 || h < 1 || w > 8192 || h > 8192 || bpp != 32
                || pixLen != w * h * 4 || 44 + pixLen != len)
            { pos = p; continue; }   // not a picture field — skip

            try
            {
                using var bmp = new Bitmap(w, h, PixelFormat.Format32bppArgb);
                var rect = new Rectangle(0, 0, w, h);
                var bd = bmp.LockBits(rect, ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
                try { Marshal.Copy(data, p + 44, bd.Scan0, pixLen); }   // BGRA == ARGB32 memory layout
                finally { bmp.UnlockBits(bd); }

                var path = Path.Combine(imgDir, $"{baseName}_pic{++n}_{w}x{h}.png");
                bmp.Save(path, ImageFormat.Png);
                written.Add(path);
                log?.Invoke($"native extractor: picture #{n} ({w}x{h}) → {Path.GetFileName(path)}");
            }
            catch (Exception ex) { log?.Invoke("native extractor: write failed: " + ex.Message); }

            pos = p + len;
        }
        return written;
    }

    private static int IndexOf(byte[] hay, byte[] needle, int from)
    {
        for (int i = from; i + needle.Length <= hay.Length; i++)
        {
            if (hay[i] == needle[0] && hay[i + 1] == needle[1]
                && hay[i + 2] == needle[2] && hay[i + 3] == needle[3])
                return i;
        }
        return -1;
    }
}
