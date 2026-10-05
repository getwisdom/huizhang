// 徽章抠图工具 - 图形界面版
// 编译: C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /target:winexe /optimize+ /out:徽章抠图.exe /r:System.Windows.Forms.dll /r:System.Drawing.dll 抠图工具.cs
// 命令行: 徽章抠图.exe --batch   （无界面批量处理，日志写入 运行日志.txt）
using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace BadgeCutterApp
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            if (args.Length > 0 && args[0] == "--batch")
            {
                Environment.ExitCode = BatchRunner.Run();
                return;
            }
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }
    }

    // ==================== 核心算法 ====================
    static class BadgeCutter
    {
        struct Pt { public double x, y; }

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
                double sumR = 0; int nr = 0;
                for (int i = 0; i < n; i++)
                {
                    if (!use[i]) continue;
                    sumR += Math.Sqrt((xa[i] - cx) * (xa[i] - cx) + (ya[i] - cy) * (ya[i] - cy));
                    nr++;
                }
                if (nr > 0) r = sumR / nr;
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

        public static string Process(string input, string output, double scanT, int feather, int margin)
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

                // 水平线扫描
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

                // 垂直线扫描
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

                // RANSAC 圆拟合
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

                // 最小二乘精修
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
                    double minDim2 = Math.Min(w, h);
                    if (fr >= minDim2 * 0.08 && fr <= minDim2 * 0.75 && fcx > 0 && fcy > 0 && fcx < w && fcy < h)
                    { bestCx = fcx; bestCy = fcy; bestR = fr; bestIn = fIn; }
                }

                // 圆内全部保留，圆边缘羽化
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
                return "OK " + cw + "x" + ch + " 圆心(" + Math.Round(bestCx, 0) + "," + Math.Round(bestCy, 0) + ") 半径" + Math.Round(bestR, 0);
            }
        }
    }

    // ==================== 批处理逻辑 ====================
    static class BatchRunner
    {
        public static string InDir { get { return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "原图"); } }
        public static string OutDir { get { return Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "底图"); } }

        public static string[] ListFiles(string inDir)
        {
            string[] exts = new string[] { "*.jpg", "*.jpeg", "*.png", "*.bmp", "*.gif", "*.tif", "*.tiff" };
            var list = new List<string>();
            foreach (string e in exts)
            {
                try { list.AddRange(Directory.GetFiles(inDir, e)); }
                catch { }
            }
            list.Sort(StringComparer.OrdinalIgnoreCase);
            return list.ToArray();
        }

        // 返回日志文本；outFiles 为生成的文件列表
        public static string RunAll(double scanT, int feather, int margin, out int ok, out int fail, out string[] outFiles)
        {
            var log = new StringBuilder();
            ok = 0; fail = 0;
            var files = ListFiles(InDir);
            var made = new List<string>();
            log.AppendLine("徽章抠图工具");
            log.AppendLine("原图: " + InDir + " (" + files.Length + " 张)");
            log.AppendLine("输出: " + OutDir);
            log.AppendLine("参数: 扫描阈值=" + scanT + "  羽化=" + feather + "px  边距=" + margin + "px");
            log.AppendLine("------------------------------");
            foreach (string f in files)
            {
                string outPath = Path.Combine(OutDir, Path.GetFileNameWithoutExtension(f) + ".png");
                string r = BadgeCutter.Process(f, outPath, scanT, feather, margin);
                if (r.StartsWith("ERR"))
                {
                    log.AppendLine("[失败] " + Path.GetFileName(f) + "  " + r);
                    fail++;
                }
                else
                {
                    log.AppendLine("[完成] " + Path.GetFileName(f) + " -> " + Path.GetFileName(outPath) + "  (" + r + ")");
                    made.Add(outPath);
                    ok++;
                }
            }
            log.AppendLine("------------------------------");
            log.AppendLine("全部完成：成功 " + ok + " 张，失败 " + fail + " 张");
            outFiles = made.ToArray();
            return log.ToString();
        }

        // 无界面模式：--batch
        public static int Run()
        {
            try
            {
                if (!Directory.Exists(InDir)) Directory.CreateDirectory(InDir);
                if (!Directory.Exists(OutDir)) Directory.CreateDirectory(OutDir);
                int ok, fail; string[] made;
                string log = RunAll(45, 4, 4, out ok, out fail, out made);
                File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "运行日志.txt"), log, new UTF8Encoding(true));
                return fail == 0 ? 0 : 1;
            }
            catch (Exception e)
            {
                try { File.WriteAllText(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "运行日志.txt"), "发生错误: " + e, new UTF8Encoding(true)); } catch { }
                return 2;
            }
        }
    }

    // ==================== 主界面 ====================
    class MainForm : Form
    {
        TextBox logBox;
        Button btnRun;
        Label statusLabel;
        NumericUpDown numScanT, numFeather;
        bool running = false;

        public MainForm()
        {
            Text = "徽章抠图工具";
            ClientSize = new Size(660, 560);
            StartPosition = FormStartPosition.CenterScreen;
            FormBorderStyle = FormBorderStyle.FixedSingle;
            MaximizeBox = false;
            Font = new Font("Microsoft YaHei UI", 9F);

            var title = new Label();
            title.Text = "徽章抠图工具";
            title.Font = new Font("Microsoft YaHei UI", 15F, FontStyle.Bold);
            title.TextAlign = ContentAlignment.MiddleCenter;
            title.Dock = DockStyle.Top;
            title.Height = 46;

            var tip = new Label();
            tip.Text = "自动识别图片中间的圆形徽章并抠出透明 PNG";
            tip.TextAlign = ContentAlignment.MiddleCenter;
            tip.ForeColor = Color.Gray;
            tip.Dock = DockStyle.Top;
            tip.Height = 22;

            // 设置区
            var box = new GroupBox();
            box.Text = "设置";
            box.Dock = DockStyle.Top;
            box.Height = 130;
            box.Padding = new Padding(10);

            var lIn = new Label(); lIn.Text = "原图文件夹:"; lIn.Location = new Point(14, 26); lIn.AutoSize = true;
            var tIn = new TextBox(); tIn.Text = BatchRunner.InDir; tIn.ReadOnly = true;
            tIn.Location = new Point(100, 23); tIn.Width = 530; tIn.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;

            var lOut = new Label(); lOut.Text = "输出文件夹:"; lOut.Location = new Point(14, 56); lOut.AutoSize = true;
            var tOut = new TextBox(); tOut.Text = BatchRunner.OutDir; tOut.ReadOnly = true;
            tOut.Location = new Point(100, 53); tOut.Width = 530; tOut.Anchor = AnchorStyles.Top | AnchorStyles.Left | AnchorStyles.Right;

            var lScan = new Label(); lScan.Text = "扫描阈值:"; lScan.Location = new Point(14, 92); lScan.AutoSize = true;
            numScanT = new NumericUpDown(); numScanT.Minimum = 10; numScanT.Maximum = 200; numScanT.Value = 45;
            numScanT.Location = new Point(100, 89); numScanT.Width = 80;

            var lFeather = new Label(); lFeather.Text = "羽化宽度(px):"; lFeather.Location = new Point(210, 92); lFeather.AutoSize = true;
            numFeather = new NumericUpDown(); numFeather.Minimum = 0; numFeather.Maximum = 20; numFeather.Value = 4;
            numFeather.Location = new Point(300, 89); numFeather.Width = 80;

            var lHint = new Label(); lHint.Text = "把图片放入「原图」文件夹后点击开始；结果输出到「底图」文件夹。";
            lHint.ForeColor = Color.Gray; lHint.Location = new Point(400, 92); lHint.AutoSize = true;

            box.Controls.Add(lIn); box.Controls.Add(tIn);
            box.Controls.Add(lOut); box.Controls.Add(tOut);
            box.Controls.Add(lScan); box.Controls.Add(numScanT);
            box.Controls.Add(lFeather); box.Controls.Add(numFeather);
            box.Controls.Add(lHint);

            btnRun = new Button();
            btnRun.Text = "开 始 抠 图";
            btnRun.Font = new Font("Microsoft YaHei UI", 12F, FontStyle.Bold);
            btnRun.Dock = DockStyle.Top;
            btnRun.Height = 44;
            btnRun.Click += delegate { StartRun(); };

            logBox = new TextBox();
            logBox.Multiline = true;
            logBox.ReadOnly = true;
            logBox.ScrollBars = ScrollBars.Vertical;
            logBox.BackColor = Color.White;
            logBox.Dock = DockStyle.Fill;
            logBox.Text = "等待开始……" + Environment.NewLine;

            statusLabel = new Label();
            statusLabel.Text = "就绪";
            statusLabel.Dock = DockStyle.Bottom;
            statusLabel.Height = 24;
            statusLabel.TextAlign = ContentAlignment.MiddleLeft;
            statusLabel.Padding = new Padding(6, 0, 0, 0);

            Controls.Add(logBox);
            Controls.Add(statusLabel);
            Controls.Add(btnRun);
            Controls.Add(box);
            Controls.Add(tip);
            Controls.Add(title);
        }

        void Log(string s)
        {
            if (logBox.InvokeRequired)
            {
                try { logBox.BeginInvoke((Action)(delegate { Log(s); })); } catch { }
                return;
            }
            logBox.AppendText(s + Environment.NewLine);
        }

        void SetStatus(string s)
        {
            if (statusLabel.InvokeRequired)
            {
                try { statusLabel.BeginInvoke((Action)(delegate { SetStatus(s); })); } catch { }
                return;
            }
            statusLabel.Text = s;
        }

        void StartRun()
        {
            if (running) return;
            running = true;
            btnRun.Enabled = false;
            logBox.Text = "";
            double scanT = (double)numScanT.Value;
            int feather = (int)numFeather.Value;

            Task.Factory.StartNew(delegate
            {
                try
                {
                    if (!Directory.Exists(BatchRunner.InDir)) Directory.CreateDirectory(BatchRunner.InDir);
                    if (!Directory.Exists(BatchRunner.OutDir)) Directory.CreateDirectory(BatchRunner.OutDir);
                    int ok, fail; string[] made;
                    string log = BatchRunner.RunAll(scanT, feather, 4, out ok, out fail, out made);
                    Log(log);
                    SetStatus("完成：成功 " + ok + " 张，失败 " + fail + " 张");
                    string msg = "处理完成：成功 " + ok + " 张，失败 " + fail + " 张。\n\n是否打开输出文件夹？";
                    var dlg = MessageBox.Show(msg, "徽章抠图工具", MessageBoxButtons.YesNo, MessageBoxIcon.Information);
                    if (dlg == DialogResult.Yes)
                    {
                        try { System.Diagnostics.Process.Start(BatchRunner.OutDir); } catch { }
                    }
                }
                catch (Exception e)
                {
                    Log("发生错误: " + e.Message);
                    SetStatus("出错");
                }
                finally
                {
                    running = false;
                    if (btnRun.InvokeRequired) { try { btnRun.BeginInvoke((Action)(delegate { btnRun.Enabled = true; })); } catch { } }
                    else btnRun.Enabled = true;
                }
            });
        }
    }
}
