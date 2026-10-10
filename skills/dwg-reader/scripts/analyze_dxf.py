"""DXF 도면 분석기: 레이어, 블록 수량, 블록 속성, 문자, 레이어별 선 길이 추출.

사용법:
    python analyze_dxf.py <도면.dxf> [--xlsx 결과.xlsx] [--map block_map.csv]
                          [--nested] [--encoding cp949] [--max-texts 200] [--json-out 결과.json]

표준출력에는 Claude가 읽을 JSON 요약을, --xlsx 지정 시 엑셀 상세 결과를 저장.
"""
import argparse
import csv
import fnmatch
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import ezdxf
from ezdxf import recover
from ezdxf import path as ezpath

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

UNITS = {0: "단위없음", 1: "inch", 2: "feet", 4: "mm", 5: "cm", 6: "m", 7: "km"}
MIF_CODEPAGE = {"1": "shift_jis", "2": "big5", "3": "cp949", "4": "johab", "5": "gb2312"}
LENGTH_TYPES = {"LINE", "LWPOLYLINE", "POLYLINE", "ARC", "CIRCLE", "ELLIPSE", "SPLINE"}


# ---------- 문자 디코딩 ----------
def decode_text(s):
    if not s:
        return ""
    s = re.sub(r"\\U\+([0-9A-Fa-f]{4})", lambda m: chr(int(m.group(1), 16)), s)

    def mif(m):
        try:
            return bytes.fromhex(m.group(2)).decode(MIF_CODEPAGE.get(m.group(1), "cp949"))
        except Exception:
            return m.group(0)

    return re.sub(r"\\M\+([1-5])([0-9A-Fa-f]{4})", mif, s)


def looks_garbled(texts):
    """한글이 없고 깨진 라틴 확장문자/대체문자 비율이 높으면 인코딩 오류로 판단."""
    sample = "".join(texts[:500])
    if not sample:
        return False
    hangul = sum(1 for c in sample if "\uac00" <= c <= "\ud7a3")
    bad = sum(1 for c in sample if c == "\ufffd" or "\udc80" <= c <= "\udcff" or "\u00c0" <= c <= "\u00ff")
    return hangul == 0 and bad / len(sample) > 0.05


# ---------- 로드 ----------
def load(path, encoding=None):
    try:
        doc = ezdxf.readfile(path, encoding=encoding) if encoding else ezdxf.readfile(path)
        return doc, []
    except ezdxf.DXFStructureError:
        doc, auditor = recover.readfile(path)
        return doc, [str(e.message) for e in auditor.errors][:20]


def raw_texts(doc):
    out = []
    for e in doc.modelspace().query("TEXT MTEXT"):
        out.append(e.dxf.text if e.dxftype() == "TEXT" else e.text)
    return out


# ---------- 블록 ----------
def effective_name(doc, insert):
    """동적 블록(*U123)의 원래 블록 이름 추적 (실패 시 원래 이름)."""
    name = insert.dxf.name
    if not name.startswith("*U"):
        return name
    try:
        br = doc.blocks.get(name).block_record
        if br.has_xdata("AcDbBlockRepBTag"):
            for code, value in br.get_xdata("AcDbBlockRepBTag"):
                if code == 1005:
                    return doc.entitydb[value].dxf.name
    except Exception:
        pass
    return name


def load_map(path):
    if not path:
        return []
    with open(path, encoding="utf-8-sig") as f:
        return [(r["pattern"].upper(), r["item"]) for r in csv.DictReader(f) if r.get("pattern")]


def map_item(name, rules):
    for pattern, item in rules:
        if fnmatch.fnmatch(name.upper(), pattern):
            return item
    return ""


def walk_inserts(doc, layout_entities, nested, depth=0):
    for e in layout_entities:
        if e.dxftype() != "INSERT":
            continue
        yield e, depth
        if nested and depth < 8:
            blk = doc.blocks.get(e.dxf.name)
            if blk is not None and not blk.block_record.is_xref:
                yield from walk_inserts(doc, blk, nested, depth + 1)


# ---------- 길이 ----------
def entity_length(e):
    t = e.dxftype()
    if t == "LINE":
        return math.dist(e.dxf.start, e.dxf.end)
    if t == "CIRCLE":
        return 2 * math.pi * e.dxf.radius
    p = ezpath.make_path(e)
    pts = list(p.flattening(distance=0.01))
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))


