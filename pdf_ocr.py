#!/usr/bin/env python3
"""
PDF OCR 프로그램 - 스캔된 PDF를 검색 가능한 텍스트 레이어 PDF로 변환
"""

import argparse
import sys
import os
import tempfile
import shutil
from pathlib import Path

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.panel import Panel
    from rich.table import Table
    from rich import print as rprint
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

console = Console() if RICH_AVAILABLE else None


def print_info(msg):
    if RICH_AVAILABLE:
        console.print(f"[cyan]ℹ[/cyan]  {msg}")
    else:
        print(f"[INFO] {msg}")


def print_success(msg):
    if RICH_AVAILABLE:
        console.print(f"[green]✓[/green]  {msg}")
    else:
        print(f"[OK] {msg}")


def print_error(msg):
    if RICH_AVAILABLE:
        console.print(f"[red]✗[/red]  {msg}", style="red")
    else:
        print(f"[ERROR] {msg}", file=sys.stderr)


def print_warn(msg):
    if RICH_AVAILABLE:
        console.print(f"[yellow]⚠[/yellow]  {msg}")
    else:
        print(f"[WARN] {msg}")


def check_pdf_has_text(pdf_path: str) -> tuple[bool, int]:
    """PDF가 이미 텍스트 레이어를 가지고 있는지 확인"""
    import fitz  # PyMuPDF
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    pages_with_text = 0

    for page in doc:
        text = page.get_text().strip()
        if len(text) > 10:
            pages_with_text += 1

    doc.close()
    return pages_with_text > (total_pages * 0.3), pages_with_text


def ocr_with_ocrmypdf(
    input_path: str,
    output_path: str,
    language: str = "kor+eng",
    dpi: int = 300,
    force_ocr: bool = False,
    optimize: int = 1,
    rotate_pages: bool = True,
    deskew: bool = True,
) -> bool:
    """ocrmypdf를 사용해 PDF OCR 수행 (메인 방법)"""
    import ocrmypdf

    kwargs = {
        "language": language,
        "output_type": "pdf",
        "optimize": optimize,
        "rotate_pages": rotate_pages,
        "deskew": deskew,
        "progress_bar": False,
    }

    if force_ocr:
        kwargs["force_ocr"] = True
    else:
        kwargs["skip_text"] = True  # 이미 텍스트 있는 페이지는 건너뜀

    try:
        ocrmypdf.ocr(input_path, output_path, **kwargs)
        return True
    except ocrmypdf.exceptions.PriorOcrFoundError:
        # 이미 OCR 된 PDF인 경우 force로 재시도
        kwargs.pop("skip_text", None)
        kwargs["force_ocr"] = True
        ocrmypdf.ocr(input_path, output_path, **kwargs)
        return True
    except Exception as e:
        print_error(f"ocrmypdf 오류: {e}")
        return False


def ocr_with_tesseract(
    input_path: str,
    output_path: str,
    language: str = "kor+eng",
    dpi: int = 300,
) -> bool:
    """pdf2image + pytesseract를 사용한 대체 OCR (폴백 방법)"""
    try:
        import pytesseract
        from pdf2image import convert_from_path
        import fitz
        from PIL import Image
        import io

        print_info("대체 OCR 방식 (pytesseract) 사용 중...")

        # PDF → 이미지 변환
        images = convert_from_path(input_path, dpi=dpi)
        total = len(images)

        # 새 PDF 생성
        doc = fitz.open()

        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("OCR 처리 중...", total=total)
                for i, img in enumerate(images):
                    _process_page_tesseract(doc, img, i + 1, language, progress, task)
        else:
            for i, img in enumerate(images):
                print(f"페이지 {i+1}/{total} 처리 중...")
                _process_page_tesseract(doc, img, i + 1, language)

        doc.save(output_path)
        doc.close()
        return True

    except Exception as e:
        print_error(f"pytesseract 오류: {e}")
        return False


def _process_page_tesseract(doc, img, page_num, language, progress=None, task=None):
    """단일 페이지를 Tesseract로 OCR 처리"""
    import pytesseract
    import fitz
    from PIL import Image
    import io

    width, height = img.size
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    # 페이지 추가 (이미지)
    page = doc.new_page(width=width, height=height)
    page.insert_image(fitz.Rect(0, 0, width, height), stream=img_bytes.read())

    # OCR로 텍스트 추출 및 투명 텍스트 레이어 추가
    ocr_data = pytesseract.image_to_data(
        img, lang=language, output_type=pytesseract.Output.DICT
    )

    n_boxes = len(ocr_data["text"])
    for j in range(n_boxes):
        text = ocr_data["text"][j].strip()
        if not text or float(ocr_data["conf"][j]) < 30:
            continue

        x, y, w, h = (
            ocr_data["left"][j],
            ocr_data["top"][j],
            ocr_data["width"][j],
            ocr_data["height"][j],
        )
        if w == 0 or h == 0:
            continue

        rect = fitz.Rect(x, y, x + w, y + h)
        # 투명 텍스트 삽입 (검색 가능하게)
        page.insert_textbox(
            rect,
            text + " ",
            fontsize=h * 0.8,
            color=(1, 1, 1),  # 흰색 = 투명하게 보임
            render_mode=3,     # 투명 렌더링
        )

    if progress and task is not None:
        progress.advance(task)


def get_pdf_info(pdf_path: str) -> dict:
    """PDF 기본 정보 반환"""
    import fitz
    doc = fitz.open(pdf_path)
    info = {
        "pages": len(doc),
        "size_mb": os.path.getsize(pdf_path) / (1024 * 1024),
        "metadata": doc.metadata,
    }
    doc.close()
    return info


