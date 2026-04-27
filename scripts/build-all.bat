@echo off
REM Build both Debug and Release versions of GotIt
echo ============================================
echo  GotIt Full Build (Debug + Release)
echo ============================================

echo.
echo === Building Debug version ===
call "%~dp0build-debug.bat"
if %ERRORLEVEL% neq 0 (
    echo FAILED: Debug build failed
    exit /b 1
)

echo.
echo === Building Release version ===
call "%~dp0build-release.bat"
if %ERRORLEVEL% neq 0 (
    echo FAILED: Release build failed
    exit /b 1
)

echo.
echo ============================================
echo  All builds complete!
echo  Debug:   frontend\src-tauri\target\debug\
echo  Release: frontend\src-tauri\target\release\bundle\nsis\
echo ============================================