# ---------- 분석 ----------
def analyze(doc, rules, nested, max_texts):
    msp = doc.modelspace()
    units = UNITS.get(doc.header.get("$INSUNITS", 0), "기타")

    layer_count = Counter()
    layer_len = defaultdict(float)
    for e in msp:
        layer = e.dxf.get("layer", "0")
        layer_count[layer] += 1
        if e.dxftype() in LENGTH_TYPES:
            try:
                layer_len[layer] += entity_length(e)
            except Exception:
                pass

    blocks = defaultdict(lambda: {"count": 0, "layers": Counter()})
    attribs, texts = [], []
    xrefs = set()
    for ins, depth in walk_inserts(doc, msp, nested):
        name = effective_name(doc, ins)
        blk = doc.blocks.get(ins.dxf.name)
        if blk is not None and blk.block_record.is_xref:
            xrefs.add(name)
            continue
        b = blocks[name]
        b["count"] += 1
        b["layers"][ins.dxf.layer] += 1
        for a in ins.attribs:
            val = decode_text(a.dxf.text)
            attribs.append({"block": name, "tag": a.dxf.tag, "value": val, "layer": ins.dxf.layer,
                            "x": round(ins.dxf.insert.x, 1), "y": round(ins.dxf.insert.y, 1)})

    for e in msp.query("TEXT MTEXT"):
        raw = e.dxf.text if e.dxftype() == "TEXT" else e.plain_text()
        txt = decode_text(raw).strip()
        if txt:
            pos = e.dxf.insert
            texts.append({"type": e.dxftype(), "layer": e.dxf.layer, "text": txt,
                          "x": round(pos.x, 1), "y": round(pos.y, 1)})

    block_rows = sorted(
        ({"block": n, "item": map_item(n, rules), "count": v["count"],
          "layers": ", ".join(f"{k}({c})" for k, c in v["layers"].most_common())}
         for n, v in blocks.items()),
        key=lambda r: -r["count"])

    layers = [{"layer": l.dxf.name, "color": l.dxf.color, "off": not l.is_on(), "frozen": l.is_frozen(),
               "entities": layer_count.get(l.dxf.name, 0), "length": round(layer_len.get(l.dxf.name, 0.0), 2)}
              for l in doc.layers]
    layers.sort(key=lambda r: -r["entities"])

    text_freq = Counter(t["text"] for t in texts)
    summary = {
        "dxf_version": doc.dxfversion,
        "units": units,
        "entity_total": sum(layer_count.values()),
        "layer_count": len(layers),
        "block_types": len(block_rows),
        "block_total": sum(r["count"] for r in block_rows),
        "text_count": len(texts),
        "xrefs": sorted(xrefs),
        "nested_counted": nested,
        "blocks": block_rows[:60],
        "layers_top": [l for l in layers if l["entities"]][:40],
        "texts_frequent": text_freq.most_common(max_texts),
        "attrib_tags": Counter(a["tag"] for a in attribs).most_common(30),
    }
    return summary, {"block_rows": block_rows, "layers": layers, "texts": texts, "attribs": attribs}


def write_xlsx(path, summary, detail):
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "요약"
    for k in ["dxf_version", "units", "entity_total", "layer_count", "block_types", "block_total", "text_count"]:
        ws.append([k, summary[k]])
    ws.append(["xrefs", ", ".join(summary["xrefs"])])
    ws.append(["nested_counted", str(summary["nested_counted"])])

    def sheet(title, header, rows):
        s = wb.create_sheet(title)
        s.append(header)
        for c in s[1]:
            c.font = Font(bold=True)
        for r in rows:
            s.append([r.get(h) for h in header])
        s.freeze_panes = "A2"
        s.auto_filter.ref = s.dimensions
        for col in s.columns:
            width = max(len(str(c.value or "")) for c in col[:300])
            s.column_dimensions[col[0].column_letter].width = min(max(width * 1.3, 8), 60)

    sheet("블록수량", ["block", "item", "count", "layers"], detail["block_rows"])
    sheet("블록속성", ["block", "tag", "value", "layer", "x", "y"], detail["attribs"])
    sheet("레이어", ["layer", "color", "off", "frozen", "entities", "length"], detail["layers"])
    sheet("문자", ["type", "layer", "text", "x", "y"], detail["texts"])
    wb.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf")
    ap.add_argument("--xlsx")
    ap.add_argument("--map", help="블록이름 패턴 -> 품목 매핑 CSV (pattern,item)")
    ap.add_argument("--nested", action="store_true", help="블록 안의 중첩 블록도 집계")
    ap.add_argument("--encoding", help="강제 인코딩 (예: cp949)")
    ap.add_argument("--max-texts", type=int, default=200)
    ap.add_argument("--json-out", help="전체 결과(JSON) 저장 경로. 내역 대조(compare.py) 입력으로 사용")
    args = ap.parse_args()

    doc, errors = load(args.dxf, args.encoding)
    encoding_note = args.encoding or "auto"
    if not args.encoding and looks_garbled(raw_texts(doc)):
        doc, errors = load(args.dxf, "cp949")
        encoding_note = "cp949 (깨짐 감지 후 자동 재시도)"

    summary, detail = analyze(doc, load_map(args.map), args.nested, args.max_texts)
    summary["file"] = Path(args.dxf).name
    summary["encoding"] = encoding_note
    summary["recover_errors"] = errors
    if args.xlsx:
        write_xlsx(args.xlsx, summary, detail)
        summary["xlsx"] = str(Path(args.xlsx).resolve())
    if args.json_out:
        full = {**summary, "blocks": detail["block_rows"], "layers": detail["layers"], "texts": detail["texts"]}
        Path(args.json_out).write_text(json.dumps(full, ensure_ascii=False, indent=1), encoding="utf-8")
        summary["json_out"] = str(Path(args.json_out).resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
