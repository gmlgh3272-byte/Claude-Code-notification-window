#!/bin/bash

# 이 파일이 있는 폴더로 이동
cd "$(dirname "$0")"

# 서버 실행
python3 pdf_ocr_gui.py
