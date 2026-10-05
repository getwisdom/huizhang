# layout.ps1 —— 徽章排版:把 底图 里的徽章按 排版demo.png 的圆形槽位排版,每 11 张一页,输出到 已排版
param(
    [string]$Demo = "排版demo.png",
    [string]$BaseDir = "底图",
    [string]$OutDir = "已排版"
)
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
if ([string]::IsNullOrEmpty($root)) { $root = Get-Location }
Add-Type -AssemblyName System.Drawing

$code = @"
using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.Drawing.Drawing2D;
using System.Runtime.InteropServices;
using System.Text;
using System.Collections.Generic;
using System.IO;

public static class Layout2 {

    [DllImport("shlwapi.dll", CharSet = CharSet.Unicode)]
    public static extern int StrCmpLogicalW(string x, string y);

    public class BaseInfo {
        public string Path;
        public Bitmap Src;
        public int MinX, MinY, MaxX, MaxY;
        public double Br;
    }

    public static byte[] LoadRgb(string path, out int w, out int h) {
        using (var b = new Bitmap(path)) {
            w = b.Width; h = b.Height;
            var c = new Bitmap(w, h, PixelFormat.Format24bppRgb);
            using (var g = Graphics.FromImage(c)) { g.DrawImage(b, 0, 0, w, h); }
            var rect = new Rectangle(0, 0, w, h);
            var bd = c.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
            var raw = new byte[bd.Stride * h];
            Marshal.Copy(bd.Scan0, raw, 0, raw.Length);
            c.UnlockBits(bd);
            var outPx = new byte[w * h * 3];
            for (int y = 0; y < h; y++) Array.Copy(raw, y * bd.Stride, outPx, y * w * 3, w * 3);
            c.Dispose();
            return outPx;
        }
    }

    public static byte[] LoadArgb(string path, out int w, out int h) {
        using (var b = new Bitmap(path)) {
            w = b.Width; h = b.Height;
            var rect = new Rectangle(0, 0, w, h);
            var bd = b.LockBits(rect, ImageLockMode.ReadOnly, PixelFormat.Format32bppArgb);
            var raw = new byte[bd.Stride * h];
            Marshal.Copy(bd.Scan0, raw, 0, raw.Length);
            b.UnlockBits(bd);
            var outPx = new byte[w * h * 4];
            for (int y = 0; y < h; y++) Array.Copy(raw, y * bd.Stride, outPx, y * w * 4, w * 4);
            return outPx;
        }
    }

    // 圆形槽位:包围盒中心十字线扫描法(对相邻圆不敏感)
    // 在 bbox 中心行扫水平弦、中心列扫垂直弦,取弦中点与最大弦长
    public static bool FitCircle(byte[] px, int w, int h, int thr, int x0, int y0, int x1, int y1,
                                 bool alphaMode, out double cx, out double cy, out double r) {
        cx = 0; cy = 0; r = 0;
        x0 = Math.Max(0, x0); y0 = Math.Max(0, y0);
        x1 = Math.Min(w - 1, x1); y1 = Math.Min(h - 1, y1);
        double cx0 = (x0 + x1) / 2.0, cy0 = (y0 + y1) / 2.0;
        int yc = (int)Math.Round(cy0);
        int hFirst = -1, hLast = -1;
        for (int x = x0; x <= x1; x++) {
            bool hit = alphaMode ? px[(yc*w+x)*4+3] > 16
                : Math.Abs(px[(yc*w+x)*3]-255) + Math.Abs(px[(yc*w+x)*3+1]-255) + Math.Abs(px[(yc*w+x)*3+2]-255) > thr;
            if (hit) { if (hFirst < 0) hFirst = x; hLast = x; }
        }
        int xc = (int)Math.Round(cx0);
        int vFirst = -1, vLast = -1;
        for (int y = y0; y <= y1; y++) {
            bool hit = alphaMode ? px[(y*w+xc)*4+3] > 16
                : Math.Abs(px[(y*w+xc)*3]-255) + Math.Abs(px[(y*w+xc)*3+1]-255) + Math.Abs(px[(y*w+xc)*3+2]-255) > thr;
            if (hit) { if (vFirst < 0) vFirst = y; vLast = y; }
        }
        if (hFirst < 0 || vFirst < 0) return false;
        double wh = hLast - hFirst + 1, wv = vLast - vFirst + 1;
        cx = (hFirst + hLast) / 2.0;
        cy = (vFirst + vLast) / 2.0;
        r = Math.Max(wh, wv) / 2.0;
        return r > 10;
    }

