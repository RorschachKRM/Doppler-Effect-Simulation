import pygame
import math
from speed_detector import SpeedDetector

# --- 配置 ---
SCREEN_W, SCREEN_H = 1000, 700
FPS = 60
WAVE_SPEED = 3.0          # 波纹扩展速度 (像素/帧)，须大于 SOURCE_SPEED 才能看到前端压缩
WAVE_EMIT_INTERVAL = 22   # 每隔多少帧发射一个波纹
SOURCE_SPEED = 2.0         # 方向键移动速度，小于 WAVE_SPEED 时为亚音速多普勒效应
MAX_WAVES = 120

# 颜色
BG_COLOR = (15, 15, 25)
SOURCE_COLOR = (255, 220, 60)
SOURCE_OUTLINE = (255, 180, 0)
WAVE_HI_COLOR = (80, 140, 255)   # 高频侧 (蓝)
WAVE_MID_COLOR = (180, 180, 220) # 中频
WAVE_LO_COLOR = (255, 90, 80)    # 低频侧 (红)

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Doppler Effect Simulation - 多普勒效应")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 28)


class Wave:
    """单个圆形波纹"""
    __slots__ = ('x', 'y', 'radius', 'alive')

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.radius = 0.0
        self.alive = True

    def update(self) -> None:
        self.radius += WAVE_SPEED
        if self.radius > max(SCREEN_W, SCREEN_H) * 1.05:
            self.alive = False

    def draw(self, surf: pygame.Surface) -> None:
        r = int(self.radius)
        if r <= 0:
            return
        # 透明度随半径递减
        progress = self.radius / (SCREEN_W * 0.7)
        alpha = max(0, int(200 * (1 - progress ** 1.5)))
        if alpha == 0:
            return

        color = (160, 180, 220, alpha)
        # 用临时 surface 画带透明度的圆
        size = r * 2 + 4
        ring = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(ring, color, (r + 2, r + 2), r, width=1)
        surf.blit(ring, (int(self.x) - r - 2, int(self.y) - r - 2))


class Source:
    """可移动的波源"""
    __slots__ = ('x', 'y', 'vx', 'vy', 'waves', 'emit_timer')

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.waves: list[Wave] = []
        self.emit_timer = 0

    @property
    def speed(self) -> float:
        return math.hypot(self.vx, self.vy)

    def handle_input(self, keys) -> None:
        self.vx = 0.0
        self.vy = 0.0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vx = -SOURCE_SPEED
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vx = SOURCE_SPEED
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.vy = -SOURCE_SPEED
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.vy = SOURCE_SPEED

    def update(self) -> None:
        # 移动波源
        self.x += self.vx
        self.y += self.vy
        # 限制在屏幕内
        margin = 30
        self.x = max(margin, min(SCREEN_W - margin, self.x))
        self.y = max(margin, min(SCREEN_H - margin, self.y))

        # 更新所有波纹
        for w in self.waves:
            w.update()
        self.waves = [w for w in self.waves if w.alive]

        # 发射新波纹
        self.emit_timer += 1
        if self.emit_timer >= WAVE_EMIT_INTERVAL:
            self.emit_timer = 0
            self.waves.append(Wave(self.x, self.y))
            if len(self.waves) > MAX_WAVES:
                self.waves = self.waves[-MAX_WAVES:]

    def draw(self, surf: pygame.Surface) -> None:
        # 画波纹
        for w in self.waves:
            w.draw(surf)

        # 画波源
        px, py = int(self.x), int(self.y)
        pygame.draw.circle(surf, SOURCE_OUTLINE, (px, py), 12, width=2)
        pygame.draw.circle(surf, SOURCE_COLOR, (px, py), 8)
        # 发光效果
        glow = pygame.Surface((30, 30), pygame.SRCALPHA)
        for r in range(12, 6, -1):
            a = max(0, 80 - (12 - r) * 15)
            pygame.draw.circle(glow, (255, 200, 40, a), (15, 15), r)
        surf.blit(glow, (px - 15, py - 15))


def draw_hud(surf: pygame.Surface, source: Source, detector: SpeedDetector) -> None:
    """显示提示信息、速度和频移"""
    texts = [
        ("Arrow Keys / WASD: Move source", (200, 200, 200)),
        ("R: Reset position", (200, 200, 200)),
        ("+/-: Change wave frequency", (200, 200, 200)),
        (f"Source Speed: {source.speed:.2f} px/frame", (180, 200, 255)),
        ("", (0, 0, 0)),
        ("--- Detector ---", (0, 220, 100)),
        (f"Radial Velocity: {detector.radial_velocity:+.2f}  (+ approach / - recede)", (0, 255, 120)),
        (f"Freq Ratio (f_obs / f_src): {detector.freq_ratio:.3f}", (0, 255, 120)),
    ]
    y = 12
    for text, color in texts:
        if not text:
            y += 8
            continue
        img = font.render(text, True, color)
        surf.blit(img, (12, y))
        y += 26


def main():
    source = Source(SCREEN_W / 2, SCREEN_H / 2)
    detector = SpeedDetector(SCREEN_W / 2, SCREEN_H / 2)
    global SOURCE_SPEED, WAVE_EMIT_INTERVAL

    running = True
    while running:
        # --- 事件 ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    source.x, source.y = SCREEN_W / 2, SCREEN_H / 2
                elif event.key in (pygame.K_EQUALS, pygame.K_KP_PLUS):
                    WAVE_EMIT_INTERVAL = max(5, WAVE_EMIT_INTERVAL - 2)
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    WAVE_EMIT_INTERVAL = min(60, WAVE_EMIT_INTERVAL + 2)

        # --- 输入 ---
        keys = pygame.key.get_pressed()
        source.handle_input(keys)

        # --- 更新 ---
        source.update()
        detector.measure(source.x, source.y, source.vx, source.vy, WAVE_SPEED)

        # --- 渲染 ---
        screen.fill(BG_COLOR)

        # 画参考网格（微弱）
        for x in range(50, SCREEN_W, 50):
            pygame.draw.line(screen, (30, 30, 40), (x, 0), (x, SCREEN_H))
        for y in range(50, SCREEN_H, 50):
            pygame.draw.line(screen, (30, 30, 40), (0, y), (SCREEN_W, y))

        source.draw(screen)
        detector.draw(screen, font)
        draw_hud(screen, source, detector)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()


if __name__ == "__main__":
    main()
