"""DWG -> DXF 변환기.

우선순위: ODA File Converter(윈도우/맥) -> LibreDWG dwg2dxf -> 실패 안내.

사용법:
    python convert_dwg.py <DWG 파일 또는 폴더> [--out 출력폴더] [--version ACAD2018]
"""
import argparse
import glob
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ODA_CANDIDATES = [
    r"C:\Program Files\ODA\ODAFileConverter*\ODAFileConverter.exe",
    r"C:\Program Files (x86)\ODA\ODAFileConverter*\ODAFileConverter.exe",
    "/Applications/ODAFileConverter.app/Contents/MacOS/ODAFileConverter",
    "/usr/bin/ODAFileConverter",
]


def find_oda():
    env = os.environ.get("ODA_CONVERTER")
    if env and Path(env).exists():
        return env
    for pattern in ODA_CANDIDATES:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[-1]  # 최신 버전 폴더
    return shutil.which("ODAFileConverter")


def convert_with_oda(oda, dwg_files, out_dir, version):
    # ODA는 폴더 단위로 동작하므로 임시 입력 폴더에 복사
    with tempfile.TemporaryDirectory() as tmp:
        for f in dwg_files:
            shutil.copy2(f, tmp)
        cmd = [oda, tmp, str(out_dir), version, "DXF", "0", "1", "*.DWG"]
        subprocess.run(cmd, check=False, timeout=600)


def convert_with_libredwg(exe, dwg_files, out_dir):
    for f in dwg_files:
        out = out_dir / (f.stem + ".dxf")
        subprocess.run([exe, "-y", "-o", str(out), str(f)], check=False, timeout=600)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("--out", default=None)
    ap.add_argument("--version", default="ACAD2018", help="출력 DXF 버전 (ACAD2018은 UTF-8이라 한글 안전)")
    args = ap.parse_args()

    src = Path(args.src)
    dwg_files = sorted(src.glob("*.dwg")) + sorted(src.glob("*.DWG")) if src.is_dir() else [src]
    dwg_files = list(dict.fromkeys(dwg_files))
    if not dwg_files:
        print("[오류] DWG 파일이 없음")
        return 1
    out_dir = Path(args.out) if args.out else (src if src.is_dir() else src.parent) / "dxf_out"
    out_dir.mkdir(parents=True, exist_ok=True)

    oda = find_oda()
    libredwg = shutil.which("dwg2dxf")
    if oda:
        print(f"[변환기] ODA File Converter: {oda}")
        convert_with_oda(oda, dwg_files, out_dir, args.version)
    elif libredwg:
        print("[변환기] LibreDWG dwg2dxf (최신 DWG는 일부 누락 가능)")
        convert_with_libredwg(libredwg, dwg_files, out_dir)
    else:
        print("[오류] 변환기를 찾지 못함.")
        print("  1) ODA File Converter 설치: https://www.opendesign.com/guestfiles/oda_file_converter")
        print("  2) 설치 경로가 다르면 환경변수 ODA_CONVERTER 에 exe 경로 지정")
        print("  3) 또는 AutoCAD/TrueView에서 직접 DXF로 저장 후 analyze_dxf.py 사용")
        return 2

    ok = 0
    for f in dwg_files:
        target = next((p for p in out_dir.iterdir() if p.stem.lower() == f.stem.lower() and p.suffix.lower() == ".dxf"), None)
        if target and target.stat().st_size > 0:
            print(f"[성공] {f.name} -> {target}")
            ok += 1
        else:
            print(f"[실패] {f.name}")
    return 0 if ok == len(dwg_files) else 3


if __name__ == "__main__":
    sys.exit(main())
