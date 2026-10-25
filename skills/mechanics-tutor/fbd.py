"""受力图（free-body diagram）生成器：模型坐标（米）→ SVG → PNG。

硬性约束：所有颜色只用 #RRGGBB。禁止 rgba()/rgb()/hsl()/颜色名——
SVG→OOXML 编译器会把 rgba(...) 原样写进 <a:srgbClr val="...">，PowerPoint 判定文件损坏。

解释器：<你的 python 解释器>（纯标准库，无需第三方包）

用法（见 SKILL.md 第 4 步）：
    import sys; sys.path.insert(0, r"~/.dsh/skills/mechanics-tutor")
    from fbd import Diagram
    d = Diagram(title="杆 AB 受力")
    d.member((0,0), (1.732,1), label="AB")
    d.support("pin", (0,0), label="A")
    d.force((0.866,0.5), -90, 1.2, label="W")
    d.save(r"C:\\temp\\fbd.svg"); d.png(r"C:\\temp\\fbd.png")
"""
from __future__ import annotations

import math
import os
import subprocess
import sys
import tempfile

# Windows 控制台默认 GBK，中文 lint 输出会乱码；强制 UTF-8
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass

# —— 配色（只用 6 位十六进制）——
INK = "#1f2937"      # 构件、轮廓、文字
APPLY = "#b91c1c"    # 主动力（重力、外载）
REACT = "#1d4ed8"    # 约束反力
DIM = "#6b7280"      # 尺寸线、角度、辅助线
SOFT = "#d1d5db"     # 剖面线/地面填充
BG = "#ffffff"
FONT = "'Microsoft YaHei','Segoe UI',Arial,sans-serif"

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _f(v: float) -> str:
    s = f"{v:.2f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def _xy(p) -> str:
    return f"{_f(p[0])},{_f(p[1])}"


def _rot(p, deg: float, about=(0.0, 0.0)):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    x, y = p[0] - about[0], p[1] - about[1]
    return (about[0] + x * c - y * s, about[1] + x * s + y * c)


def _unit(deg: float):
    a = math.radians(deg)
    return (math.cos(a), math.sin(a))


def _est_width(s: str, size: float) -> float:
    """估算文字宽度（px）：CJK 按 1.0 em，其余按字符类别估。"""
    w = 0.0
    for ch in s:
        o = ord(ch)
        if o > 0x2E80:
            w += 1.0
        elif ch in "il.,:;'|![]()":
            w += 0.32
        elif ch.isupper():
            w += 0.68
        elif ch.isdigit():
            w += 0.56
        elif ch == " ":
            w += 0.30
        else:
            w += 0.54
    return w * size


def _seg_seg(a, b, c, d) -> bool:
    """两条线段是否真交叉。"""
    def cross(o, p, q):
        return (p[0] - o[0]) * (q[1] - o[1]) - (p[1] - o[1]) * (q[0] - o[0])

    d1, d2 = cross(c, d, a), cross(c, d, b)
    d3, d4 = cross(a, b, c), cross(a, b, d)
    return d1 * d2 < 0 and d3 * d4 < 0


def _seg_rect_hit(p, q, poly) -> bool:
    """线段是否穿过凸多边形（poly 为四个角点，支持旋转后的四边形）。"""
    n = len(poly)

    def inside(pt):
        signs = []
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            signs.append((b[0] - a[0]) * (pt[1] - a[1]) - (b[1] - a[1]) * (pt[0] - a[0]))
        return all(s >= -1e-9 for s in signs) or all(s <= 1e-9 for s in signs)

    if inside(p) or inside(q):
        return True
    return any(_seg_seg(p, q, poly[i], poly[(i + 1) % n]) for i in range(n))


def _poly_poly_hit(A, B) -> bool:
    """两个凸多边形是否相交（分离轴定理）。"""
    for poly in (A, B):
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            nx, ny = -(b[1] - a[1]), b[0] - a[0]      # 边的法线
            pa = [nx * x + ny * y for (x, y) in A]
            pb = [nx * x + ny * y for (x, y) in B]
            if max(pa) < min(pb) - 1e-9 or max(pb) < min(pa) - 1e-9:
                return False
    return True