    public static string Run(string demoPath, string baseDir, string outDir, string root) {
        var sb = new StringBuilder();
        int dw, dh;
        var dp = LoadRgb(demoPath, out dw, out dh);
        sb.AppendLine(string.Format("demo: {0}x{1}", dw, dh));

        // 1) 连通域找槽位(step=4)
        int step = 4;
        int sw = dw / step, sh = dh / step;
        var mask = new bool[sw * sh];
        for (int y = 0; y < sh; y++) for (int x = 0; x < sw; x++) {
            int i = (y * step * dw + x * step) * 3;
            int d = Math.Abs(dp[i]-255) + Math.Abs(dp[i+1]-255) + Math.Abs(dp[i+2]-255);
            mask[y*sw+x] = d > 60;
        }
        var label = new int[sw*sh];
        for (int i = 0; i < label.Length; i++) label[i] = -1;
        var comps = new List<int[]>();
        int[] ddx = {1,0,-1,0}, ddy = {0,1,0,-1};
        for (int start = 0; start < sw*sh; start++) {
            if (!mask[start] || label[start] >= 0) continue;
            int id = comps.Count;
            int x0 = int.MaxValue, y0 = int.MaxValue, x1 = -1, y1 = -1, cnt = 0;
            var q = new Queue<int>();
            q.Enqueue(start); label[start] = id;
            while (q.Count > 0) {
                int cur = q.Dequeue();
                int cx2 = cur % sw, cy2 = cur / sw;
                x0 = Math.Min(x0, cx2); x1 = Math.Max(x1, cx2);
                y0 = Math.Min(y0, cy2); y1 = Math.Max(y1, cy2);
                cnt++;
                for (int d = 0; d < 4; d++) {
                    int nx = cx2 + ddx[d], ny = cy2 + ddy[d];
                    if (nx < 0 || ny < 0 || nx >= sw || ny >= sh) continue;
                    int ni = ny*sw+nx;
                    if (mask[ni] && label[ni] < 0) { label[ni] = id; q.Enqueue(ni); }
                }
            }
            comps.Add(new int[] { x0*step, y0*step, (x1+1)*step-1, (y1+1)*step-1, cnt });
        }
        // 合并重叠的 bbox(同一圆被分割的情况)
        var merged = new List<int[]>();
        var used = new bool[comps.Count];
        for (int i = 0; i < comps.Count; i++) {
            if (used[i] || comps[i][4] < 300) continue;
            int bx0 = comps[i][0], by0 = comps[i][1], bx1 = comps[i][2], by1 = comps[i][3];
            for (int j = i + 1; j < comps.Count; j++) {
                if (used[j] || comps[j][4] < 300) continue;
                int ox0 = Math.Max(bx0, comps[j][0]), oy0 = Math.Max(by0, comps[j][1]);
                int ox1 = Math.Min(bx1, comps[j][2]), oy1 = Math.Min(by1, comps[j][3]);
                if (ox1 <= ox0 || oy1 <= oy0) continue;
                double inter = (ox1-ox0)*(oy1-oy0);
                double area = (bx1-bx0)*(by1-by0) + (comps[j][2]-comps[j][0])*(comps[j][3]-comps[j][1]) - inter;
                if (inter / area > 0.3) {
                    used[j] = true;
                    bx0 = Math.Min(bx0, comps[j][0]); by0 = Math.Min(by0, comps[j][1]);
                    bx1 = Math.Max(bx1, comps[j][2]); by1 = Math.Max(by1, comps[j][3]);
                }
            }
            used[i] = true;
            merged.Add(new int[] { bx0, by0, bx1, by1 });
        }
        // 按 y 排序(同 y 再按 x),保证填入顺序稳定:从上到下、从左到右
        merged.Sort((a, b) => {
            int c = a[1].CompareTo(b[1]);
            return c != 0 ? c : a[0].CompareTo(b[0]);
        });
        sb.AppendLine(string.Format("detected {0} slots:", merged.Count));

        var slots = new List<double[]>();
        foreach (var m in merged) {
            double cx, cy, r;
            int pad = 6;
            if (FitCircle(dp, dw, dh, 60, m[0]-pad, m[1]-pad, m[2]+pad, m[3]+pad, false, out cx, out cy, out r)) {
                if (r < 300) continue;   // 过滤照片内部的小元素
                slots.Add(new double[] { cx, cy, r });
                sb.AppendLine(string.Format("  slot center=({0:F1},{1:F1}) r={2:F1} d={3:F1}", cx, cy, r, 2*r));
            }
        }
        sb.AppendLine(string.Format("fitted {0} circles", slots.Count));

        // 2) 底图(按文件名自然排序,按此顺序每 11 张排一页)
        var baseFiles = new List<string>(Directory.GetFiles(Path.Combine(root, baseDir), "*.*"));
        baseFiles.Sort((a, b) => StrCmpLogicalW(a, b));
        sb.AppendLine(string.Format("base files: {0}", baseFiles.Count));

        // 3) 输出目录(清空旧的 PNG 结果,避免残留旧页)
        var outPath = Path.Combine(root, outDir);
        Directory.CreateDirectory(outPath);
        foreach (var old in Directory.GetFiles(outPath, "*.png")) {
            try { File.Delete(old); } catch { }
        }

        // 预载入所有底图及其 alpha 包围盒
        var infos = new List<BaseInfo>();
        foreach (var bf in baseFiles) {
            string ext = Path.GetExtension(bf).ToLower();
            if (ext != ".png" && ext != ".jpg" && ext != ".jpeg" && ext != ".bmp" && ext != ".gif") continue;
            int bw, bh;
            var bp = LoadArgb(bf, out bw, out bh);
            // 徽章圆形区域:用 alpha 包围盒定位(更稳,避免轻微不对称被弦长法误判)
            int minx = bw, maxx = -1, miny = bh, maxy = -1;
            for (int y = 0; y < bh; y++) for (int x = 0; x < bw; x++) {
                if (bp[(y*bw+x)*4+3] > 16) {
                    if (x < minx) minx = x;
                    if (x > maxx) maxx = x;
                    if (y < miny) miny = y;
                    if (y > maxy) maxy = y;
                }
            }
            if (maxx < minx) {
                sb.AppendLine(string.Format("SKIP {0}: no alpha content", Path.GetFileName(bf)));
                continue;
            }
            double bcx = (minx + maxx) / 2.0, bcy = (miny + maxy) / 2.0;
            double br = Math.Max(maxx - minx + 1, maxy - miny + 1) / 2.0;
            sb.AppendLine(string.Format("base {0}: circle center=({1:F1},{2:F1}) r={3:F1}", Path.GetFileName(bf), bcx, bcy, br));
            infos.Add(new BaseInfo { Path = bf, Src = new Bitmap(bf), MinX = minx, MinY = miny, MaxX = maxx, MaxY = maxy, Br = br });
        }
        if (infos.Count == 0) { sb.AppendLine("no valid base images"); return sb.ToString(); }

        // 每页槽位数 = demo 检测出的槽位(当前 11 个),每 11 张底图排一页,最后一页不足的槽位留白
        int perPage = slots.Count;
        int totalPages = (int)Math.Ceiling((double)infos.Count / perPage);
        sb.AppendLine(string.Format("pages: {0} ({1} per page)", totalPages, perPage));
        for (int p = 0; p < totalPages; p++) {
            using (var canvas = new Bitmap(dw, dh, PixelFormat.Format32bppArgb))
            using (var g = Graphics.FromImage(canvas)) {
                g.Clear(Color.White);
                g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                g.SmoothingMode = SmoothingMode.HighQuality;
                g.CompositingMode = CompositingMode.SourceOver;
                for (int i = 0; i < perPage; i++) {
                    int idx = p * perPage + i;
                    if (idx >= infos.Count) break;   // 多余的槽位留白
                    var bi = infos[idx];
                    var s = slots[i];
                    double scx = s[0], scy = s[1], sr = s[2];
                    var dest = new RectangleF((float)(scx - sr - 1), (float)(scy - sr - 1), (float)(2*sr + 2), (float)(2*sr + 2));
                    var srcR = new RectangleF((float)(bi.MinX - 1), (float)(bi.MinY - 1), (float)(bi.MaxX - bi.MinX + 3), (float)(bi.MaxY - bi.MinY + 3));
                    g.DrawImage(bi.Src, dest, srcR, GraphicsUnit.Pixel);
                    sb.AppendLine(string.Format("  p{0} slot#{1,2} ({2:F0},{3:F0}) <- {4}", p + 1, i + 1, scx, scy, Path.GetFileName(bi.Path)));
                }
                string outName = string.Format("第{0}页.png", p + 1);
                canvas.Save(Path.Combine(outPath, outName), ImageFormat.Png);
                sb.AppendLine(string.Format("  -> {0}", Path.Combine(outDir, outName)));
            }
        }
        foreach (var bi in infos) bi.Src.Dispose();
        return sb.ToString();
    }
}
"@
Add-Type -TypeDefinition $code -Language CSharp -ReferencedAssemblies @("System.Drawing")

$out = [Layout2]::Run((Join-Path $root $Demo), $BaseDir, $OutDir, $root)
Set-Content -LiteralPath (Join-Path $root "_layout_log.txt") -Value $out -Encoding UTF8
Write-Output $out
