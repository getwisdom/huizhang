@echo off
chcp 65001 >nul
cd /d %~dp0
echo ============================================
echo  豆包去水印 -^> 抠图 一键流程
echo ============================================
echo.
echo  1. 用豆包处理「原图」文件夹里的图片（消除水印）
echo  2. 把豆包导出的图片放进「doubao」文件夹
echo  3. 双击本脚本（或直接继续）自动抠图
echo.
echo  输出：无水印底图（透明背景 PNG）
echo ============================================
echo.
powershell -ExecutionPolicy Bypass -File cut_badge.ps1 -InputDir "doubao" -OutputDir "无水印底图"
echo.
echo 完成！结果在「无水印底图」文件夹
pause