class Diagram:
    """一张受力图。模型坐标 y 轴向上，单位自定（建议米）。"""

    def __init__(self, width=680, height=500, scale=110.0, origin=None, title=None):
        self.w, self.h, self.s = width, height, scale
        self.ox, self.oy = origin if origin else (width * 0.40, height * 0.78)
        self.title = title
        self.body: list[str] = []
        self.colors: set[str] = {INK}
        self._texts: list[tuple] = []    # (bbox, 文字)
        self._segs: list[tuple] = []     # (p, q, 说明) 只记「有分量」的线段

    # —— 坐标 ——
    def P(self, p):
        return (self.ox + p[0] * self.s, self.oy - p[1] * self.s)

    def _len(self, v: float) -> float:
        return v * self.s

    # —— 基本图元 ——
    def _line(self, a, b, color=INK, w=2.0, dash=None, cap="round", opacity=None,
              track=False, tag=""):
        self.colors.add(color)
        if track:
            self._segs.append((a, b, tag or "线"))
        d = f' stroke-dasharray="{dash}"' if dash else ""
        o = f' stroke-opacity="{opacity}"' if opacity else ""
        self.body.append(
            f'<line x1="{_f(a[0])}" y1="{_f(a[1])}" x2="{_f(b[0])}" y2="{_f(b[1])}" '
            f'stroke="{color}" stroke-width="{_f(w)}" stroke-linecap="{cap}"{d}{o}/>'
        )

    def _arrow(self, a, b, color=APPLY, w=2.4, dash=None, head=11.0, shrink=0.0, tag="箭头"):
        self.colors.add(color)
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 0.5:
            return
        if shrink:
            b = (b[0] - dx / L * shrink, b[1] - dy / L * shrink)
        self._segs.append((a, b, tag))
        d = f' stroke-dasharray="{dash}"' if dash else ""
        self.body.append(
            f'<line x1="{_f(a[0])}" y1="{_f(a[1])}" x2="{_f(b[0])}" y2="{_f(b[1])}" '
            f'stroke="{color}" stroke-width="{_f(w)}" stroke-linecap="round"{d} '
            f'marker-end="url(#ah{color[1:]})"/>'
        )

    def _text(self, at, s, color=INK, size=15, anchor="middle", bold=False,
              rotate=None, italic=False):
        self.colors.add(color)
        w = _est_width(str(s), size)
        x0 = at[0] - (w / 2 if anchor == "middle" else (w if anchor == "end" else 0))
        hh = size * 0.62
        corners = [(x0, at[1] - hh), (x0 + w, at[1] - hh),
                   (x0 + w, at[1] + hh), (x0, at[1] + hh)]
        if rotate:
            corners = [_rot(c, rotate, at) for c in corners]
        self._texts.append((corners, str(s)))
        tr = f' transform="rotate({_f(rotate)} {_f(at[0])} {_f(at[1])})"' if rotate else ""
        fw = ' font-weight="700"' if bold else ""
        fs = ' font-style="italic"' if italic else ""
        self.body.append(
            f'<text x="{_f(at[0])}" y="{_f(at[1])}" fill="{color}" font-size="{size}" '
            f'font-family="{FONT}" text-anchor="{anchor}" dominant-baseline="middle"'
            f'{fw}{fs}{tr}>{s}</text>'
        )

    def _label_at(self, at_px, text, color, lx=0.0, ly=0.0, anchor="middle", size=15, bold=False):
        if not text:
            return
        self._text((at_px[0] + lx, at_px[1] + ly), text, color=color, size=size,
                   anchor=anchor, bold=bold)

    # —— 对外 API（全部用模型坐标）——
    def sleeve(self, at, ang, length=0.16, width=0.09, color=INK, lw=1.8,
               dot=True, fill=BG):
        """套筒 / 滑块：中心在 at、沿 ang 方向的长方形（模型单位），中间画铰点。"""
        ux, uy = _unit(ang)
        nx, ny = -uy, ux
        c = self.P(at)
        hl, hw = self._len(length) / 2, self._len(width) / 2
        pts = []
        for a, b in ((1, 1), (1, -1), (-1, -1), (-1, 1)):
            dx = ux * hl * a + nx * hw * b
            dy = uy * hl * a + ny * hw * b
            pts.append((c[0] + dx, c[1] - dy))
        self.colors.add(color)
        self.body.append(
            f'<polygon points="{" ".join(_xy(p) for p in pts)}" fill="{fill}" '
            f'stroke="{color}" stroke-width="{_f(lw)}" stroke-linejoin="round"/>'
        )
        if dot:
            self.body.append(
                f'<circle cx="{_f(c[0])}" cy="{_f(c[1])}" r="3.8" fill="{color}"/>'
            )

    def hinge(self, at, r=6.0, color=INK, fill=BG, lw=2.0, dot=False):
        """铰链小圆圈（墙上/板上的销轴）。r 为像素半径。"""
        c = self.P(at)
        self.colors.add(color)
        self.body.append(
            f'<circle cx="{_f(c[0])}" cy="{_f(c[1])}" r="{_f(r)}" fill="{fill}" '
            f'stroke="{color}" stroke-width="{_f(lw)}"/>'
        )
        if dot:
            self.body.append(f'<circle cx="{_f(c[0])}" cy="{_f(c[1])}" r="2.2" fill="{color}"/>')

    def member(self, a, b, label="", lw=5.0, color=INK, dash=None,
               off=(0.0, 0.0), label_color=None, double=False, label_t=0.5):
        """构件（杆/梁/绳的实体）。off 为标签偏移（模型单位），label_t 为标签沿线位置（0=a,1=b）。"""
        pa, pb = self.P(a), self.P(b)
        self._line(pa, pb, color=color, w=lw, dash=dash, track=True, tag="构件")
        if double:                      # 双线表示厚度
            d = 4.0
            self._line((pa[0], pa[1] + d), (pb[0], pb[1] + d), color=color, w=1.6)
            self._line((pa[0], pa[1] - d), (pb[0], pb[1] - d), color=color, w=1.6)
        if label:
            mid = (pa[0] + (pb[0] - pa[0]) * label_t + off[0] * self.s,
                   pa[1] + (pb[1] - pa[1]) * label_t - off[1] * self.s)
            self._text(mid, label, color=label_color or color, size=16, bold=True)

    bar = member

    def rope(self, a, b, label="", off=(0.0, 0.0)):
        """柔索：细虚线之外的实线细线 + 双箭头表示只能受拉。"""
        pa, pb = self.P(a), self.P(b)
        self._line(pa, pb, color=INK, w=1.8, track=True, tag="柔索")
        if label:
            mid = ((pa[0] + pb[0]) / 2 + off[0] * self.s, (pa[1] + pb[1]) / 2 - off[1] * self.s)
            self._text(mid, label, color=INK, size=16, bold=True)

    def force(self, at, ang, length, label="", color=APPLY, lw=2.6,
              lab_off=(0.0, 0.0), lab_anchor="middle", tip=True, dash=None, bold=True):
        """集中力：从 at 沿 ang 度（数学惯例，y 向上，逆时针为正）画出 length（模型单位）。"""
        ux, uy = _unit(ang)
        tail = at if tip else (at[0] - ux * length, at[1] - uy * length)
        head = (tail[0] + ux * length, tail[1] + uy * length)
        pa, pb = self.P(tail), self.P(head)
        self._arrow(pa, pb, color=color, w=lw, dash=dash)
        if label:
            # 沿力方向自动外推，保证标签不压在箭头上
            w = _est_width(label, 16)
            push = 8 + (w / 2) * abs(ux) + 12 * abs(uy)
            lx = pb[0] + ux * push + lab_off[0]
            ly = pb[1] - uy * push + lab_off[1]
            self._text((lx, ly), label, color=color, size=16, anchor=lab_anchor, bold=bold)

    def force_vec(self, at, vec, label="", color=APPLY, **kw):
        """用力矢量 (dx, dy) 指定方向和长度（模型单位）；长度按矢量长度。"""
        L = math.hypot(vec[0], vec[1])
        ang = math.degrees(math.atan2(vec[1], vec[0]))
        self.force(at, ang, L, label=label, color=color, **kw)

    def reaction(self, at, ang, length, label="", **kw):
        """约束反力（蓝色）。"""
        kw.pop("color", None)
        self.force(at, ang, length, label=label, color=REACT, **kw)

    def couple(self, center, radius, label="", ccw=True, color=DIM, lw=2.2, lab_off=None):
        """力偶：圆弧箭头，半径 radius（模型单位）。"""
        self.colors.add(color)
        c = self.P(center)
        r = self._len(radius)
        # 起点在 +x 方向，逆时针画 300°
        a0 = 20.0
        a1 = a0 + (300.0 if ccw else -300.0)
        x0, y0 = c[0] + r * math.cos(math.radians(a0)), c[1] - r * math.sin(math.radians(a0))
        x1, y1 = c[0] + r * math.cos(math.radians(a1)), c[1] - r * math.sin(math.radians(a1))
        large = 1 if abs(a1 - a0) > 180 else 0
        sweep = 0 if ccw else 1
        self.body.append(
            f'<path d="M {_f(x0)} {_f(y0)} A {_f(r)} {_f(r)} 0 {large} {sweep} {_f(x1)} {_f(y1)}" '
            f'fill="none" stroke="{color}" stroke-width="{_f(lw)}" stroke-linecap="round" '
            f'marker-end="url(#ah{color[1:]})"/>'
        )
        if label:
            if lab_off is None:          # 自动放到圆弧对侧，省掉手调一轮
                am = math.radians(170.0)
                lab_off = ((r + 22) * math.cos(am), -(r + 22) * math.sin(am))
            self._text((c[0] + lab_off[0], c[1] + lab_off[1]), label,
                       color=color, size=16, bold=True)

    def support(self, kind="pin", at=(0, 0), rot=0.0, size=1.0, color=INK, label="",
                span=34):
        """支座。kind: pin(铰链) roller(辊轴) fix(固定端/墙) ground(地面线)。

        rot: 支座朝向角度（度，0=支座在下方顶住构件）。
        span: 仅 ground 用，地面线向两侧各伸出多少 px（默认 34，画长地面就调大）。
        """
        self.colors.add(color)
        c = self.P(at)
        k = size
        # 局部坐标（屏幕像素，y 向下），支座位在构件下方
        def L(p):
            return _rot((c[0] + p[0] * k, c[1] + p[1] * k), rot, about=c)

        if kind in ("pin", "roller"):
            tri = [L((0, 0)), L((-11, 16)), L((11, 16))]
            self.body.append(
                f'<polygon points="{_xy(tri[0])} {_xy(tri[1])} {_xy(tri[2])}" '
                f'fill="none" stroke="{color}" stroke-width="1.8" stroke-linejoin="round"/>'
            )
            if kind == "pin":           # 铰链：加个小圆
                self.body.append(
                    f'<circle cx="{_f(c[0])}" cy="{_f(c[1])}" r="{_f(3.6 * k)}" '
                    f'fill="{color}" stroke="none"/>'
                )
            base_a, base_b = L((-15, 16)), L((15, 16))
            self._line(base_a, base_b, color=color, w=1.8)
            if kind == "roller":
                for t in (-9, 0, 9):
                    cc = L((t, 19.5))
                    self.body.append(
                        f'<circle cx="{_f(cc[0])}" cy="{_f(cc[1])}" r="{_f(2.8 * k)}" '
                        f'fill="none" stroke="{color}" stroke-width="1.4"/>'
                    )
                base_a, base_b = L((-15, 24)), L((15, 24))
                self._line(base_a, base_b, color=color, w=1.8)
                self._hatch(L((-15, 24)), L((15, 24)), n=5, length=8 * k, color=color, side=1)
            else:
                self._hatch(base_a, base_b, n=5, length=9 * k, color=color, side=1)

        elif kind == "fix":             # 固定端：垂直于构件的墙线 + 剖面线
            a, b = L((-16, 0)), L((16, 0))
            self._line(a, b, color=color, w=2.6)
            self._hatch(a, b, n=6, length=10 * k, color=color, side=1)

        elif kind == "ground":          # 地面线
            a, b = L((-span, 0)), L((span, 0))
            self._line(a, b, color=color, w=2.2)
            self._hatch(a, b, n=max(6, int(span / 2.4)), length=9 * k, color=color, side=1)

        if label:
            lp = L((0, 30))
            self._text((lp[0], lp[1] + 6), label, color=color, size=16, bold=True)

    def wall(self, a, b, side=1, label="", ticks=8, color=INK):
        """墙面：实线 + 剖面线。side=1 → 剖面线在 a→b 的法线侧（竖墙自下而上画时朝右）。"""
        pa, pb = self.P(a), self.P(b)
        self._line(pa, pb, color=color, w=3.0)
        self._hatch(pa, pb, n=ticks, length=11, color=color, side=side)
        if label:
            mid = ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2 + 16)
            self._text(mid, label, color=color, size=15)

    def _hatch(self, a, b, n=6, length=9.0, color=DIM, side=1, w=1.4):
        """沿线段画剖面线：垂直该线段朝 side 一侧（side=1 → 屏幕坐标下 b→a 的右侧）。"""
        self.colors.add(color)
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1.0
        ux, uy = dx / L, dy / L
        nx, ny = -uy * side, ux * side          # 法线
        for i in range(n):
            t = (i + 0.5) / n
            x, y = a[0] + dx * t, a[1] + dy * t
            self._line((x, y), (x + nx * length - ux * length * 0.6,
                                y + ny * length - uy * length * 0.6),
                       color=color, w=w, opacity=0.85)

    def dist_load(self, a, b, h1, h2=None, label="", color=APPLY, n=6,
                  direction=-90.0, label_off=(0, 0)):
        """分布载荷。a,b 为梁上受载区间端点；h1,h2 为两端图示高度（模型单位）。

        箭头沿 direction 指向梁体（默认竖直向下 = -90）。
        """
        h2 = h1 if h2 is None else h2
        ux, uy = _unit(direction)                 # 箭头指向
        # 尾端（外轮廓）在 a/b 的反方向偏移
        ta = (a[0] - ux * h1, a[1] - uy * h1)
        tb = (b[0] - ux * h2, b[1] - uy * h2)
        mids = []
        for i in range(n):
            t = (i + 0.5) / n if n > 1 else 0.5
            sa = (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            top = (sa[0] - ux * (h1 + (h2 - h1) * t), sa[1] - uy * (h1 + (h2 - h1) * t))
            self._arrow(self.P(top), self.P(sa), color=color, w=1.8, head=9.0, shrink=1.0)
            mids.append(top)
        # 外轮廓线
        pta, ptb = self.P(ta), self.P(tb)
        self._line(pta, ptb, color=color, w=2.0)
        if label:
            mid = ((pta[0] + ptb[0]) / 2 + label_off[0], (pta[1] + ptb[1]) / 2 - 12 + label_off[1])
            self._text(mid, label, color=color, size=16, bold=True)

    def dim(self, a, b, offset=0.5, text="", color=DIM, orient="auto", size=14,
            side=1, arrows=True):
        """尺寸线。offset 为法向偏移（模型单位，正值指向 a→b 的左侧 * side）。"""
        pa, pb = self.P(a), self.P(b)
        dx, dy = pb[0] - pa[0], pb[1] - pa[1]
        L = math.hypot(dx, dy)
        if L < 1:
            return
        nx, ny = -dy / L * side, dx / L * side
        off = self._len(offset)
        a2 = (pa[0] + nx * off, pa[1] + ny * off)
        b2 = (pb[0] + nx * off, pb[1] + ny * off)
        self._line(pa, a2, color=color, w=1.0, opacity=0.8)
        self._line(pb, b2, color=color, w=1.0, opacity=0.8)
        if arrows:
            self._line(a2, b2, color=color, w=1.2)
            self._arrow(a2, b2, color=color, w=1.2, head=8.0)
            self._arrow(b2, a2, color=color, w=1.2, head=8.0)
        else:
            self._line(a2, b2, color=color, w=1.2, dash="5 4")
        if text:
            mid = ((a2[0] + b2[0]) / 2 + nx * 12, (a2[1] + b2[1]) / 2 + ny * 12)
            if orient == "h":
                self._text(mid, text, color=color, size=size)
            else:                       # auto/along：文字随尺寸线旋转，斜杆也能标
                deg = math.degrees(math.atan2(dy, dx))
                if deg > 90 or deg < -90:
                    deg += 180
                self._text(mid, text, color=color, size=size, rotate=deg)

    def angle(self, center, a1, a2, r, text="", color=DIM, size=14, lab_dr=0.0):
        """角度标记：从 a1 逆时针画弧到 a2（度）。"""
        self.colors.add(color)
        c = self.P(center)
        R = self._len(r)
        p0 = (c[0] + R * math.cos(math.radians(a1)), c[1] - R * math.sin(math.radians(a1)))
        p1 = (c[0] + R * math.cos(math.radians(a2)), c[1] - R * math.sin(math.radians(a2)))
        large = 1 if abs(a2 - a1) > 180 else 0
        sweep = 0 if a2 > a1 else 1
        self.body.append(
            f'<path d="M {_f(p0[0])} {_f(p0[1])} A {_f(R)} {_f(R)} 0 {large} {sweep} '
            f'{_f(p1[0])} {_f(p1[1])}" fill="none" stroke="{color}" stroke-width="1.4"/>'
        )
        if text:
            am = math.radians((a1 + a2) / 2)
            tr = R + 14 + self._len(lab_dr)
            self._text((c[0] + tr * math.cos(am), c[1] - tr * math.sin(am)),
                       text, color=color, size=size)

    def text(self, at, s, color=INK, size=15, anchor="middle", bold=False, dy=0.0):
        pa = self.P(at)
        self._text((pa[0], pa[1] + dy), s, color=color, size=size, anchor=anchor, bold=bold)

    def legend(self, items, at=(0.0, 0.0), color=INK, size=14, dy=20):
        """图例：items = [(颜色, 文字), ...]，位置为模型坐标（图内）。"""
        pa = self.P(at)
        for i, (col, label) in enumerate(items):
            y = pa[1] + i * dy
            self._line((pa[0], y), (pa[0] + 22, y), color=col, w=3.0)
            self._text((pa[0] + 28, y), label, color=color, size=size, anchor="start")

    # —— 输出 ——
    def lint(self, quiet=False) -> list:
        """排版检查。返回**硬冲突**列表（文字互压、出画布）；压线只作提示。

        文字按真实四边形（含旋转）判碰撞，旋转的尺寸标注不会误报。
        文字压在箭头/构件线上属于教科书里也常见的正常情况，只提示不算失败。
        """
        hard, soft = [], []
        t = self._texts
        if self.title:            # 标题也占版面，文字压标题算硬冲突
            from_w = _est_width(self.title, 17)
            t = t + [([(self.w / 2 - from_w / 2, 10), (self.w / 2 + from_w / 2, 10),
                      (self.w / 2 + from_w / 2, 44), (self.w / 2 - from_w / 2, 44)],
                     '标题')]
        for i in range(len(t)):
            (pa_, sa) = t[i]
            for j in range(i + 1, len(t)):
                (pb_, sb) = t[j]
                if _poly_poly_hit(pa_, pb_):
                    hard.append(f"文字重叠：「{sa}」×「{sb}」")
        for (poly, s) in t:
            for (p, q, tag) in self._segs:
                if _seg_rect_hit(p, q, poly):
                    soft.append(f"文字压{tag}：「{s}」")
        for (poly, s) in t:
            xs = [c[0] for c in poly]
            ys = [c[1] for c in poly]
            if min(xs) < 0 or min(ys) < 0 or max(xs) > self.w or max(ys) > self.h:
                hard.append(f"出画布：「{s}」")
        for (p, q, tag) in self._segs:
            for pt in (p, q):
                if not (-1 <= pt[0] <= self.w + 1 and -1 <= pt[1] <= self.h + 1):
                    hard.append(f"出画布：{tag}")
                    break
        if not quiet:
            for m in hard:
                print(f"  [lint] {m}")
            for m in soft:
                print(f"  [提示] {m}（可接受，想更好看就调 off/lab_off）")
            if hard:
                print(f"[lint] {len(hard)} 处硬冲突：文字重叠或出画布，必须调完再出图")
            else:
                print("[lint] 0 硬冲突，可交图")
        return hard

    def _defs(self) -> str:
        out = []
        for col in sorted(self.colors):
            out.append(
                f'<marker id="ah{col[1:]}" viewBox="0 0 10 10" refX="8.5" refY="5" '
                f'markerWidth="10" markerHeight="10" markerUnits="userSpaceOnUse" '
                f'orient="auto-start-reverse">'
                f'<path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>'
            )
        return "<defs>" + "".join(out) + "</defs>"

    def svg(self) -> str:
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}">'
        )
        title = ""
        if self.title:
            title = (f'<text x="{self.w / 2}" y="26" fill="{INK}" font-size="17" '
                     f'font-family="{FONT}" text-anchor="middle" font-weight="700">'
                     f'{self.title}</text>')
        return (head + self._defs() +
                f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="{BG}"/>' +
                title + "".join(self.body) + "</svg>")

    def save(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.svg())
        return os.path.abspath(path)

    def png(self, path: str, scale=2, edge=None) -> str:
        """SVG → PNG（headless Edge 截图）。返回 PNG 绝对路径。会自动跑排版检查。"""
        self.lint()
        svg_path = os.path.splitext(os.path.abspath(path))[0] + ".svg"
        self.save(svg_path)
        return render_png(svg_path, path, self.w, self.h, scale=scale, edge=edge)


