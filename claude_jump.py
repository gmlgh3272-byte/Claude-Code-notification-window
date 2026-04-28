"""
Claude Code 답변 완료 알림 - 점프하는 아이콘 (Windows)

클로드 코드가 답변을 완료하면 화면 우측 하단에서 픽셀 아트 캐릭터가 점프합니다.
클릭하거나 5초 후 자동으로 사라집니다.
"""

import tkinter as tk
import math
import sys
import os

# 투명 처리할 배경색 (윈도우 투명색 키)
TRANSPARENT = '#010101'

# 클로드 코드 마스코트 색상
ORANGE      = '#E8823A'
ORANGE_MID  = '#C96820'
DARK        = '#1A0A00'

PIXEL = 10  # 각 픽셀의 화면 크기(px)

# 16x15 픽셀 아트 맵
# 0=투명, 1=주황(메인), 2=진한주황(그림자), 3=어두운색(눈/입)
ICON = [
    [0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0],  # 0
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 1
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 2
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 3
    [0,1,1,1,3,3,1,1,1,1,3,3,1,1,1,0],  # 4  <- 눈
    [0,1,1,1,3,3,1,1,1,1,3,3,1,1,1,0],  # 5  <- 눈
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 6
    [0,1,1,1,1,3,3,3,3,3,3,1,1,1,1,0],  # 7  <- 입
    [0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,0],  # 8
    [0,1,2,1,1,1,1,1,1,1,1,1,1,2,1,0],  # 9  <- 어깨 그림자
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 10
    [0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0],  # 11
    [0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0],  # 12 <- 다리
    [0,0,0,0,1,1,0,0,0,0,0,1,1,0,0,0],  # 13 <- 다리
    [0,0,0,0,2,2,0,0,0,0,0,2,2,0,0,0],  # 14 <- 발(그림자)
]

ROWS    = len(ICON)
COLS    = len(ICON[0])
ICON_W  = COLS * PIXEL
ICON_H  = ROWS * PIXEL
MAX_JUMP = 90   # 최대 점프 높이(px)
DURATION = 5.0  # 표시 시간(초)
FPS_MS   = 40   # 프레임 간격(ms) = 25fps


class JumpingIcon:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)           # 제목표시줄 없음
        self.root.attributes('-topmost', True)      # 항상 위에
        self.root.wm_attributes('-transparentcolor', TRANSPARENT)  # 배경 투명

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        # 캔버스 크기: 아이콘 + 점프 여유공간 + 그림자 여백
        self.win_w = ICON_W + 24
        self.win_h = ICON_H + MAX_JUMP + 24

        # 화면 우측 하단 (작업표시줄 위)
        x = sw - self.win_w - 16
        y = sh - ICON_H - 48

        self.root.geometry(f'{self.win_w}x{self.win_h}+{x}+{y - MAX_JUMP}')

        self.canvas = tk.Canvas(
            self.root,
            width=self.win_w,
            height=self.win_h,
            bg=TRANSPARENT,
            highlightthickness=0,
        )
        self.canvas.pack()

        # 클릭하면 닫기
        self.canvas.bind('<Button-1>', lambda e: self.root.destroy())

        self.t = 0.0
        self._animate()
        self.root.mainloop()

    # ── 렌더링 ───────────────────────────────────────────────────
    def _draw(self, jump_px: int):
        """jump_px: 위로 올라간 양 (양수 = 위)"""
        self.canvas.delete('all')

        ox = 12
        oy = MAX_JUMP + 12 - jump_px  # 점프할수록 y 감소

        # 아이콘 픽셀
        color_map = {1: ORANGE, 2: ORANGE_MID, 3: DARK}
        for r, row in enumerate(ICON):
            for c, v in enumerate(row):
                if v == 0:
                    continue
                color = color_map[v]
                x1 = ox + c * PIXEL
                y1 = oy + r * PIXEL
                self.canvas.create_rectangle(
                    x1, y1, x1 + PIXEL, y1 + PIXEL,
                    fill=color, outline='',
                )

        # 바닥 그림자 (점프 높이에 따라 크기 변화)
        ground_y = MAX_JUMP + 12 + ICON_H
        ratio = 1.0 - jump_px / MAX_JUMP  # 0(최고점) ~ 1(지면)
        shadow_w = int(ICON_W * 0.5 * (0.3 + 0.7 * ratio))
        shadow_h = max(2, int(8 * ratio))
        sx = ox + ICON_W // 2 - shadow_w // 2
        sy = ground_y - shadow_h
        if shadow_w > 4:
            self.canvas.create_oval(
                sx, sy, sx + shadow_w, sy + shadow_h,
                fill='#404040', outline='',
            )

    # ── 애니메이션 루프 ──────────────────────────────────────────
    def _animate(self):
        self.t += FPS_MS / 1000.0

        if self.t >= DURATION:
            self.root.destroy()
            return

        progress = self.t / DURATION

        # 감쇠 바운스: |sin| 파형, 시간이 갈수록 진폭 감소
        freq    = 1.6  # 초당 점프 횟수
        phase   = self.t * freq * math.pi * 2
        decay   = max(0.0, 1.0 - progress * 0.85)
        jump_px = int(abs(math.sin(phase)) * MAX_JUMP * decay)

        self._draw(jump_px)
        self.root.after(FPS_MS, self._animate)


if __name__ == '__main__':
    # 이미 실행 중인 인스턴스가 있으면 종료 (lock 파일 방식)
    lock_path = os.path.join(os.environ.get('TEMP', os.getcwd()), 'claude_jump.lock')
    try:
        if os.path.exists(lock_path):
            with open(lock_path) as f:
                pid = int(f.read().strip())
            # 이전 프로세스가 살아있으면 그냥 종료
            try:
                os.kill(pid, 0)
                sys.exit(0)
            except OSError:
                pass  # 이전 프로세스가 없으면 계속 진행

        with open(lock_path, 'w') as f:
            f.write(str(os.getpid()))

        JumpingIcon()
    finally:
        try:
            os.remove(lock_path)
        except OSError:
            pass
