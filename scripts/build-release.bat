@echo off
REM Build GotIt — Release version (ERROR-only logging)
echo ============================================
echo  GotIt Release Build
echo  - Python backend: ERROR level logs only
echo  - Tauri/Rust: ERROR level logs only
echo ============================================

cd /d "%~dp0..\frontend"

echo.
echo [1/2] Building frontend...
call npm run build
if %ERRORLEVEL% neq 0 (
    echo FAILED: Frontend build failed
    exit /b 1
)

echo.
echo [2/2] Building Tauri app (release)...
call npx tauri build
if %ERRORLEVEL% neq 0 (
    echo FAILED: Tauri build failed
    exit /b 1
)

echo.
echo ============================================
echo  Release build complete!
echo  Output: frontend\src-tauri\target\release\
echo  Installer: frontend\src-tauri\target\release\bundle\nsis\
echo ============================================
