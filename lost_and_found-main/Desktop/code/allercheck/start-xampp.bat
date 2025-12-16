@echo off
title allercheck XAMPP Starter

echo ==========================================
echo   allercheck Application Starter
echo ==========================================
echo.

REM Check if XAMPP is installed
if not exist "C:\xampp\xampp-control.exe" (
    echo ERROR: XAMPP not found at C:\xampp\
    echo Please install XAMPP first and try again.
    echo.
    pause
    exit /b
)

echo XAMPP found. Starting services...
echo.

REM Start Apache and MySQL services
echo Starting Apache and MySQL services...
echo.

net start apache >nul 2>&1
if %errorlevel% == 0 (
    echo Apache service started successfully.
) else (
    echo Apache service is already running or failed to start.
    echo Please check XAMPP Control Panel to ensure Apache is running.
)

net start mysql >nul 2>&1
if %errorlevel% == 0 (
    echo MySQL service started successfully.
) else (
    echo MySQL service is already running or failed to start.
    echo Please check XAMPP Control Panel to ensure MySQL is running.
)

echo.
echo Services started. Please ensure:
echo 1. MySQL is configured to use port 3307
echo 2. Database is set up (run setup-database.bat if needed)
echo.
echo Access the application at http://localhost/allercheck
echo.
echo To stop services, close this window and use XAMPP Control Panel.
echo.
pause