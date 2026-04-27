@echo off
REM Build GotIt — Debug version (with full logging)
echo ============================================
echo  GotIt Debug Build
echo  - Python backend: INFO level logs
echo  - Tauri/Rust: INFO level logs
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
echo [2/2] Building Tauri app (debug)...
call npx tauri build --debug
if %ERRORLEVEL% neq 0 (
    echo FAILED: Tauri build failed
    exit /b 1
)

echo.
echo ============================================
echo  Debug build complete!
echo  Output: frontend\src-tauri\target\debug\
echo ============================================
