"""径向速度检测器 —— 测量波源相对于检测器的径向速度，并计算多普勒频移"""

import math


class SpeedDetector:
    """固定在空间某点的测速器，测量波源的径向速度和理论多普勒频移"""

    __slots__ = ('x', 'y', 'radial_velocity', 'freq_ratio')

    def __init__(self, x: float, y: float):
        self.x = x                          # 检测器 X 坐标
        self.y = y                          # 检测器 Y 坐标
        self.radial_velocity = 0.0          # 最近一次测得的径向速度
        self.freq_ratio = 1.0               # 观测频率 / 发射频率

    def measure(self, source_x: float, source_y: float,
                source_vx: float, source_vy: float,
                wave_speed: float) -> None:
        """
        测量波源相对于检测器的径向速度和多普勒频移比。

        径向速度: 波源速度在「波源→检测器连线」方向上的投影
          - 正: 波源正在靠近检测器 (蓝移)
          - 负: 波源正在远离检测器 (红移)

        多普勒频移公式 (声波, 检测器静止, 波源运动):
          f_obs = f_src × ─────────
                          c − v_r
          其中 c = 波速, v_r 以靠近检测器为正方向
        """
        # 波源到检测器的向量
        dx = self.x - source_x
        dy = self.y - source_y
        distance = math.hypot(dx, dy)

        if distance < 1e-6:
            # 波源与检测器重合，无法定义径向
            self.radial_velocity = 0.0
            self.freq_ratio = 1.0
            return

        # 从波源指向检测器的单位向量
        ux = dx / distance
        uy = dy / distance

        # 径向速度: 速度在单位向量上的投影
        # v_r > 0: 波源朝检测器移动 → 蓝移
        # v_r < 0: 波源远离检测器移动 → 红移
        self.radial_velocity = source_vx * ux + source_vy * uy

        # 多普勒频移比
        c = wave_speed
        vr = self.radial_velocity  # 靠近检测器为正
        self.freq_ratio = c / (c - vr) if abs(c - vr) > 1e-6 else float('inf')

    def draw(self, surf, font) -> None:
        """在屏幕上绘制检测器标记"""
        import pygame
        px, py = int(self.x), int(self.y)

        # 十字标
        arm = 14
        gap = 4
        color = (0, 255, 100)
        pygame.draw.line(surf, color, (px - arm, py), (px - gap, py), 2)
        pygame.draw.line(surf, color, (px + gap, py), (px + arm, py), 2)
        pygame.draw.line(surf, color, (px, py - arm), (px, py - gap), 2)
        pygame.draw.line(surf, color, (px, py + gap), (px, py + arm), 2)

        # 中心圆
        pygame.draw.circle(surf, color, (px, py), 5, width=1)

        # 标签
        label = font.render("Detector", True, (0, 220, 100))
        surf.blit(label, (px - 28, py - 28))
