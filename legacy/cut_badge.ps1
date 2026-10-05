param(
    [string]$InputDir   = "原图",   # 原图文件夹
    [string]$OutputDir  = "底图",   # 输出文件夹（抠好的透明 PNG 放在这里）
    [double]$ScanT      = 45,      # 边界扫描的颜色跃变阈值（RGB 各通道差值之和）
    [int]$Feather       = 4,       # 圆形边缘羽化宽度（像素）
    [int]$Margin        = 4,       # 裁切边距（像素）
    [switch]$Debug
)
$ErrorActionPreference = "Stop"

$code = @"
using System;
using System.IO;
using System.Drawing;
using System.Drawing.Imaging;
using System.Runtime.InteropServices;
using System.Collections.Generic;

public static class BadgeCutter
{
    struct Pt { public double x, y; }

    // 三点求圆（行列式法），返回圆心与半径；三点共线时返回 false
    static bool CircleFrom3(double x1, double y1, double x2, double y2, double x3, double y3,
                            out double cx, out double cy, out double r)
    {
        double d = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2));
        if (Math.Abs(d) < 1e-9) { cx = cy = r = 0; return false; }
        double s1 = x1 * x1 + y1 * y1, s2 = x2 * x2 + y2 * y2, s3 = x3 * x3 + y3 * y3;
        cx = (s1 * (y2 - y3) + s2 * (y3 - y1) + s3 * (y1 - y2)) / d;
        cy = (s1 * (x3 - x2) + s2 * (x1 - x3) + s3 * (x2 - x1)) / d;
        r = Math.Sqrt((x1 - cx) * (x1 - cx) + (y1 - cy) * (y1 - cy));
        return true;
    }

    // Kasa 最小二乘圆拟合（带内点重估）
    static void FitCircle(List<Pt> pts, double tol, int iters, out double cx, out double cy, out double r, out int inliers)
    {
        cx = 0; cy = 0; r = 0; inliers = 0;
        int n = pts.Count;
        double[] xa = new double[n], ya = new double[n];
        for (int i = 0; i < n; i++) { xa[i] = pts[i].x; ya[i] = pts[i].y; }
        bool[] use = new bool[n];
        for (int i = 0; i < n; i++) use[i] = true;
        for (int it = 0; it < iters; it++)
        {
            double Sx = 0, Sy = 0, Sxx = 0, Syy = 0, Sxy = 0, Sxxx = 0, Syyy = 0, Sxyy = 0, Sxxy = 0;
            int m = 0;
            for (int i = 0; i < n; i++)
            {
                if (!use[i]) continue;
                double x = xa[i], y = ya[i];
                Sx += x; Sy += y; Sxx += x * x; Syy += y * y; Sxy += x * y;
                Sxxx += x * x * x; Syyy += y * y * y; Sxyy += x * y * y; Sxxy += x * x * y;
                m++;
            }
            if (m < 3) break;
            double A11 = 2 * Sxx - 2 * Sx * Sx / m;
            double A12 = 2 * Sxy - 2 * Sx * Sy / m;
            double A22 = 2 * Syy - 2 * Sy * Sy / m;
            double B1 = Sxxx + Sxyy - (Sxx + Syy) * Sx / m;
            double B2 = Syyy + Sxxy - (Sxx + Syy) * Sy / m;
            double det = A11 * A22 - A12 * A12;
            if (Math.Abs(det) < 1e-12) break;
            double u = (B1 * A22 - B2 * A12) / det;
            double v = (B2 * A11 - B1 * A12) / det;
            cx = -u / 2; cy = -v / 2;
            r = Math.Sqrt(Math.Max(0, u * u / 4 + v * v / 4 + (Sxx + Syy + u * Sx + v * Sy) / m));
            // 重算 r 为平均距离
            double sumR = 0; int nr = 0;
            for (int i = 0; i < n; i++)
            {
                if (!use[i]) continue;
                sumR += Math.Sqrt((xa[i] - cx) * (xa[i] - cx) + (ya[i] - cy) * (ya[i] - cy));
                nr++;
            }
            if (nr > 0) r = sumR / nr;
            // 重新选内点
            bool changed = false;
            for (int i = 0; i < n; i++)
            {
                double d = Math.Abs(Math.Sqrt((xa[i] - cx) * (xa[i] - cx) + (ya[i] - cy) * (ya[i] - cy)) - r);
                bool nu = d <= tol;
                if (nu != use[i]) { use[i] = nu; changed = true; }
            }
            if (!changed && it >= 1) break;
        }
        inliers = 0;
        for (int i = 0; i < n; i++) if (use[i]) inliers++;
    }

    public static string Process(string input, string output, double scanT, int feather, int margin, bool debug)
    {
        Bitmap src = null;
        try { src = new Bitmap(input); }
        catch (Exception e) { return "ERR 读取失败: " + e.Message; }
        using (src)
        {
            int w = src.Width, h = src.Height;
            PixelFormat pf = src.PixelFormat;
            int bpp = Image.GetPixelFormatSize(pf) / 8;
            Bitmap work = src, converted = null;
            if (bpp != 3 && bpp != 4)
            {
                converted = new Bitmap(w, h, PixelFormat.Format24bppRgb);
                using (Graphics g = Graphics.FromImage(converted)) { g.DrawImage(src, 0, 0, w, h); }
                work = converted; pf = PixelFormat.Format24bppRgb; bpp = 3;
            }

            BitmapData bd = work.LockBits(new Rectangle(0, 0, w, h), ImageLockMode.ReadOnly, pf);
            int stride = bd.Stride;
            byte[] px = new byte[checked(stride * h)];
            Marshal.Copy(bd.Scan0, px, 0, px.Length);
            work.UnlockBits(bd);

            var pts = new List<Pt>();

            // ---- 1) 水平线扫描：从左右两侧向内找第一个颜色跃变点
            int hLines = 20;
            for (int li = 0; li < hLines; li++)
            {
                int y = (int)(h * (0.14 + 0.72 * li / (hLines - 1)));
                int r0 = 0, g0 = 0, b0 = 0, n0 = 0;
                for (int x = (int)(w * 0.05); x < (int)(w * 0.10); x++) { int i = y * w + x; r0 += px[i * bpp + 2]; g0 += px[i * bpp + 1]; b0 += px[i * bpp]; n0++; }
                if (n0 == 0) continue;
                r0 /= n0; g0 /= n0; b0 /= n0;
                int xL = -1;
                for (int x = (int)(w * 0.14); x <= w / 2; x++)
                {
                    int r = 0, g = 0, b = 0, n = 0;
                    for (int xx = x - 4; xx <= x + 4; xx++)
                    {
                        if (xx < 0 || xx >= w) continue;
                        int i = y * w + xx; r += px[i * bpp + 2]; g += px[i * bpp + 1]; b += px[i * bpp]; n++;
                    }
                    if (n == 0) continue;
                    r /= n; g /= n; b /= n;
                    if (Math.Abs(r - r0) + Math.Abs(g - g0) + Math.Abs(b - b0) > scanT) { xL = x; break; }
                }
                int r1 = 0, g1 = 0, b1 = 0, n1 = 0;
                for (int x = (int)(w * 0.90); x < (int)(w * 0.95); x++) { int i = y * w + x; r1 += px[i * bpp + 2]; g1 += px[i * bpp + 1]; b1 += px[i * bpp]; n1++; }
                if (n1 == 0) { if (xL >= 0) pts.Add(new Pt { x = xL, y = y }); continue; }
                r1 /= n1; g1 /= n1; b1 /= n1;
                int xR = -1;
                for (int x = (int)(w * 0.86); x >= w / 2; x--)
                {
                    int r = 0, g = 0, b = 0, n = 0;
                    for (int xx = x - 4; xx <= x + 4; xx++)
                    {
                        if (xx < 0 || xx >= w) continue;
                        int i = y * w + xx; r += px[i * bpp + 2]; g += px[i * bpp + 1]; b += px[i * bpp]; n++;
                    }
                    if (n == 0) continue;
                    r /= n; g /= n; b /= n;
                    if (Math.Abs(r - r1) + Math.Abs(g - g1) + Math.Abs(b - b1) > scanT) { xR = x; break; }
                }
                if (xL >= 0) pts.Add(new Pt { x = xL, y = y });
                if (xR >= 0) pts.Add(new Pt { x = xR, y = y });
            }

            // ---- 2) 垂直线扫描：从上下两侧向内找第一个颜色跃变点
            int vLines = 20;
            for (int li = 0; li < vLines; li++)
            {
                int x = (int)(w * (0.14 + 0.72 * li / (vLines - 1)));
                int r0 = 0, g0 = 0, b0 = 0, n0 = 0;
                for (int y = (int)(h * 0.05); y < (int)(h * 0.10); y++) { int i = y * w + x; r0 += px[i * bpp + 2]; g0 += px[i * bpp + 1]; b0 += px[i * bpp]; n0++; }
                if (n0 == 0) continue;
                r0 /= n0; g0 /= n0; b0 /= n0;
                int yT = -1;
                for (int y = (int)(h * 0.14); y <= h / 2; y++)
                {
                    int r = 0, g = 0, b = 0, n = 0;
                    for (int yy = y - 4; yy <= y + 4; yy++)
                    {
                        if (yy < 0 || yy >= h) continue;
                        int i = yy * w + x; r += px[i * bpp + 2]; g += px[i * bpp + 1]; b += px[i * bpp]; n++;
                    }
                    if (n == 0) continue;
                    r /= n; g /= n; b /= n;
                    if (Math.Abs(r - r0) + Math.Abs(g - g0) + Math.Abs(b - b0) > scanT) { yT = y; break; }
                }
                int r1 = 0, g1 = 0, b1 = 0, n1 = 0;
                for (int y = (int)(h * 0.90); y < (int)(h * 0.95); y++) { int i = y * w + x; r1 += px[i * bpp + 2]; g1 += px[i * bpp + 1]; b1 += px[i * bpp]; n1++; }
                if (n1 == 0) { if (yT >= 0) pts.Add(new Pt { x = x, y = yT }); continue; }
                r1 /= n1; g1 /= n1; b1 /= n1;
                int yB = -1;
                for (int y = (int)(h * 0.86); y >= h / 2; y--)
                {
                    int r = 0, g = 0, b = 0, n = 0;
                    for (int yy = y - 4; yy <= y + 4; yy++)
                    {
                        if (yy < 0 || yy >= h) continue;
                        int i = yy * w + x; r += px[i * bpp + 2]; g += px[i * bpp + 1]; b += px[i * bpp]; n++;
                    }
                    if (n == 0) continue;
                    r /= n; g /= n; b /= n;
                    if (Math.Abs(r - r1) + Math.Abs(g - g1) + Math.Abs(b - b1) > scanT) { yB = y; break; }
                }
                if (yT >= 0) pts.Add(new Pt { x = x, y = yT });
                if (yB >= 0) pts.Add(new Pt { x = x, y = yB });
            }

            if (pts.Count < 6) { if (converted != null) converted.Dispose(); return "ERR 边界点不足(" + pts.Count + ")，未找到圆形徽章"; }

            // ---- 3) RANSAC 圆拟合
            double bestCx = 0, bestCy = 0, bestR = 0; int bestIn = -1;
            var rnd = new Random(2024);
            int nPts = pts.Count;
            for (int it = 0; it < 600; it++)
            {
                int a = rnd.Next(nPts), b = rnd.Next(nPts), c = rnd.Next(nPts);
                if (a == b || b == c || a == c) continue;
                double cx, cy, r;
                if (!CircleFrom3(pts[a].x, pts[a].y, pts[b].x, pts[b].y, pts[c].x, pts[c].y, out cx, out cy, out r)) continue;
                double minDim = Math.Min(w, h);
                if (r < minDim * 0.10 || r > minDim * 0.70) continue;
                if (cx < w * 0.15 || cx > w * 0.85 || cy < h * 0.15 || cy > h * 0.85) continue;
                int inn = 0;
                for (int i = 0; i < nPts; i++)
                {
                    double d = Math.Abs(Math.Sqrt((pts[i].x - cx) * (pts[i].x - cx) + (pts[i].y - cy) * (pts[i].y - cy)) - r);
                    if (d <= 4.0) inn++;
                }
                if (inn > bestIn) { bestIn = inn; bestCx = cx; bestCy = cy; bestR = r; }
            }
            if (bestIn < 8) { if (converted != null) converted.Dispose(); return "ERR 未找到可靠的圆形(最多内点 " + bestIn + ")"; }

            // ---- 4) 最小二乘精修
            var inPts = new List<Pt>();
            for (int i = 0; i < nPts; i++)
            {
                double d = Math.Abs(Math.Sqrt((pts[i].x - bestCx) * (pts[i].x - bestCx) + (pts[i].y - bestCy) * (pts[i].y - bestCy)) - bestR);
                if (d <= 6.0) inPts.Add(pts[i]);
            }
            double fcx, fcy, fr; int fIn;
            FitCircle(inPts, 5.0, 6, out fcx, out fcy, out fr, out fIn);
            if (fIn >= 8 && fr > 0)
            {
                // 精修结果必须仍然合理
                double minDim2 = Math.Min(w, h);
                if (fr >= minDim2 * 0.08 && fr <= minDim2 * 0.75 && fcx > 0 && fcy > 0 && fcx < w && fcy < h)
                { bestCx = fcx; bestCy = fcy; bestR = fr; bestIn = fIn; }
            }

            if (debug)
            {
                Console.WriteLine("  [debug] scanPoints=" + pts.Count + " ransacInliers=" + bestIn +
                    " circle=(cx=" + Math.Round(bestCx, 1) + ", cy=" + Math.Round(bestCy, 1) + ", r=" + Math.Round(bestR, 1) + ")");
                int dc = 80, dr = 40;
                var sb = new System.Text.StringBuilder();
                for (int ry = 0; ry < dr; ry++)
                {
                    for (int rx = 0; rx < dc; rx++)
                    {
                        double sx = (rx + 0.5) * w / dc, sy = (ry + 0.5) * h / dr;
                        double d = Math.Sqrt((sx - bestCx) * (sx - bestCx) + (sy - bestCy) * (sy - bestCy));
                        sb.Append(d <= bestR ? '#' : ' ');
                    }
                    sb.AppendLine();
                }
                Console.WriteLine(sb.ToString());
            }

            // ---- 5) 圆内全部保留，圆边缘羽化
            int cx0 = Math.Max(0, (int)(bestCx - bestR - feather - margin));
            int cy0 = Math.Max(0, (int)(bestCy - bestR - feather - margin));
            int cx1 = Math.Min(w - 1, (int)(bestCx + bestR + feather + margin));
            int cy1 = Math.Min(h - 1, (int)(bestCy + bestR + feather + margin));
            int cw = cx1 - cx0 + 1, ch = cy1 - cy0 + 1;

            byte[] alpha = new byte[cw * ch];
            for (int y = 0; y < ch; y++)
                for (int x = 0; x < cw; x++)
                {
                    double dx = (cx0 + x + 0.5) - bestCx;
                    double dy = (cy0 + y + 0.5) - bestCy;
                    double d = Math.Sqrt(dx * dx + dy * dy);
                    if (d <= bestR) alpha[y * cw + x] = 255;
                    else if (d >= bestR + feather) alpha[y * cw + x] = 0;
                    else alpha[y * cw + x] = (byte)Math.Max(0, Math.Min(255, (bestR + feather - d) / feather * 255.0 + 0.5));
                }

            using (Bitmap outBmp = new Bitmap(cw, ch, PixelFormat.Format32bppArgb))
            {
                BitmapData obd = outBmp.LockBits(new Rectangle(0, 0, cw, ch), ImageLockMode.WriteOnly, PixelFormat.Format32bppArgb);
                byte[] opx = new byte[obd.Stride * ch];
                for (int y = 0; y < ch; y++)
                    for (int x = 0; x < cw; x++)
                    {
                        int sx = cx0 + x, sy = cy0 + y;
                        int si = sy * w + sx;
                        int di = y * obd.Stride + x * 4;
                        opx[di + 2] = px[si * bpp + 2];
                        opx[di + 1] = px[si * bpp + 1];
                        opx[di] = px[si * bpp];
                        opx[di + 3] = alpha[y * cw + x];
                    }
                Marshal.Copy(opx, 0, obd.Scan0, opx.Length);
                outBmp.UnlockBits(obd);
                string dir = Path.GetDirectoryName(output);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                outBmp.Save(output, ImageFormat.Png);
            }
            if (converted != null) converted.Dispose();
            return "OK " + cw + "x" + ch + " circle=(cx=" + Math.Round(bestCx, 0) + ", cy=" + Math.Round(bestCy, 0) + ", r=" + Math.Round(bestR, 0) + ")";
        }
    }
}
"@

