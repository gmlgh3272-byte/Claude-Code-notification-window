# dwg-reader 스킬

DWG/DXF 도면을 Claude가 자동으로 변환·분석하게 하는 스킬.

## 설치
### Claude Code (윈도우 데스크톱 앱)
1. ODA File Converter 설치: https://www.opendesign.com/guestfiles/oda_file_converter
2. 이 폴더에서 `install.bat` 실행 → `%USERPROFILE%\.claude\skills\dwg-reader` 에 복사되고 ezdxf, openpyxl 설치
3. Claude Code 재시작

### 코워크 / Claude 앱
- `dwg-reader.zip`을 설정 > 기능(Capabilities) > 스킬에서 업로드
- 코워크는 격리 환경이라 윈도우의 ODA를 직접 호출하지 못할 수 있음. 이 경우 DWG를 미리 DXF로 바꿔서 올리면 분석은 정상 동작

## 사용 예
- "이 DWG 도면 분석해서 콘센트랑 조명 수량 뽑아줘"
- "도면 폴더 전체 DXF로 바꾸고 문자 목록 엑셀로 정리해줘"

## 블록 매핑
`block_map.example.csv`를 복사해서 실제 설계사무소 블록 이름에 맞게 수정 (`pattern,item`, `*` 와일드카드, 위쪽 규칙 우선).

## 파일
- `SKILL.md`: 스킬 지침
- `scripts/convert_dwg.py`: DWG → DXF 변환 (ODA 우선, LibreDWG 대체)
- `scripts/analyze_dxf.py`: 레이어·블록 수량·속성·문자·선 길이 추출, 엑셀 출력
