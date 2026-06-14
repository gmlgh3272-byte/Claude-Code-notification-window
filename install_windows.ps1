# PDF OCR Windows 자동 설치 스크립트
# PowerShell을 관리자 권한으로 실행 후: .\install_windows.ps1

$ErrorActionPreference = "Stop"

function Print-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Print-OK($msg)   { Write-Host "  [OK] $msg" -ForegroundColor Green }
function Print-Warn($msg) { Write-Host "  [!!] $msg" -ForegroundColor Yellow }

Print-Step "1단계 - Git 설치 확인"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    winget install --id Git.Git -e --source winget --accept-package-agreements --accept-source-agreements
    $env:PATH += ";C:\Program Files\Git\bin"
    Print-OK "Git 설치 완료"
} else {
    Print-OK "Git 이미 설치됨"
}

Print-Step "2단계 - Python 설치 확인"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    winget install --id Python.Python.3.12 -e --source winget --accept-package-agreements --accept-source-agreements
    $env:PATH += ";$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts"
    Print-OK "Python 설치 완료"
} else {
    Print-OK "Python 이미 설치됨: $(python --version)"
}

Print-Step "3단계 - Tesseract OCR 설치 확인"
$tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"
if (-not (Test-Path $tesseractPath)) {
    winget install --id UB-Mannheim.TesseractOCR -e --source winget --accept-package-agreements --accept-source-agreements
    Print-OK "Tesseract 설치 완료"
} else {
    Print-OK "Tesseract 이미 설치됨"
}

# Tesseract PATH 추가
if ($env:PATH -notlike "*Tesseract-OCR*") {
    $env:PATH += ";C:\Program Files\Tesseract-OCR"
    [Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Program Files\Tesseract-OCR", "User")
}

Print-Step "4단계 - 한국어 언어팩 확인"
$korData = "C:\Program Files\Tesseract-OCR\tessdata\kor.traineddata"
if (-not (Test-Path $korData)) {
    Print-Warn "한국어 데이터 다운로드 중..."
    $korUrl = "https://github.com/tesseract-ocr/tessdata/raw/main/kor.traineddata"
    Invoke-WebRequest -Uri $korUrl -OutFile $korData
    Print-OK "한국어 언어팩 설치 완료"
} else {
    Print-OK "한국어 언어팩 이미 있음"
}

Print-Step "5단계 - Poppler 설치 (pdf2image 필수)"
$popplerDir = "C:\poppler"
$popplerBin = "$popplerDir\Library\bin"
if (-not (Test-Path $popplerBin)) {
    Print-Warn "Poppler 다운로드 중..."
    $popplerUrl = "https://github.com/oschwartz10612/poppler-windows/releases/download/v24.08.0-0/Release-24.08.0-0.zip"
    $zipPath = "$env:TEMP\poppler.zip"
    Invoke-WebRequest -Uri $popplerUrl -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath "C:\" -Force
    # 폴더 이름 정리
    $extracted = Get-ChildItem "C:\" -Filter "poppler-*" -Directory | Select-Object -First 1
    if ($extracted) { Rename-Item $extracted.FullName $popplerDir -ErrorAction SilentlyContinue }
    Remove-Item $zipPath
    Print-OK "Poppler 설치 완료"
} else {
    Print-OK "Poppler 이미 설치됨"
}

# Poppler PATH 추가
if ($env:PATH -notlike "*poppler*") {
    $env:PATH += ";$popplerBin"
    [Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$popplerBin", "User")
    Print-OK "Poppler PATH 등록 완료"
}

Print-Step "6단계 - 프로젝트 다운로드"
$projectDir = "$env:USERPROFILE\Claude-Code-notification-window"
if (-not (Test-Path $projectDir)) {
    git clone https://github.com/gmlgh3272-byte/Claude-Code-notification-window.git $projectDir
    Print-OK "프로젝트 다운로드 완료"
} else {
    Print-OK "프로젝트 폴더 이미 존재함 — git pull 실행"
    git -C $projectDir pull origin claude/inspiring-volta-regy1v
}
git -C $projectDir checkout claude/inspiring-volta-regy1v

Print-Step "7단계 - Python 패키지 설치"
python -m pip install --upgrade pip --quiet
python -m pip install flask ocrmypdf pdf2image pytesseract PyMuPDF Pillow rich
Print-OK "Python 패키지 설치 완료"

Print-Step "8단계 - 바탕화면에 실행파일 복사"
$bat = "$projectDir\PDF OCR 실행.bat"
$desktop = "$env:USERPROFILE\Desktop\PDF OCR 실행.bat"
Copy-Item $bat $desktop -Force
Print-OK "바탕화면에 'PDF OCR 실행.bat' 생성 완료"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  설치 완료!" -ForegroundColor Green
Write-Host "  바탕화면의 'PDF OCR 실행.bat'를 더블클릭하면 시작됩니다." -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green
