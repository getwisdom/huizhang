// 排版工具.cs —— 徽章排版工具(编译为 排版工具.exe)
// 把 底图\*.png 按 排版demo.png 自动识别的圆形槽位排版,每 11 张一页,输出 已排版\第N页.png
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

class LayoutTool
{
    [DllImport("shlwapi.dll", CharSet = CharSet.Unicode)]
    static extern int StrCmpLogicalW(string x, string y);

    class BaseInfo
    {
        public string Path;
        public Bitmap Src;
        public int MinX, MinY, MaxX, MaxY;
    }

    static byte[] LoadRgb(string path, out int w, out int h)
    {
        using (var b = new Bitmap(path))
        {
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

    static byte[] LoadArgb(string path, out int w, out int h)
    {
        using (var b = new Bitmap(path))
        {
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
    static bool FitCircle(byte[] px, int w, int h, int thr, int x0, int y0, int x1, int y1,
                          out double cx, out double cy, out double r)
    {
        cx = 0; cy = 0; r = 0;
        x0 = Math.Max(0, x0); y0 = Math.Max(0, y0);
        x1 = Math.Min(w - 1, x1); y1 = Math.Min(h - 1, y1);
        double cx0 = (x0 + x1) / 2.0, cy0 = (y0 + y1) / 2.0;
        int yc = (int)Math.Round(cy0);
        int hFirst = -1, hLast = -1;
        for (int x = x0; x <= x1; x++)
        {
            int i = (yc * w + x) * 3;
            if (Math.Abs(px[i] - 255) + Math.Abs(px[i + 1] - 255) + Math.Abs(px[i + 2] - 255) > thr)
            { if (hFirst < 0) hFirst = x; hLast = x; }
        }
        int xc = (int)Math.Round(cx0);
        int vFirst = -1, vLast = -1;
        for (int y = y0; y <= y1; y++)
        {
            int i = (y * w + xc) * 3;
            if (Math.Abs(px[i] - 255) + Math.Abs(px[i + 1] - 255) + Math.Abs(px[i + 2] - 255) > thr)
            { if (vFirst < 0) vFirst = y; vLast = y; }
        }
        if (hFirst < 0 || vFirst < 0) return false;
        double wh = hLast - hFirst + 1, wv = vLast - vFirst + 1;
        cx = (hFirst + hLast) / 2.0;
        cy = (vFirst + vLast) / 2.0;
        r = Math.Max(wh, wv) / 2.0;
        return r > 10;
    }

    static void Run(string demoPath, string baseDir, string outDir, StringBuilder sb)
    {
        if (!File.Exists(demoPath)) throw new Exception("找不到模板文件 排版demo.png");
        if (!Directory.Exists(baseDir)) throw new Exception("找不到输入文件夹 底图");

        int dw, dh;
        var dp = LoadRgb(demoPath, out dw, out dh);
        sb.AppendLine(string.Format("模板: {0}x{1}", dw, dh));

        // 1) 连通域找槽位(step=4)
        int step = 4;
        int sw = dw / step, sh = dh / step;
        var mask = new bool[sw * sh];
        for (int y = 0; y < sh; y++) for (int x = 0; x < sw; x++)
        {
            int i = (y * step * dw + x * step) * 3;
            int d = Math.Abs(dp[i] - 255) + Math.Abs(dp[i + 1] - 255) + Math.Abs(dp[i + 2] - 255);
            mask[y * sw + x] = d > 60;
        }
        var label = new int[sw * sh];
        for (int i = 0; i < label.Length; i++) label[i] = -1;
        var comps = new List<int[]>();
        int[] ddx = { 1, 0, -1, 0 }, ddy = { 0, 1, 0, -1 };
        for (int start = 0; start < sw * sh; start++)
        {
            if (!mask[start] || label[start] >= 0) continue;
            int id = comps.Count;
            int x0 = int.MaxValue, y0 = int.MaxValue, x1 = -1, y1 = -1, cnt = 0;
            var q = new Queue<int>();
            q.Enqueue(start); label[start] = id;
            while (q.Count > 0)
            {
                int cur = q.Dequeue();
                int cx2 = cur % sw, cy2 = cur / sw;
                x0 = Math.Min(x0, cx2); x1 = Math.Max(x1, cx2);
                y0 = Math.Min(y0, cy2); y1 = Math.Max(y1, cy2);
                cnt++;
                for (int d = 0; d < 4; d++)
                {
                    int nx = cx2 + ddx[d], ny = cy2 + ddy[d];
                    if (nx < 0 || ny < 0 || nx >= sw || ny >= sh) continue;
                    int ni = ny * sw + nx;
                    if (mask[ni] && label[ni] < 0) { label[ni] = id; q.Enqueue(ni); }
                }
            }
            comps.Add(new int[] { x0 * step, y0 * step, (x1 + 1) * step - 1, (y1 + 1) * step - 1, cnt });
        }
        // 合并重叠的 bbox(同一圆被分割的情况)
        var merged = new List<int[]>();
        var used = new bool[comps.Count];
        for (int i = 0; i < comps.Count; i++)
        {
            if (used[i] || comps[i][4] < 300) continue;
            int bx0 = comps[i][0], by0 = comps[i][1], bx1 = comps[i][2], by1 = comps[i][3];
            for (int j = i + 1; j < comps.Count; j++)
            {
                if (used[j] || comps[j][4] < 300) continue;
                int ox0 = Math.Max(bx0, comps[j][0]), oy0 = Math.Max(by0, comps[j][1]);
                int ox1 = Math.Min(bx1, comps[j][2]), oy1 = Math.Min(by1, comps[j][3]);
                if (ox1 <= ox0 || oy1 <= oy0) continue;
                double inter = (ox1 - ox0) * (oy1 - oy0);
                double area = (bx1 - bx0) * (by1 - by0) + (comps[j][2] - comps[j][0]) * (comps[j][3] - comps[j][1]) - inter;
                if (inter / area > 0.3)
                {
                    used[j] = true;
                    bx0 = Math.Min(bx0, comps[j][0]); by0 = Math.Min(by0, comps[j][1]);
                    bx1 = Math.Max(bx1, comps[j][2]); by1 = Math.Max(by1, comps[j][3]);
                }
            }
            used[i] = true;
            merged.Add(new int[] { bx0, by0, bx1, by1 });
        }
        // 按 y 排序(同 y 再按 x),保证填入顺序稳定:从上到下、从左到右
        merged.Sort((a, b) =>
        {
            int c = a[1].CompareTo(b[1]);
            return c != 0 ? c : a[0].CompareTo(b[0]);
        });

        var slots = new List<double[]>();
        foreach (var m in merged)
        {
            double cx, cy, r;
            int pad = 6;
            if (FitCircle(dp, dw, dh, 60, m[0] - pad, m[1] - pad, m[2] + pad, m[3] + pad, out cx, out cy, out r))
            {
                if (r < 300) continue;   // 过滤照片内部的小元素
                slots.Add(new double[] { cx, cy, r });
            }
        }
        sb.AppendLine(string.Format("识别到 {0} 个槽位", slots.Count));
        if (slots.Count == 0) throw new Exception("模板上没有识别到圆形槽位,请检查 排版demo.png");

        // 2) 底图(按文件名自然排序,按此顺序每页填充)
        var baseFiles = new List<string>(Directory.GetFiles(baseDir, "*.*"));
        baseFiles.Sort((a, b) => StrCmpLogicalW(a, b));

        var infos = new List<BaseInfo>();
        foreach (var bf in baseFiles)
        {
            string ext = Path.GetExtension(bf).ToLower();
            if (ext != ".png" && ext != ".jpg" && ext != ".jpeg" && ext != ".bmp" && ext != ".gif") continue;
            int bw, bh;
            var bp = LoadArgb(bf, out bw, out bh);
            // 徽章圆形区域:用 alpha 包围盒定位
            int minx = bw, maxx = -1, miny = bh, maxy = -1;
            for (int y = 0; y < bh; y++) for (int x = 0; x < bw; x++)
            {
                if (bp[(y * bw + x) * 4 + 3] > 16)
                {
                    if (x < minx) minx = x;
                    if (x > maxx) maxx = x;
                    if (y < miny) miny = y;
                    if (y > maxy) maxy = y;
                }
            }
            if (maxx < minx) continue;   // 无透明区域,跳过
            infos.Add(new BaseInfo { Path = bf, Src = new Bitmap(bf), MinX = minx, MinY = miny, MaxX = maxx, MaxY = maxy });
        }
        sb.AppendLine(string.Format("底图数量: {0}", infos.Count));
        if (infos.Count == 0) throw new Exception("底图文件夹里没有可用图片");

        // 3) 输出目录(清空旧的 PNG 结果,避免残留旧页)
        Directory.CreateDirectory(outDir);
        foreach (var old in Directory.GetFiles(outDir, "*.png"))
        {
            try { File.Delete(old); } catch { }
        }

        // 每页槽位数 = 模板识别出的槽位(当前 11 个),每 11 张底图排一页,最后一页不足的槽位留白
        int perPage = slots.Count;
        int totalPages = (int)Math.Ceiling((double)infos.Count / perPage);
        sb.AppendLine(string.Format("共 {0} 页(每页 {1} 个槽位)", totalPages, perPage));
        for (int p = 0; p < totalPages; p++)
        {
            using (var canvas = new Bitmap(dw, dh, PixelFormat.Format32bppArgb))
            using (var g = Graphics.FromImage(canvas))
            {
                g.Clear(Color.White);
                g.InterpolationMode = InterpolationMode.HighQualityBicubic;
                g.PixelOffsetMode = PixelOffsetMode.HighQuality;
                g.SmoothingMode = SmoothingMode.HighQuality;
                g.CompositingMode = CompositingMode.SourceOver;
                for (int i = 0; i < perPage; i++)
                {
                    int idx = p * perPage + i;
                    if (idx >= infos.Count) break;   // 多余的槽位留白
                    var bi = infos[idx];
                    var s = slots[i];
                    double scx = s[0], scy = s[1], sr = s[2];
                    var dest = new RectangleF((float)(scx - sr - 1), (float)(scy - sr - 1), (float)(2 * sr + 2), (float)(2 * sr + 2));
                    var srcR = new RectangleF((float)(bi.MinX - 1), (float)(bi.MinY - 1), (float)(bi.MaxX - bi.MinX + 3), (float)(bi.MaxY - bi.MinY + 3));
                    g.DrawImage(bi.Src, dest, srcR, GraphicsUnit.Pixel);
                }
                string outName = string.Format("第{0}页.png", p + 1);
                canvas.Save(Path.Combine(outDir, outName), ImageFormat.Png);
                sb.AppendLine(string.Format("  已生成 {0}", Path.Combine(outDir, outName)));
            }
        }
        foreach (var bi in infos) bi.Src.Dispose();
    }

    static int Main(string[] args)
    {
        Console.Title = "徽章排版工具";
        string root = Path.GetDirectoryName(System.Reflection.Assembly.GetExecutingAssembly().Location);
        var sb = new StringBuilder();
        sb.AppendLine("======== 徽章排版工具 ========");
        sb.AppendLine("模板: 排版demo.png   输入: 底图\\*.png   输出: 已排版\\第N页.png");
        sb.AppendLine();
        try
        {
            Run(Path.Combine(root, "排版demo.png"), Path.Combine(root, "底图"), Path.Combine(root, "已排版"), sb);
            sb.AppendLine();
            sb.AppendLine("完成。请打开「已排版」文件夹查看结果。");
        }
        catch (Exception ex)
        {
            sb.AppendLine("错误: " + ex.Message);
        }
        try { File.WriteAllText(Path.Combine(root, "排版日志.txt"), sb.ToString(), new UTF8Encoding(true)); } catch { }
        Console.WriteLine(sb.ToString());
        if (!Console.IsOutputRedirected)
        {
            Console.WriteLine("按任意键退出...");
            try { Console.ReadKey(true); } catch { }
        }
        return 0;
    }
}