def find_edge() -> str:
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("找不到 msedge.exe，改用 SVG 直接贴图")


def render_png(svg_path: str, png_path: str, width: int, height: int,
               scale=2, edge=None) -> str:
    """用 headless Edge 把 SVG 截成 PNG（经 HTML 包装，保证尺寸精确）。"""
    edge = edge or find_edge()
    svg_abs = os.path.abspath(svg_path).replace("\\", "/")
    html_path = os.path.splitext(os.path.abspath(svg_path))[0] + "_render.html"
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(
            '<!doctype html><html><head><meta charset="utf-8">'
            '<style>html,body{margin:0;padding:0;background:#ffffff;}</style></head>'
            f'<body><img src="file:///{svg_abs}" width="{width}" height="{height}" '
            'style="display:block"></body></html>'
        )
    png_abs = os.path.abspath(png_path)
    os.makedirs(os.path.dirname(png_abs) or ".", exist_ok=True)
    profile = os.path.join(tempfile.gettempdir(), "dsh-fbd-edge-profile")
    base = [edge, "--disable-gpu", "--hide-scrollbars", "--no-first-run",
            "--disable-extensions", f"--user-data-dir={profile}",
            f"--force-device-scale-factor={scale}",
            f"--window-size={width},{height}",
            f"--screenshot={png_abs}"]
    for mode in ("--headless=new", "--headless"):
        try:
            r = subprocess.run(base[:1] + [mode] + base[1:] +
                               ["file:///" + html_path.replace("\\", "/")],
                               capture_output=True, timeout=180)
        except subprocess.TimeoutExpired:
            continue
        if os.path.exists(png_abs) and os.path.getsize(png_abs) > 1000:
            return png_abs
    raise SystemExit(f"Edge 截图失败（返回码 {r.returncode}）：{r.stderr[-400:]!r}")


if __name__ == "__main__":
    # 自检：画一道铰支杆 + 柔索 + 重力的受力图
    d = Diagram(title="自检图：杆 AB")
    d.wall((0, 0), (0, 2.6), side=1, label="墙")
    d.member((0, 0), (1.732, 1.0), label="AB", off=(0.18, -0.12))
    d.member((1.732, 1.0), (0, 2.0), lw=1.8)
    d.support("pin", (0, 0), label="A")
    d.force((0.866, 0.5), -90, 1.1, label="W")
    d.force((1.732, 1.0), 150, 0.9, label="T", color=APPLY)
    d.reaction((0, 0), 0, 0.7, label="X_A", lab_off=(0, -14))
    d.reaction((0, 0), 90, 0.9, label="Y_A", lab_off=(-16, 0))
    d.angle((0, 0), 30, 90, 0.55, text="60°")
    d.dim((0, 0), (0.866, 0.5), offset=-0.35, text="L/2", side=-1)
    out = os.path.join(tempfile.gettempdir(), "fbd_selfcheck")
    print(d.save(out + ".svg"))
    print(d.png(out + ".png"))
