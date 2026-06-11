#!/usr/bin/env python3
"""
PDF OCR 웹 GUI - 드래그앤드랍으로 PDF를 OCR 처리
실행: python3 pdf_ocr_gui.py
"""

import os
import sys
import threading
import webbrowser
import uuid
import tempfile
import shutil
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string

app = Flask(__name__)

UPLOAD_FOLDER = tempfile.mkdtemp(prefix="pdf_ocr_")
jobs: dict[str, dict] = {}

HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>PDF OCR</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #0f0f13;
      color: #e2e8f0;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 48px 24px;
    }

    h1 {
      font-size: 2rem;
      font-weight: 700;
      background: linear-gradient(135deg, #60a5fa, #a78bfa);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      margin-bottom: 8px;
    }

    .subtitle {
      color: #64748b;
      font-size: 0.9rem;
      margin-bottom: 40px;
    }

    .card {
      background: #1a1a24;
      border: 1px solid #2d2d3d;
      border-radius: 20px;
      padding: 32px;
      width: 100%;
      max-width: 560px;
      box-shadow: 0 24px 64px rgba(0,0,0,0.4);
    }

    /* 드롭존 */
    #drop-zone {
      border: 2px dashed #3d3d55;
      border-radius: 14px;
      padding: 60px 32px;
      text-align: center;
      cursor: pointer;
      transition: all .25s ease;
      background: #12121a;
      position: relative;
    }
    #drop-zone.drag-over {
      border-color: #60a5fa;
      background: #1a2233;
      box-shadow: 0 0 0 4px rgba(96,165,250,.15);
    }
    #drop-zone .drop-icon {
      font-size: 3rem;
      margin-bottom: 16px;
      display: block;
    }
    #drop-zone .drop-title {
      font-size: 1.1rem;
      font-weight: 600;
      color: #cbd5e1;
      margin-bottom: 8px;
    }
    #drop-zone .drop-sub {
      font-size: 0.82rem;
      color: #475569;
    }
    #file-input { display: none; }

    /* 옵션 */
    .options {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
      margin-top: 20px;
    }
    .option-group label {
      display: block;
      font-size: 0.78rem;
      color: #64748b;
      margin-bottom: 5px;
      text-transform: uppercase;
      letter-spacing: .05em;
    }
    .option-group select {
      width: 100%;
      background: #12121a;
      border: 1px solid #2d2d3d;
      color: #e2e8f0;
      border-radius: 8px;
      padding: 8px 10px;
      font-size: 0.88rem;
      outline: none;
      cursor: pointer;
      transition: border-color .2s;
    }
    .option-group select:focus { border-color: #60a5fa; }

    .toggle-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-top: 12px;
      padding: 10px 14px;
      background: #12121a;
      border: 1px solid #2d2d3d;
      border-radius: 8px;
    }
    .toggle-label { font-size: 0.85rem; color: #94a3b8; }
    .toggle {
      position: relative;
      width: 40px;
      height: 22px;
      flex-shrink: 0;
    }
    .toggle input { opacity: 0; width: 0; height: 0; }
    .toggle .slider {
      position: absolute;
      inset: 0;
      background: #2d2d3d;
      border-radius: 22px;
      cursor: pointer;
      transition: .2s;
    }
    .toggle .slider::before {
      content: '';
      position: absolute;
      width: 16px; height: 16px;
      left: 3px; top: 3px;
      background: #fff;
      border-radius: 50%;
      transition: .2s;
    }
    .toggle input:checked + .slider { background: #60a5fa; }
    .toggle input:checked + .slider::before { transform: translateX(18px); }

    /* 진행 상태 */
    #status-area { margin-top: 24px; display: none; }
    .status-box {
      background: #12121a;
      border: 1px solid #2d2d3d;
      border-radius: 12px;
      padding: 20px;
    }
    .status-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 14px;
    }
    .spinner {
      width: 20px; height: 20px;
      border: 2.5px solid #2d2d3d;
      border-top-color: #60a5fa;
      border-radius: 50%;
      animation: spin .7s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .status-text { font-size: 0.9rem; color: #94a3b8; }
    .status-filename { font-weight: 600; color: #e2e8f0; font-size: 0.95rem; }

    .progress-bar-wrap {
      background: #1e1e2e;
      border-radius: 99px;
      height: 6px;
      overflow: hidden;
    }
    .progress-bar {
      height: 100%;
      border-radius: 99px;
      background: linear-gradient(90deg, #60a5fa, #a78bfa);
      transition: width .4s ease;
      width: 0%;
    }
    .progress-bar.indeterminate {
      width: 40%;
      animation: indeterminate 1.4s ease-in-out infinite;
    }
    @keyframes indeterminate {
      0%   { transform: translateX(-100%); }
      100% { transform: translateX(350%); }
    }

    /* 결과 */
    #result-area { margin-top: 16px; display: none; }
    .result-box {
      background: #0f2410;
      border: 1px solid #166534;
      border-radius: 12px;
      padding: 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .result-box.error {
      background: #1a0a0a;
      border-color: #7f1d1d;
    }
    .result-info { flex: 1; min-width: 0; }
    .result-title { font-weight: 600; color: #4ade80; font-size: 0.95rem; }
    .result-box.error .result-title { color: #f87171; }
    .result-sub { font-size: 0.78rem; color: #4b7a4b; margin-top: 3px; word-break: break-all; }
    .result-box.error .result-sub { color: #7f4b4b; }

    .btn-download {
      background: linear-gradient(135deg, #22c55e, #16a34a);
      color: white;
      border: none;
      border-radius: 8px;
      padding: 10px 20px;
      font-size: 0.88rem;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: opacity .2s;
    }
    .btn-download:hover { opacity: .85; }

    /* 히스토리 */
    #history { margin-top: 28px; width: 100%; max-width: 560px; }
    #history h2 { font-size: 0.82rem; color: #475569; text-transform: uppercase; letter-spacing: .08em; margin-bottom: 12px; }
    .history-item {
      background: #1a1a24;
      border: 1px solid #2d2d3d;
      border-radius: 10px;
      padding: 12px 16px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 8px;
      font-size: 0.85rem;
    }
    .history-name { color: #94a3b8; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
    .history-dl { color: #60a5fa; text-decoration: none; font-size: 0.8rem; white-space: nowrap; }
    .history-dl:hover { text-decoration: underline; }
  </style>
</head>
<body>
  <h1>PDF OCR</h1>
  <p class="subtitle">드래그앤드랍으로 PDF를 텍스트 검색 가능한 PDF로 변환</p>

  <div class="card">
    <div id="drop-zone">
      <span class="drop-icon">📄</span>
      <div class="drop-title">PDF 파일을 여기에 드래그하세요</div>
      <div class="drop-sub">또는 클릭해서 파일 선택 · 최대 200MB</div>
      <input type="file" id="file-input" accept=".pdf" multiple/>
    </div>

    <div class="options">
      <div class="option-group">
        <label>OCR 언어</label>
        <select id="opt-lang">
          <option value="kor+eng" selected>한국어 + 영어</option>
          <option value="kor">한국어만</option>
          <option value="eng">영어만</option>
        </select>
      </div>
      <div class="option-group">
        <label>해상도 (DPI)</label>
        <select id="opt-dpi">
          <option value="200">200 (빠름)</option>
          <option value="300" selected>300 (권장)</option>
          <option value="400">400 (정밀)</option>
          <option value="600">600 (최고품질)</option>
        </select>
      </div>
    </div>

    <div class="toggle-row">
      <span class="toggle-label">기울기 자동 보정</span>
      <label class="toggle">
        <input type="checkbox" id="opt-deskew" checked/>
        <span class="slider"></span>
      </label>
    </div>
    <div class="toggle-row" style="margin-top:8px">
      <span class="toggle-label">페이지 자동 회전</span>
      <label class="toggle">
        <input type="checkbox" id="opt-rotate" checked/>
        <span class="slider"></span>
      </label>
    </div>
    <div class="toggle-row" style="margin-top:8px">
      <span class="toggle-label">기존 텍스트 무시하고 강제 재OCR</span>
      <label class="toggle">
        <input type="checkbox" id="opt-force"/>
        <span class="slider"></span>
      </label>
    </div>

    <div id="status-area">
      <div class="status-box">
        <div class="status-header">
          <div class="spinner"></div>
          <div>
            <div class="status-filename" id="status-filename"></div>
            <div class="status-text" id="status-text">OCR 처리 중...</div>
          </div>
        </div>
        <div class="progress-bar-wrap">
          <div class="progress-bar indeterminate" id="progress-bar"></div>
        </div>
      </div>
    </div>

    <div id="result-area">
      <div class="result-box" id="result-box">
        <div class="result-info">
          <div class="result-title" id="result-title"></div>
          <div class="result-sub" id="result-sub"></div>
        </div>
        <button class="btn-download" id="btn-download" onclick="downloadResult()">다운로드</button>
      </div>
    </div>
  </div>

  <div id="history" style="display:none">
    <h2>완료된 파일</h2>
    <div id="history-list"></div>
  </div>

<script>
  let currentJobId = null;
  let pollInterval = null;
  const history = [];

  const dropZone = document.getElementById('drop-zone');
  const fileInput = document.getElementById('file-input');

  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', e => {
    if (e.target.files.length) handleFiles(e.target.files);
  });

  dropZone.addEventListener('dragover', e => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    const files = [...e.dataTransfer.files].filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (files.length) handleFiles(files);
    else alert('PDF 파일만 지원합니다.');
  });

  function getOptions() {
    return {
      language: document.getElementById('opt-lang').value,
      dpi: parseInt(document.getElementById('opt-dpi').value),
      deskew: document.getElementById('opt-deskew').checked,
      rotate: document.getElementById('opt-rotate').checked,
      force: document.getElementById('opt-force').checked,
    };
  }

  async function handleFiles(files) {
    for (const file of files) {
      await uploadFile(file);
    }
  }

  async function uploadFile(file) {
    if (pollInterval) { clearInterval(pollInterval); pollInterval = null; }

    const opts = getOptions();
    const formData = new FormData();
    formData.append('file', file);
    formData.append('language', opts.language);
    formData.append('dpi', opts.dpi);
    formData.append('deskew', opts.deskew);
    formData.append('rotate', opts.rotate);
    formData.append('force', opts.force);

    showStatus(file.name);

    try {
      const res = await fetch('/upload', { method: 'POST', body: formData });
      const data = await res.json();
      if (!data.job_id) { showError('업로드 실패'); return; }
      currentJobId = data.job_id;
      pollInterval = setInterval(() => pollStatus(file.name), 1200);
    } catch(e) {
      showError('서버 연결 실패: ' + e.message);
    }
  }

  async function pollStatus(filename) {
    if (!currentJobId) return;
    try {
      const res = await fetch('/status/' + currentJobId);
      const data = await res.json();

      if (data.status === 'done') {
        clearInterval(pollInterval); pollInterval = null;
        showSuccess(filename, data.size_mb, currentJobId);
        addHistory(filename, currentJobId);
      } else if (data.status === 'error') {
        clearInterval(pollInterval); pollInterval = null;
        showError(data.message || 'OCR 처리 중 오류 발생');
      } else {
        document.getElementById('status-text').textContent = data.message || 'OCR 처리 중...';
      }
    } catch(e) {}
  }

  function showStatus(name) {
    document.getElementById('status-filename').textContent = name;
    document.getElementById('status-text').textContent = 'OCR 처리 중...';
    document.getElementById('status-area').style.display = 'block';
    document.getElementById('result-area').style.display = 'none';
  }

  function showSuccess(name, size_mb, jobId) {
    document.getElementById('status-area').style.display = 'none';
    const box = document.getElementById('result-box');
    box.className = 'result-box';
    document.getElementById('result-title').textContent = '✓  OCR 완료!';
    document.getElementById('result-sub').textContent =
      `${name.replace('.pdf','_ocr.pdf')}  ·  ${size_mb.toFixed(2)} MB`;
    document.getElementById('btn-download').style.display = '';
    document.getElementById('btn-download').dataset.jobId = jobId;
    document.getElementById('result-area').style.display = 'block';
  }

  function showError(msg) {
    document.getElementById('status-area').style.display = 'none';
    const box = document.getElementById('result-box');
    box.className = 'result-box error';
    document.getElementById('result-title').textContent = '✗  실패';
    document.getElementById('result-sub').textContent = msg;
    document.getElementById('btn-download').style.display = 'none';
    document.getElementById('result-area').style.display = 'block';
  }

  function downloadResult() {
    const jobId = document.getElementById('btn-download').dataset.jobId;
    if (jobId) window.location.href = '/download/' + jobId;
  }

  function addHistory(name, jobId) {
    history.unshift({ name, jobId });
    const histEl = document.getElementById('history');
    const list = document.getElementById('history-list');
    histEl.style.display = 'block';
    list.innerHTML = history.slice(0, 8).map(h => `
      <div class="history-item">
        <span class="history-name">📄 ${h.name.replace('.pdf','_ocr.pdf')}</span>
        <a class="history-dl" href="/download/${h.jobId}">다운로드</a>
      </div>
    `).join('');
  }
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/upload", methods=["POST"])
def upload():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".pdf"):
        return jsonify({"error": "PDF 파일만 지원합니다."}), 400

    language = request.form.get("language", "kor+eng")
    dpi = int(request.form.get("dpi", 300))
    deskew = request.form.get("deskew", "true").lower() == "true"
    rotate = request.form.get("rotate", "true").lower() == "true"
    force = request.form.get("force", "false").lower() == "true"

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_FOLDER, job_id)
    os.makedirs(job_dir)

    input_path = os.path.join(job_dir, "input.pdf")
    output_path = os.path.join(job_dir, "output.pdf")
    f.save(input_path)

    jobs[job_id] = {"status": "processing", "message": "OCR 처리 시작..."}

    thread = threading.Thread(
        target=process_job,
        args=(job_id, input_path, output_path, language, dpi, deskew, rotate, force),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


def process_job(job_id, input_path, output_path, language, dpi, deskew, rotate, force):
    try:
        jobs[job_id]["message"] = "PDF 분석 중..."

        import ocrmypdf
        import fitz

        # 페이지 수 파악
        doc = fitz.open(input_path)
        pages = len(doc)
        doc.close()
        jobs[job_id]["message"] = f"총 {pages}페이지 OCR 처리 중..."

        kwargs = dict(
            language=language,
            output_type="pdf",
            optimize=1,
            rotate_pages=rotate,
            deskew=deskew,
            progress_bar=False,
        )
        if force:
            kwargs["force_ocr"] = True
        else:
            kwargs["skip_text"] = True

        try:
            ocrmypdf.ocr(input_path, output_path, **kwargs)
        except ocrmypdf.exceptions.PriorOcrFoundError:
            kwargs.pop("skip_text", None)
            kwargs["force_ocr"] = True
            ocrmypdf.ocr(input_path, output_path, **kwargs)

        size_mb = os.path.getsize(output_path) / (1024 * 1024)
        jobs[job_id].update({"status": "done", "size_mb": size_mb})

    except Exception as e:
        jobs[job_id].update({"status": "error", "message": str(e)})


@app.route("/status/<job_id>")
def status(job_id):
    job = jobs.get(job_id)
    if not job:
        return jsonify({"status": "error", "message": "작업을 찾을 수 없습니다."}), 404
    return jsonify(job)


@app.route("/download/<job_id>")
def download(job_id):
    output_path = os.path.join(UPLOAD_FOLDER, job_id, "output.pdf")
    if not os.path.exists(output_path):
        return "파일을 찾을 수 없습니다.", 404
    return send_file(output_path, as_attachment=True, download_name="output_ocr.pdf")


def open_browser(port):
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{port}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PDF OCR 웹 GUI")
    parser.add_argument("--port", type=int, default=5050, help="포트 번호 (기본: 5050)")
    parser.add_argument("--no-browser", action="store_true", help="브라우저 자동 실행 안 함")
    args = parser.parse_args()

    print(f"\n🚀 PDF OCR GUI 시작!")
    print(f"   브라우저 주소: http://localhost:{args.port}")
    print(f"   종료: Ctrl+C\n")

    if not args.no_browser:
        threading.Thread(target=open_browser, args=(args.port,), daemon=True).start()

    app.run(host="0.0.0.0", port=args.port, debug=False)
