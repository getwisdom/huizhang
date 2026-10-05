# _analyze.ps1 —— 底图 PNG 与原图 JPG 的差值分析（开发辅助脚本，完成后可删除）
param(
    [string]$PngPath = "底图\测试_1.png",
    [string]$JpgPath = "原图\测试_1.jpg"
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$code = @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;

public static class ImgA
{
    public static byte[] LoadRgb(string path, out int w, out int h)
    {
        using (Bitmap b = new Bitmap(path))
        {
            w = b.Width; h = b.Height;
            Bitmap c = new Bitmap(w, h, PixelFormat.Format24bppRgb);
            using (Graphics g = Graphics.FromImage(c)) { g.DrawImage(b, 0, 0, w, h); }
            BitmapData bd = c.LockBits(new Rectangle(0,0,w,h), ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
            byte[] px = new byte[bd.Stride * h];
            Marshal.Copy(bd.Scan0, px, 0, px.Length);
            c.UnlockBits(bd);
            byte[] outx = new byte[w*h*3];
            for (int y=0; y<h; y++) Array.Copy(px, y*bd.Stride, outx, y*w*3, w*3);
            c.Dispose();
            return outx;
        }
    }
    public static byte[] LoadAlpha(string path, out int w, out int h)
    {
        using (Bitmap b = new Bitmap(path))
        {
            w = b.Width; h = b.Height;
            BitmapData bd = b.LockBits(new Rectangle(0,0,w,h), ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            byte[] px = new byte[bd.Stride * h];
            Marshal.Copy(bd.Scan0, px, 0, px.Length);
            b.UnlockBits(bd);
            byte[] outx = new byte[w*h];
            for (int y=0; y<h; y++) for (int x=0; x<w; x++) outx[y*w+x] = px[y*bd.Stride + x*4 + 3];
            return outx;
        }
    }
    // 在 JPG 内搜索与 PNG 圆内内容最匹配的偏移，返回 "ox,oy,meanDiff"
    public static string SearchOffset(byte[] p, int pw, int ph, byte[] a, byte[] j, int jw, int jh,
                                      int oy0, int oy1, int ox0, int ox1, int step)
    {
        double best = double.MaxValue; int box = 0, boy = 0;
        for (int oy = oy0; oy <= oy1; oy += step)
        for (int ox = ox0; ox <= ox1; ox += step)
        {
            double sum = 0; long n = 0;
            for (int y = 30; y < ph - 30; y += 10)
            for (int x = 30; x < pw - 30; x += 10)
            {
                int pi = y * pw + x;
                if (a[pi] < 200) continue;
                int jx = ox + x, jy = oy + y;
                if (jx < 0 || jy < 0 || jx >= jw || jy >= jh) continue;
                int ji = jy * jw + jx;
                int dr = p[pi*3]   - j[ji*3];
                int dg = p[pi*3+1] - j[ji*3+1];
                int db = p[pi*3+2] - j[ji*3+2];
                sum += Math.Abs(dr) + Math.Abs(dg) + Math.Abs(db); n++;
            }
            if (n == 0) continue;
            double mean = sum / n;
            if (mean < best) { best = mean; box = ox; boy = oy; }
        }
        return box + "," + boy + "," + Math.Round(best, 2);
    }
    // 差值图 ASCII：只显示 |dr|+|dg|+|db| 超过阈值的位置
    public static string DiffAscii(byte[] p, int pw, int ph, byte[] a, byte[] j, int jw, int jh,
                                   int ox, int oy, int step, int thr, int onlyY)
    {
        var sb = new System.Text.StringBuilder();
        for (int y = 0; y < ph; y += step)
        {
            for (int x = 0; x < pw; x += step)
            {
                int pi = y * pw + x;
                if (a[pi] < 128) { sb.Append(' '); continue; }
                int jx = ox + x, jy = oy + y;
                char ch;
                if (jx < 0 || jy < 0 || jx >= jw || jy >= jh) { ch = ' '; }
                else
                {
                    int ji = jy * jw + jx;
                    int dr = p[pi*3]   - j[ji*3];
                    int dg = p[pi*3+1] - j[ji*3+1];
                    int db = p[pi*3+2] - j[ji*3+2];
                    int m = Math.Abs(dr) + Math.Abs(dg) + Math.Abs(db);
                    if (m < thr) ch = '.';
                    else
                    {
                        // 判定差值的色调：偏黄(高亮)、偏灰(水印/网格)、其他
                        int lr = p[pi*3], lg = p[pi*3+1], lb = p[pi*3+2];
                        if (onlyY == 1)
                        {
                            // 只看“原图不是黄色、PNG 变黄”的位置（黄色高亮叠加）
                            bool pngYellow = lr > 200 && lg > 170 && lb < 160;
                            bool jpgYellow = j[ji*3] > 200 && j[ji*3+1] > 170 && j[ji*3+2] < 160;
                            ch = (pngYellow && !jpgYellow) ? 'H' : '.';
                        }
                        else
                        {
                            if (lr > 200 && lg > 170 && lb < 160) ch = 'H';
                            else if (Math.Abs(dr) <= 18 && Math.Abs(dg) <= 18 && Math.Abs(db) <= 18) ch = 'g';
                            else ch = '*';
                        }
                    }
                }
                sb.Append(ch);
            }
            sb.AppendLine();
        }
        return sb.ToString();
    }
}
"@
if (-not ("ImgA" -as [type])) { Add-Type -TypeDefinition $code -Language CSharp -ReferencedAssemblies System.Drawing }

$root = $PSScriptRoot
if ([string]::IsNullOrEmpty($root)) { $root = Get-Location }
$png = Join-Path $root $PngPath
$jpg = Join-Path $root $JpgPath

$pw=0; $ph=0; $aw=0; $ah=0; $jw=0; $jh=0
$p = [ImgA]::LoadRgb($png, [ref]$pw, [ref]$ph)
$a = [ImgA]::LoadAlpha($png, [ref]$aw, [ref]$ah)
$j = [ImgA]::LoadRgb($jpg, [ref]$jw, [ref]$jh)
Write-Output ("PNG {0}x{1}  JPG {2}x{3}" -f $pw,$ph,$jw,$jh)

# 1) 粗搜偏移
$r1 = [ImgA]::SearchOffset($p,$pw,$ph,$a,$j,$jw,$jh, 100, 240, 100, 240, 8)
$parts = $r1 -split ","
$ox0 = [int]$parts[0]; $oy0 = [int]$parts[1]
Write-Output ("粗搜偏移: ox={0} oy={1} meanDiff={2}" -f $ox0,$oy0,$parts[2])
# 2) 精搜偏移（±6）
$r2 = [ImgA]::SearchOffset($p,$pw,$ph,$a,$j,$jw,$jh, ($oy0-6), ($oy0+6), ($ox0-6), ($ox0+6), 1)
$parts2 = $r2 -split ","
$ox = [int]$parts2[0]; $oy = [int]$parts2[1]
Write-Output ("精搜偏移: ox={0} oy={1} meanDiff={2}" -f $ox,$oy,$parts2[2])

Write-Output "--- 差值图 (step=6, thr=45)  * = 差值大  H = 偏黄  g = 灰差 ---"
$map = [ImgA]::DiffAscii($p,$pw,$ph,$a,$j,$jw,$jh, $ox,$oy, 6, 45, 0)
Write-Output $map

Write-Output "--- 黄色高亮叠加图 (step=4, 只看 PNG黄/JPG非黄)  H = 高亮 ---"
$map2 = [ImgA]::DiffAscii($p,$pw,$ph,$a,$j,$jw,$jh, $ox,$oy, 4, 0, 1)
Write-Output $map2
