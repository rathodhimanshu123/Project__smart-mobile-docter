@echo off
echo Building Smart Mobile Doctor APK...
echo.

cd app

echo Cleaning previous build...
call gradlew clean

echo Building APK...
call gradlew assembleDebug

if %ERRORLEVEL% EQU 0 (
    echo.
    echo APK built successfully!
    echo Location: app\build\outputs\apk\debug\app-debug.apk
    echo.
    echo To install on your phone:
    echo 1. Enable "Developer options" and "USB debugging" on your phone
    echo 2. Connect phone via USB or transfer the APK file
    echo 3. Install the APK file
    echo 4. Grant permissions when prompted
    echo.
    echo Then scan the QR code and tap the "Open App" link for full device details!
) else (
    echo.
    echo Build failed! Please check the error messages above.
)

pause 