if (-not ("BadgeCutter" -as [type])) {
    Add-Type -TypeDefinition $code -Language CSharp -ReferencedAssemblies System.Drawing
}

# ================= 批处理 =================
$root = $PSScriptRoot
if ([string]::IsNullOrEmpty($root)) { $root = Get-Location }
$inDir  = Join-Path $root $InputDir
$outDir = Join-Path $root $OutputDir
if (-not (Test-Path $inDir)) { Write-Host "[错误] 找不到原图文件夹: $inDir" -ForegroundColor Red; exit 1 }
New-Item -ItemType Directory -Path $outDir -Force | Out-Null

$exts = @("*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif", "*.tif", "*.tiff")
$files = foreach ($e in $exts) { Get-ChildItem -Path $inDir -Filter $e -File -ErrorAction SilentlyContinue }
$files = @($files | Sort-Object FullName -Unique)
if ($files.Count -eq 0) { Write-Host "[提示] 原图文件夹里没有图片文件" -ForegroundColor Yellow; exit 0 }

Write-Host ""
Write-Host "==== 徽章抠图工具（圆形）====" -ForegroundColor Cyan
Write-Host "原图: $inDir ($($files.Count) 张)"
Write-Host "输出: $outDir"
Write-Host ""

$ok = 0; $fail = 0
foreach ($f in $files) {
    $outName = $f.BaseName + ".png"
    $outPath = Join-Path $outDir $outName
    $r = [BadgeCutter]::Process($f.FullName, $outPath, $ScanT, $Feather, $Margin, $Debug.IsPresent)
    if ($r.StartsWith("ERR")) {
        Write-Host "[失败] $($f.Name)  $r" -ForegroundColor Red
        $fail++
    } else {
        Write-Host "[完成] $($f.Name) -> $outName  ($r)" -ForegroundColor Green
        $ok++
    }
}

Write-Host ""
Write-Host "==== 全部完成：成功 $ok 张，失败 $fail 张 ====" -ForegroundColor Cyan
