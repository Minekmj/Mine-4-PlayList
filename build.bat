@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo [1/5] PyInstaller 빌드 중...
pyinstaller -w -n "Mine 4 PlayList" -i "./src/icon/icon.ico" --add-data "./src/icon/icon.ico;src/icon" --add-data "./src/C/ambient_core.dll;src/C" --add-data "./src/qss/main.qss;src/qss" --add-data "./src/qss/dialog.qss;src/qss" main.py

set "OUTPUT_DIR=dist\Mine 4 PlayList"

if not exist "%OUTPUT_DIR%" (
    echo [오류] 빌드 결과물 폴더를 찾을 수 없습니다: %OUTPUT_DIR%
    goto END
)

echo [2/5] updater.exe 복사 중...
if not exist "src\updater" mkdir "src\updater"
if not exist "./updater/updater.exe" (
    echo [경고] 루트에 ./updater/updater.exe 파일이 존재하지 않습니다. 복사를 건너뜁니다.
) else (
    xcopy /Y ".\updater\updater.exe" "%OUTPUT_DIR%" > nul
)

echo [3/5] 버전 정보 설정 중...
set "VERSION="
set /p "VERSION=사용할 버전을 입력하세요 (예: 1.0.0 또는 v1.0.0): "

if "%VERSION%"=="" goto GET_VERSION

set "FIRST_CHAR=%VERSION:~0,1%"
if /i not "%FIRST_CHAR%"=="v" (
    set "VERSION=v%VERSION%"
)

echo [4/5] ver.txt 저장 중...
echo %VERSION%> "%OUTPUT_DIR%\ver.txt"
echo 버전이 %VERSION%(으)로 설정되었습니다.

echo [5/5] 결과물 폴더 압축 중...
set "ZIP_NAME=%OUTPUT_DIR%\..\Mine 4 PlayList.zip"

if exist "%ZIP_NAME%" (
    echo 기존 압축 파일 삭제 중: %ZIP_NAME%
    del /f /q "%ZIP_NAME%"
)

powershell -Command "Compress-Archive -Path '%OUTPUT_DIR%\*' -DestinationPath '%ZIP_NAME%' -Force"

echo.
echo ========================================================
echo 모든 작업이 성공적으로 완료되었습니다!
echo 생성된 압축 파일: %ZIP_NAME%
echo ========================================================

:END
pause
endlocal