def run_ocr(
    input_path: str,
    output_path: str,
    language: str = "kor+eng",
    dpi: int = 300,
    force_ocr: bool = False,
    optimize: int = 1,
    rotate_pages: bool = True,
    deskew: bool = True,
    fallback: bool = True,
) -> bool:
    """메인 OCR 파이프라인"""
    if RICH_AVAILABLE:
        console.print(
            Panel.fit(
                "[bold cyan]PDF OCR 프로그램[/bold cyan]\n"
                "스캔된 PDF → 검색 가능한 텍스트 레이어 PDF",
                border_style="cyan",
            )
        )

    # 입력 파일 검사
    if not os.path.exists(input_path):
        print_error(f"파일을 찾을 수 없습니다: {input_path}")
        return False

    info = get_pdf_info(input_path)

    if RICH_AVAILABLE:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[dim]입력 파일[/dim]", f"[white]{input_path}[/white]")
        table.add_row("[dim]출력 파일[/dim]", f"[white]{output_path}[/white]")
        table.add_row("[dim]총 페이지[/dim]", f"[white]{info['pages']}페이지[/white]")
        table.add_row("[dim]파일 크기[/dim]", f"[white]{info['size_mb']:.2f} MB[/white]")
        table.add_row("[dim]OCR 언어[/dim]", f"[white]{language}[/white]")
        table.add_row("[dim]해상도[/dim]", f"[white]{dpi} DPI[/white]")
        console.print(table)
        console.print()

    # 텍스트 레이어 확인
    has_text, pages_with_text = check_pdf_has_text(input_path)
    if has_text and not force_ocr:
        print_warn(
            f"이 PDF는 이미 텍스트 레이어를 포함하고 있습니다 "
            f"({pages_with_text}/{info['pages']} 페이지). "
            "텍스트 없는 페이지만 OCR 처리합니다."
        )

    # ocrmypdf로 OCR 시도
    print_info("OCR 처리를 시작합니다...")

    if RICH_AVAILABLE:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]ocrmypdf로 {info['pages']}페이지 처리 중...[/cyan]",
                total=None,
            )
            success = ocr_with_ocrmypdf(
                input_path, output_path, language, dpi, force_ocr, optimize,
                rotate_pages, deskew
            )
    else:
        success = ocr_with_ocrmypdf(
            input_path, output_path, language, dpi, force_ocr, optimize,
            rotate_pages, deskew
        )

    # 실패 시 폴백
    if not success and fallback:
        print_warn("ocrmypdf 실패. pytesseract로 대체 시도...")
        success = ocr_with_tesseract(input_path, output_path, language, dpi)

    if success and os.path.exists(output_path):
        out_size = os.path.getsize(output_path) / (1024 * 1024)
        print_success(f"OCR 완료!")
        print_success(f"출력 파일: {output_path} ({out_size:.2f} MB)")
        return True
    else:
        print_error("OCR 처리에 실패했습니다.")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="PDF OCR 프로그램 - 스캔된 PDF를 검색 가능한 PDF로 변환",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python pdf_ocr.py input.pdf                        # 기본 실행 (한국어+영어)
  python pdf_ocr.py input.pdf -o output.pdf          # 출력 파일 지정
  python pdf_ocr.py input.pdf -l kor                 # 한국어 전용
  python pdf_ocr.py input.pdf -l eng                 # 영어 전용
  python pdf_ocr.py input.pdf -l kor+eng --dpi 400   # 고해상도
  python pdf_ocr.py input.pdf --force                # 기존 텍스트 무시하고 재OCR
  python pdf_ocr.py input.pdf --no-deskew --no-rotate  # 전처리 없이 OCR
        """,
    )

    parser.add_argument("input", help="입력 PDF 파일 경로")
    parser.add_argument(
        "-o", "--output",
        help="출력 PDF 파일 경로 (기본: input_ocr.pdf)",
        default=None,
    )
    parser.add_argument(
        "-l", "--language",
        help="OCR 언어 (기본: kor+eng). 예: kor, eng, kor+eng",
        default="kor+eng",
    )
    parser.add_argument(
        "--dpi",
        help="변환 해상도 (기본: 300). 높을수록 정확하지만 느림",
        type=int,
        default=300,
        choices=[150, 200, 300, 400, 600],
    )
    parser.add_argument(
        "--force",
        help="기존 텍스트 레이어가 있어도 강제 재OCR",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--optimize",
        help="PDF 최적화 수준 (0=없음, 1=기본, 2=강력, 3=최강). 기본: 1",
        type=int,
        default=1,
        choices=[0, 1, 2, 3],
    )
    parser.add_argument(
        "--no-rotate",
        help="페이지 자동 회전 비활성화",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--no-deskew",
        help="기울기 보정 비활성화",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "--no-fallback",
        help="ocrmypdf 실패 시 pytesseract 대체 사용 안 함",
        action="store_true",
        default=False,
    )

    args = parser.parse_args()

    # 출력 경로 자동 설정
    if args.output is None:
        input_p = Path(args.input)
        args.output = str(input_p.parent / f"{input_p.stem}_ocr{input_p.suffix}")

    success = run_ocr(
        input_path=args.input,
        output_path=args.output,
        language=args.language,
        dpi=args.dpi,
        force_ocr=args.force,
        optimize=args.optimize,
        rotate_pages=not args.no_rotate,
        deskew=not args.no_deskew,
        fallback=not args.no_fallback,
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
