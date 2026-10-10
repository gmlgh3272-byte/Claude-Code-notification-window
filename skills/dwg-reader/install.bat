@echo off
chcp 65001 > nul
echo ============================================
echo  dwg-reader 스킬 설치 (Claude Code용)
echo ============================================

python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 없습니다. https://www.python.org 에서 설치하세요.
    pause
    exit /b 1
)

echo [1/3] Python 패키지 설치
python -m pip install --upgrade ezdxf openpyxl

echo [2/3] 스킬 복사: %USERPROFILE%\.claude\skills\dwg-reader
set TARGET=%USERPROFILE%\.claude\skills\dwg-reader
if not exist "%TARGET%\scripts" mkdir "%TARGET%\scripts"
copy /Y "%~dp0SKILL.md" "%TARGET%\" > nul
copy /Y "%~dp0block_map.example.csv" "%TARGET%\" > nul
copy /Y "%~dp0scripts\*.py" "%TARGET%\scripts\" > nul

echo [3/3] ODA File Converter 확인
if exist "C:\Program Files\ODA" (
    echo   ODA 폴더 확인됨
) else (
    echo   [안내] ODA File Converter가 없습니다. DWG 자동 변환을 쓰려면 설치하세요.
    echo   https://www.opendesign.com/guestfiles/oda_file_converter
)

echo.
echo 설치 완료. Claude Code를 다시 시작하면 스킬이 인식됩니다.
pause
