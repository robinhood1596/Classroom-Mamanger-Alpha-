@echo off
echo ============================================
echo   Building Classroom Overlay
echo ============================================
echo.

echo [1/3] Installing dependencies...
pip install pyinstaller -q
pip install -r requirements.txt -q
echo.

echo [2/3] Building executable...
pyinstaller overlay.spec --noconfirm
echo.

echo [3/3] Copying data files...
if not exist "dist\Classroom Overlay\classes" mkdir "dist\Classroom Overlay\classes"
if not exist "dist\Classroom Overlay\sounds" mkdir "dist\Classroom Overlay\sounds"
if not exist "dist\Classroom Overlay\layouts" mkdir "dist\Classroom Overlay\layouts"
if not exist "dist\Classroom Overlay\symbols" mkdir "dist\Classroom Overlay\symbols"

rem Copy sound files
if exist sounds\*.wav xcopy /Y /Q sounds\*.wav "dist\Classroom Overlay\sounds\" >nul 2>&1

rem Copy example class file (optional)
if exist classes\*.json xcopy /Y /Q classes\*.json "dist\Classroom Overlay\classes\" >nul 2>&1

echo.
echo ============================================
echo   Build complete!
echo   Output: dist\Classroom Overlay\
echo   Run:    dist\Classroom Overlay\Classroom Overlay.exe
echo ============================================
pause
