@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo ============================================
echo  Claude Code 점프 알림 설치 스크립트
echo ============================================
echo.

:: Python 확인
python --version > nul 2>&1
if errorlevel 1 (
    echo [오류] Python이 설치되어 있지 않습니다.
    echo        https://www.python.org 에서 Python 3.8 이상을 설치하세요.
    pause
    exit /b 1
)

:: pythonw 확인 (GUI 전용, 콘솔창 없음)
where pythonw > nul 2>&1
if errorlevel 1 (
    echo [경고] pythonw 를 찾을 수 없습니다. python 으로 대체합니다.
    set PYEXE=python
) else (
    set PYEXE=pythonw
)

:: 설치 경로 설정
set INSTALL_DIR=%USERPROFILE%\claude-notification
echo 설치 경로: %INSTALL_DIR%
echo.

:: 디렉토리 생성
if not exist "%INSTALL_DIR%" (
    mkdir "%INSTALL_DIR%"
    echo [OK] 디렉토리 생성: %INSTALL_DIR%
)

:: 스크립트 복사
copy /y "%~dp0claude_jump.py" "%INSTALL_DIR%\claude_jump.py" > nul
echo [OK] claude_jump.py 복사 완료

:: 테스트 실행
echo.
echo 애니메이션 테스트 중... (5초 후 자동 종료)
start /b %PYEXE% "%INSTALL_DIR%\claude_jump.py"
timeout /t 2 /nobreak > nul
echo [OK] 테스트 실행됨 - 화면 우측 하단을 확인하세요!
echo.

:: Claude Code 전역 settings.json 경로
set CC_SETTINGS=%USERPROFILE%\.claude\settings.json

echo ============================================
echo  Claude Code Hook 설정 안내
echo ============================================
echo.
echo 아래 내용을 %CC_SETTINGS% 에 추가하세요.
echo (파일이 없으면 새로 만드세요)
echo.
echo {
echo   "hooks": {
echo     "Stop": [
echo       {
echo         "matcher": "",
echo         "hooks": [
echo           {
echo             "type": "command",
echo             "command": "cmd /c start /b %PYEXE% \"%INSTALL_DIR%\claude_jump.py\""
echo           }
echo         ]
echo       }
echo     ]
echo   }
echo }
echo.

:: 자동으로 설정 파일 업데이트 시도
if exist "%CC_SETTINGS%" (
    echo [안내] %CC_SETTINGS% 가 이미 존재합니다.
    echo       위 내용을 수동으로 병합하거나 /ultrareview 를 활용하세요.
) else (
    if not exist "%USERPROFILE%\.claude" mkdir "%USERPROFILE%\.claude"
    (
        echo {
        echo   "hooks": {
        echo     "Stop": [
        echo       {
        echo         "matcher": "",
        echo         "hooks": [
        echo           {
        echo             "type": "command",
        echo             "command": "cmd /c start /b %PYEXE% \"%INSTALL_DIR%\\claude_jump.py\""
        echo           }
        echo         ]
        echo       }
        echo     ]
        echo   }
        echo }
    ) > "%CC_SETTINGS%"
    echo [OK] %CC_SETTINGS% 생성 완료!
)

echo.
echo 설치가 완료되었습니다.
echo Claude Code 가 답변을 완료하면 화면 우측 하단에서 아이콘이 점프합니다!
echo.
pause
