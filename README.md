# Doppler Effect Simulation / 多普勒效应仿真

一个基于 Python + Pygame 的多普勒效应可视化仿真。通过可交互的移动波源和圆形波纹直观展示波源运动时波长在前后方向上的压缩与拉伸现象，屏幕中心的测速器实时测量波源的径向速度并计算多普勒频移比。

---

## 什么是多普勒效应？

多普勒效应描述了波源与观察者之间存在相对运动时，观察者接收到的波的频率与波源实际发出的频率不同的现象。

- **波源向你靠近时**：波长被压缩，频率变高（**蓝移**）
- **波源远离你时**：波长被拉伸，频率变低（**红移**）

现实中的例子：
- 救护车/警车从你身边经过时，警笛的音调会从高突然变低
- 天文学家通过光谱的红移/蓝移判断星系的运动方向和速度
- 雷达测速仪利用电磁波的多普勒效应测量车速

---

## 依赖包

| 包 | 用途 |
|----|------|
| [pygame](https://www.pygame.org/) | 图形渲染、事件处理、键盘输入。基于 SDL2，提供窗口创建、2D 绘图、事件循环等游戏/仿真所需的基础能力 |
| [math](https://docs.python.org/3/library/math.html) | Python 内置数学库。本项目中只用了 `math.hypot(x, y)` 计算波源的速度大小（即 (vx² + vy²) 的平方根），用于 HUD 速度显示 |

---

## 操作说明

| 按键 | 功能 |
|------|------|
| **方向键 / WASD** | 移动波源 |
| **R** | 将波源重置到屏幕中心 |
| **+ / -** | 提高/降低波纹发射频率 |
| **ESC** | 退出程序 |

建议先静止观察均匀波纹，然后按住一个方向勾速移动，对比运动前后方向的波纹疏密差异。

---

## 代码详解

整个仿真由 **2 个文件** 组成：`doppler_simulation.py`（主程序）和 `speed_detector.py`（测速器模块），共约 240 行。

---

### 1. 全局配置（第 4–10 行）

```python
SCREEN_W, SCREEN_H = 1000, 700   # 窗口尺寸
FPS = 60                          # 帧率，决定物理更新的时间精度
WAVE_SPEED = 3.0                  # 波纹半径每帧扩张的像素数
WAVE_EMIT_INTERVAL = 22           # 每 22 帧发射一个波纹
SOURCE_SPEED = 2.0                # 方向键按住时波源每帧移动的像素数
MAX_WAVES = 120                   # 最多保留的波纹数量，超出后淘汰最早的
```

**速度关系是展示多普勒效应的核心。** 默认 `SOURCE_SPEED (2.0) < WAVE_SPEED (3.0)`，波源速度小于波速，属于**亚音速**情况：运动前方波纹被压缩（蓝移）、后方波纹被拉伸（红移），前后都有波纹可见。

如果手动将 `SOURCE_SPEED` 调到 ≥ `WAVE_SPEED`（例如都设为 3.0 或更大），则波源会追上前方所有波纹，在前进方向上形成一个锥形包络——这就是物理上的**马赫锥**（Mach cone），对应超音速/音爆现象。

---

### 2. Wave 类（第 27–57 行）—— 单个波纹

```python
class Wave:
    __slots__ = ('x', 'y', 'radius', 'alive')

    def __init__(self, x, y):
        self.x = x          # 波纹圆心 X 坐标（固定在发射时的位置）
        self.y = y          # 波纹圆心 Y 坐标
        self.radius = 0.0   # 当前半径
        self.alive = True   # 是否仍在屏幕内
```

**关键设计**：波纹的 `(x, y)` 在构造时就被锁定。这意味着波源移动后，已发射的波纹圆心**不会跟随**波源移动——这正是波长压缩/拉伸的根本原因。如果波纹圆心跟着波源一起动，就不会出现任何疏密变化。

#### update() 方法

```python
def update(self):
    self.radius += WAVE_SPEED  # 每帧均匀扩张
    if self.radius > max(SCREEN_W, SCREEN_H) * 1.05:
        self.alive = False     # 超出屏幕后标记为死亡，后续在列表中移除
```

波纹的扩张速度是**恒定**的——所有波纹以相同速度向外扩展，不管波源当时在做什么。

#### draw() 方法

```python
def draw(self, surf):
    r = int(self.radius)
    progress = self.radius / (SCREEN_W * 0.7)
    alpha = max(0, int(200 * (1 - progress ** 1.5)))
    # 用带 alpha 通道的临时 Surface 画透明圆环
    ring = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(ring, color, (r + 2, r + 2), r, width=1)
    surf.blit(ring, (int(self.x) - r - 2, int(self.y) - r - 2))
```

要点：
- **alpha 衰减**：波纹越大越透明（`progress ** 1.5` 是非线性衰减，让外圈消失得更快）
- **pygame.SRCALPHA**：创建一个支持透明通道的 Surface，这样波纹叠加时不会互相遮盖
- **width=1**：只画圆环的线，不填充，保持画面干净

---

### 3. Source 类（第 60–124 行）—— 波源

```python
class Source:
    __slots__ = ('x', 'y', 'vx', 'vy', 'waves', 'emit_timer')

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0      # X 方向速度
        self.vy = 0.0      # Y 方向速度
        self.waves = []    # 当前存活的所有波纹
        self.emit_timer = 0  # 发射倒计时
```

#### handle_input() —— 将键盘状态转换为速度

```python
def handle_input(self, keys):
    self.vx = 0.0
    self.vy = 0.0
    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        self.vx = -SOURCE_SPEED
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        self.vx = SOURCE_SPEED
    # ... 上下同理
```

`keys` 是 `pygame.key.get_pressed()` 返回的布尔数组，每次主循环都会调用此方法，所以在按住键时速度会持续生效。

#### update() —— 每帧逻辑（核心）

```python
def update(self):
    # 1. 移动波源
    self.x += self.vx
    self.y += self.vy
    self.x = max(30, min(SCREEN_W - 30, self.x))  # 边界限制
    self.y = max(30, min(SCREEN_H - 30, self.y))

    # 2. 更新所有波纹
    for w in self.waves:
        w.update()
    self.waves = [w for w in self.waves if w.alive]  # 移除死亡波纹

    # 3. 定时发射新波纹
    self.emit_timer += 1
    if self.emit_timer >= WAVE_EMIT_INTERVAL:
        self.emit_timer = 0
        self.waves.append(Wave(self.x, self.y))      # 在当前位置发射
        if len(self.waves) > MAX_WAVES:
            self.waves = self.waves[-MAX_WAVES:]      # 淘汰最早的
```

**这就是产生多普勒效应的全部物理代码。** 其原理是：

- 波源静止时，每次发射的圆心相同，所有波纹同心，间距均匀
- 波源向右移动时，每次发射的圆心都比上一个略靠右
  - 右侧（前方）：相邻波纹圆心间距被拉开，但波源追着前一个波跑，波峰间距实际上变小 → 波长压缩
  - 左侧（后方）：相邻波纹圆心间距被拉开，波源逃离上一个波，波峰间距变大 → 波长拉伸

这完全由 `Wave(self.x, self.y)` 在波源**当前**位置发射这个行为天然产生，不需要任何额外的公式。

#### draw() —— 绘制波源和发光效果

```python
def draw(self, surf):
    for w in self.waves:
        w.draw(surf)
    # 波源主体：外圈 + 内核
    pygame.draw.circle(surf, SOURCE_OUTLINE, (px, py), 12, width=2)
    pygame.draw.circle(surf, SOURCE_COLOR, (px, py), 8)
    # 多层渐变发光
    glow = pygame.Surface((30, 30), pygame.SRCALPHA)
    for r in range(12, 6, -1):
        a = max(0, 80 - (12 - r) * 15)
        pygame.draw.circle(glow, (255, 200, 40, a), (15, 15), r)
    surf.blit(glow, (px - 15, py - 15))
```

发光效果是通过画 6 层半径递减、透明度递增的圆叠加出来的——内层亮、外层暗，模拟辉光。

---

### 4. draw_hud() —— HUD 信息显示（第 128–148 行）

```python
def draw_hud(surf, source, detector):
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
```

HUD 分为两部分：上半部分是操作提示和波源速度（蓝色），下半部分是检测器数据（绿色）。中间的空行用 `y += 8` 产生视觉分隔，而非常规的 `y += 26`。

---

### 5. main() —— 主循环（第 150–199 行）

```python
source = Source(SCREEN_W / 2, SCREEN_H / 2)
detector = SpeedDetector(SCREEN_W / 2, SCREEN_H / 2)  # 固定在屏幕中心

while running:
    # ① 事件处理
    for event in pygame.event.get():
        # ... QUIT、KEYDOWN（R/ESC/+/-）

    # ② 连续按键
    keys = pygame.key.get_pressed()
    source.handle_input(keys)

    # ③ 物理更新 + 测速
    source.update()
    detector.measure(source.x, source.y, source.vx, source.vy, WAVE_SPEED)

    # ④ 渲染
    screen.fill(BG_COLOR)
    # 网格
    source.draw(screen)
    detector.draw(screen, font)     # 绿色十字标
    draw_hud(screen, source, detector)

    pygame.display.flip()
    clock.tick(FPS)
```

测速器的 `measure()` 被放在物理更新之后、渲染之前——因为它不修改任何物理状态，只是读取当前帧的波源位置和速度做计算，属于"观测层"逻辑。

---

### 6. SpeedDetector 类 —— 径向速度与多普勒频移（[speed_detector.py](speed_detector.py)）

测速器固定在屏幕中心，模拟一个静止的"观察者"，实时测量波源的径向速度并计算多普勒频移比。

#### 径向速度（radial_velocity）

径向速度是波源速度在"波源→检测器连线"方向上的投影，而非波源的总速度：

```
径向速度 = 0           径向速度 = +2.0         径向速度 = -2.0
(切向掠过, 无频移)     (沿连线靠近, 蓝移)      (沿连线远离, 红移)

  · Detector              · Detector              · Detector
     \                        ↑                        |
      \   → Source            |   ↑ Source             |   ↓ Source
       \                       |                        |
```

公式实现（[speed_detector.py#L38-L41](speed_detector.py#L38-L41)）：

```python
dx = self.x - source_x       # 检测器 → 波源 的向量
dy = self.y - source_y
distance = math.hypot(dx, dy)
ux = dx / distance            # 单位向量 (检测器方向)
uy = dy / distance
self.radial_velocity = source_vx * ux + source_vy * uy  # 点积投影
```

- **正数**（显示 `+`）：波源正在靠近检测器 → 蓝移
- **负数**（显示 `-`）：波源正在远离检测器 → 红移
- **接近零**：波源在做切向运动（掠过），无多普勒效应

#### 多普勒频移比（freq_ratio）

声学多普勒效应公式（检测器静止，波源运动）：

```
f_obs = f_src × ─────────
                 c − v_r
```

其中 `c` 是波的传播速度（即 `WAVE_SPEED`），`v_r` 以**靠近检测器为正方向**。

- `freq_ratio > 1`：观测频率高于发射频率（蓝移，波源靠近）
- `freq_ratio < 1`：观测频率低于发射频率（红移，波源远离）
- `freq_ratio = 1`：无频移（波源静止或纯切向运动）

当波源径向速度趋近于波速（`v_r → c`）时，分母趋近于零，频移比趋近于无穷大——物理上对应波源以声速冲向检测器的极限情况。

#### draw() —— 绿色十字标

检测器在屏幕上以绿色十字标显示（[speed_detector.py#L46-L62](speed_detector.py#L46-L62)）：四条短线围绕中心间隙排列，中央有一个小空心圆，上方有 "Detector" 标签。

**为什么事件处理分成两步？**

`pygame.event.get()`（事件队列）和 `pygame.key.get_pressed()`（实时状态）是不同的机制：
- `KEYDOWN` 事件只在按键**按下瞬间**触发一次——适合 R、ESC、+/- 这种一次性操作
- `key.get_pressed()` 返回的是**当前这一帧**的按键状态——适合方向键这种需要按住持续移动的操作

**pygame.display.flip()** 是双缓冲渲染的关键：所有绘制都发生在后台缓冲上，flip() 一次把整帧交换到前台，避免画面撕裂。

**clock.tick(FPS)** 确保每帧耗时固定（1/60 秒），既是帧率上限也是物理时间基准——波速和波频的"每帧"单位依赖这个稳定间隔。

---

## 可调参数与效果

| 参数 | 默认值 | 增大效果 | 减小效果 |
|------|--------|----------|----------|
| `WAVE_SPEED` | 3.0 | 波扩展更快；需保持 > SOURCE_SPEED 才能看到前端波纹 | 波扩展慢；若低于 SOURCE_SPEED 则进入超音速模式 |
| `WAVE_EMIT_INTERVAL` | 22 | 发射更慢，波纹间距大 | 发射更快，波纹间距小（运行时按 +/-） |
| `SOURCE_SPEED` | 2.0 | 多普勒效应更剧烈；≥ WAVE_SPEED 时出现马赫锥 | 效果更微妙 |
| `FPS` | 60 | 物理更细腻，CPU 消耗更高 | 物理变粗糙，可能出现跳帧 |

> **亚音速 vs 超音速**：默认 `SOURCE_SPEED (2.0) < WAVE_SPEED (3.0)` 展示正常多普勒效应——运动前方波纹密集（蓝移）、后方波纹稀疏（红移）。若把两者调成相等或反向，则波源跑得比波还快，前方波纹被全部甩在后面，形成**马赫锥**（Mach cone），即音爆/激波的视觉对应。
