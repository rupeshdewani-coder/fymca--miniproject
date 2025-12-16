@echo off
title allercheck Database Setup

echo ==========================================
echo   allercheck Database Setup
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

echo XAMPP found. Checking services...
echo.

REM Check if MySQL is configured to use port 3307
echo Checking MySQL configuration...
findstr /C:"port=3307" "C:\xampp\mysql\bin\my.ini" >nul 2>&1
if %errorlevel% == 0 (
    echo MySQL is configured to use port 3307.
) else (
    echo MySQL is not configured to use port 3307.
    echo.
    echo Please update your MySQL configuration:
    echo 1. Open C:\xampp\mysql\bin\my.ini
    echo 2. Change port=3306 to port=3307
    echo 3. Restart MySQL service
    echo.
    echo Press any key to continue anyway (database may not work)...
    pause >nul
)

echo.
echo Starting MySQL service...
net start mysql >nul 2>&1
if %errorlevel% == 0 (
    echo MySQL service started successfully.
) else (
    echo MySQL service is already running or failed to start.
    echo Please check XAMPP Control Panel to ensure MySQL is running.
)

echo.
echo Creating database and tables...
echo.

REM Create database using MySQL command line with port 3307
echo CREATE DATABASE IF NOT EXISTS allercheck; USE allercheck; > temp_sql.sql
type database_schema.sql >> temp_sql.sql

"C:\xampp\mysql\bin\mysql.exe" -u root -P 3307 -e "source temp_sql.sql" 2>nul

if %errorlevel% == 0 (
    echo Database and tables created successfully!
    echo.
    echo Database name: allercheck
    echo Username: root
    echo Password: (empty)
    echo Port: 3307
) else (
    echo.
    echo WARNING: Failed to create database using command line.
    echo.
    echo Please follow these steps manually:
    echo 1. Open XAMPP Control Panel
    echo 2. Start Apache and MySQL services
    echo 3. Configure MySQL to use port 3307
    echo 4. Open phpMyAdmin at http://localhost/phpmyadmin
    echo 5. Create a database named "allercheck"
    echo 6. Import the "database_schema.sql" file
)

echo.
del temp_sql.sql >nul 2>&1
echo Setup complete!
echo.
echo To start the allercheck application:
echo 1. Run "start-server.bat"
echo 2. Open your browser and go to http://localhost:8080
echo.
pause