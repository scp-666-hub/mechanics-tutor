"""常见静力学题型 → 受力图骨架。改参数就出图，不用再调坐标。

用法：
    import sys; sys.path.insert(0, r"~/.dsh/skills/mechanics-tutor")
    from templates import ladder_wall
    print(ladder_wall(theta=59.0, mu=0.3).png(r"C:\\CTMP\\a.png"))

每个函数返回 fbd.Diagram，可以继续 d.force(...) 加点东西，也可以直接 png()。
尺寸约定：模型单位按「1 m 左右的题」设计，比例不对就改 scale。
"""
import math

from fbd import Diagram, APPLY, REACT, DIM, INK

__all__ = [
    "beam_simple", "beam_cantilever", "block_incline", "ladder_wall",
    "two_rope_knot", "slider_rod", "box_between_rails", "truss_triangle",
    "crank_slider",
]


def _u(ang):
    a = math.radians(ang)
    return (math.cos(a), math.sin(a))


# ────────────────────────────── 梁 ──────────────────────────────
def beam_simple(L=1.0, xF=0.35, dist_from=None, dist_to=None, q=0.30,
                show_reactions=True, scale=360):
    """简支梁（左铰支 + 右辊轴），可带集中力、均布载荷。"""
    d = Diagram(width=780, height=430, scale=scale, origin=(170, 290),
                title="简支梁受力图")
    d.support("ground", (0, 0), span=230, size=0.85)
    d.member((0, 0), (L, 0), lw=6.0)
    d.support("pin", (0, 0), size=0.8)
    d.support("roller", (L, 0), size=0.8)
    if dist_from is not None:
        d.dist_load((dist_from, 0), (dist_to, 0), q, label="q")
    d.force((xF, 0), -90, 0.30, label="F")
    if show_reactions:
        d.reaction((0, 0), 90, 0.42, label="Y_A", lab_off=(-22, 0))
        d.reaction((L, 0), 90, 0.42, label="Y_B", lab_off=(22, 0))
        d.reaction((0, 0), 0, 0.30, label="X_A", lab_off=(0, 24))
    d.dim((0, 0), (L, 0), offset=0.14, text="L", side=1)
    return d


def beam_cantilever(L=1.0, q=None, scale=340):
    """悬臂梁：左端固支，自由端受集中力（给 q 加均布载荷）。"""
    d = Diagram(width=780, height=450, scale=scale, origin=(240, 250),
                title="悬臂梁受力图")
    d.support("fix", (0, 0), rot=90, size=1.1)
    d.member((0, 0), (L, 0), lw=6.0)
    if q is not None:
        d.dist_load((L * 0.40, 0), (L, 0), q, label="q")
    d.force((L, 0), -90, 0.42, label="F")
    d.text((0.10, -0.22), "M_A", color=DIM, size=16, anchor="start")
    d.dim((0, 0), (L, 0), offset=0.12, text="L", side=-1)
    return d


# ────────────────────────────── 摩擦 ──────────────────────────────
def block_incline(alpha=30.0, mu=0.3, scale=340):
    """斜面滑块：重力、法向反力、沿斜面向上的摩擦。"""
    d = Diagram(width=720, height=480, scale=scale, origin=(170, 395),
                title=f"斜面滑块（α = {alpha:g}°）")
    a = _u(alpha)
    run = 1.5
    d.member((0, 0), (run * a[0], run * a[1]), lw=4.0)
    d.support("ground", (0, 0), span=110, size=0.85)
    nrm = (-a[1], a[0])
    on = (0.75 * a[0], 0.75 * a[1])
    base = (on[0] + nrm[0] * 0.12, on[1] + nrm[1] * 0.12)
    d.sleeve(base, alpha, length=0.30, width=0.24, dot=False)
    d.force(base, -90, 0.50, label="W")
    d.reaction(base, alpha + 90, 0.42, label="N", lab_off=(12, -4))
    d.force(base, alpha, 0.45, label="F", lab_off=(6, -16))
    d.angle((0, 0), 0, alpha, 0.42, text=f"{alpha:g}°")
    d.text((run * a[0] - 0.04, run * a[1] + 0.16), f"f = {mu:g}", color=DIM,
           size=13, anchor="end")
    return d


def ladder_wall(theta=60.0, mu=0.3, L=1.0, scale=250):
    """梯子：A 端粗糙地面、B 端靠光滑竖墙，θ 为与地面夹角。"""
    d = Diagram(width=700, height=620, scale=scale, origin=(210, 500),
                title=f"梯子受力图（θ = {theta:g}°）")
    B = (L * math.cos(math.radians(theta)), L * math.sin(math.radians(theta)))
    G = (B[0] / 2, B[1] / 2)
    d.support("ground", (0, 0), span=120, size=0.85)
    d.wall((B[0], 0), (B[0], B[1] + 0.55), side=1)
    d.member((0, 0), B, lw=6.0, label="AB", off=(-0.14, 0.02), label_t=0.55)
    d.support("pin", (0, 0), size=0.85)
    d.force(G, -90, 0.60, label="W")
    d.reaction((0, 0), 90, 0.50, label="N_A")
    d.reaction((0, 0), 0, 0.45, label="f")
    d.reaction(B, 180, 0.50, label="N_B")
    d.angle((0, 0), 0, theta, 0.36, text=f"θ={theta:g}°")
    d.text((-0.30, 0.10), f"f = {mu:g}", color=DIM, size=13, anchor="end")
    return d


# ────────────────────────── 三力汇交 / 二力杆 ──────────────────────────
def two_rope_knot(a_left=115.0, a_right=55.0, scale=300):
    """重物用两根索吊在天花板上，求两索张力（三力汇交）。角度从 +x 轴量。"""
    d = Diagram(width=800, height=620, scale=scale, origin=(250, 430),
                title="两索吊重　三力汇交")
    ceil_y = 0.95
    d.member((-0.15, ceil_y), (1.30, ceil_y), lw=3.0)
    d._hatch(d.P((-0.15, ceil_y)), d.P((1.30, ceil_y)), n=12, length=10,
             color=INK, side=-1)
    O = (0.55, 0.0)
    for ang, lab in ((a_left, "T_A"), (a_right, "T_B")):
        u = _u(ang)
        t = (ceil_y - O[1]) / u[1]
        d.rope(O, (O[0] + u[0] * t, O[1] + u[1] * t), label=lab,
              off=(-0.14 if u[0] < 0 else 0.14, 0.03))
        d.force(O, ang, 0.40, label="", color=APPLY)
    d.force(O, -90, 0.42, label="P")
    d.hinge(O, r=4)
    d.angle(O, a_right, 90, 0.26, text="", color=DIM)
    return d


# ─────────────────────────── 机构：套筒滑块 ───────────────────────────
def slider_rod(scale=280):
    """套筒滑块双杆机构（题 4-16 骨架）：C 在下、A 在上，两杆各成 30°。"""
    l = 1.0
    h = l / math.sqrt(3)
    C, A = (0.0, 0.0), (0.0, h)
    u1 = _u(30)
    B = (l / 2, math.sqrt(3) * l / 2)
    D = (A[0] + 1.12 * u1[0], A[1] + 1.12 * u1[1])
    MCp = (0.34 * _u(60)[0], 0.34 * _u(60)[1])
    d = Diagram(width=820, height=660, scale=scale, origin=(230, 560),
                title="套筒滑块机构受力图")
    d.wall((0, -0.20), (0, 1.30), side=-1, ticks=11)
    d.hinge(A, r=7)
    d.hinge(C, r=7)
    d.member(A, D, lw=6.5, label="AD", off=(-0.07, 0.15), label_t=0.78)
    d.member(C, B, lw=6.5, label="CB", off=(0.20, -0.02), label_t=0.50)
    d.sleeve(B, 30, length=0.20, width=0.115)
    d.text((-0.10, h + 0.05), "A", size=17, bold=True, anchor="end")
    d.text((-0.10, -0.05), "C", size=17, bold=True, anchor="end")
    d.text((D[0] + 0.03, D[1] + 0.07), "D", size=17, bold=True, anchor="start")
    d.text((B[0] + 0.03, B[1] - 0.14), "B", size=17, bold=True, anchor="start")
    d.couple(A, 0.115, label="M_A", ccw=False, lab_off=(-46, -44))
    d.couple(MCp, 0.095, label="M_C", ccw=True, lab_off=(58, -6))
    d.reaction(B, 120, 0.30, label="N", lab_off=(-10, -10))
    d.force(B, 30, 0.28, label="F", lab_off=(8, -20))
    d.angle(C, 60, 90, 0.24, text="30°", lab_dr=0.05)
    d.angle(B, 210, 240, 0.15, text="30°", lab_dr=0.12)
    d.dim(C, B, offset=0.34, text="l", side=1)
    return d


# ───────────────────────── 机构：升降箱卡滞 ─────────────────────────
def box_between_rails(a=1.4, b=1.0, off_ratio=0.25, scale=230,
                      ascending=True):
    """升降箱卡在两条竖直滑道间（题 4-20 骨架）。off_ratio = 偏心/箱宽。"""
    d = Diagram(width=680, height=830, scale=scale, origin=(340, 505),
                title="升降箱受力图")
    hb, ha = b / 2, a / 2
    d.wall((-hb, -ha - 0.10), (-hb, ha + 0.10), side=-1, ticks=7)
    d.wall((hb, -ha - 0.10), (hb, ha + 0.10), side=1, ticks=7)
    for p, q in (((-hb, ha), (hb, ha)), ((-hb, -ha), (hb, -ha)),
                 ((-hb, -ha), (-hb, ha)), ((hb, -ha), (hb, ha))):
        d.member(p, q, lw=3.2)
    d.force((0, 0.06), -90, 0.42, label="", color=APPLY)
    d.text((-0.075, 0.20), "C", size=17, bold=True, anchor="end")
    d.text((0.055, 0.10), "P₁", size=16, bold=True, anchor="start", color=APPLY)
    x2 = hb - off_ratio * b
    d.force((x2, -0.16), -90, 0.36, label="", color=APPLY)
    d.text((x2 - 0.035, -0.10), "P₂", size=16, bold=True, anchor="end",
           color=APPLY)
    d.force((0, ha), 90, 0.40, label="", color=REACT)
    d.text((-0.06, ha + 0.46), "P₃", size=16, bold=True, anchor="end",
           color=REACT)
    s = -1 if ascending else 1
    d.reaction((hb, ha), 180, 0.26, label="")
    d.text((hb - 0.30, ha + 0.07), "N", size=16, bold=True, anchor="end",
           color=REACT)
    d.force((hb - 0.02, ha), 90 * s, 0.22, label="", color=APPLY)
    d.text((hb + 0.05, ha - 0.17 * (-s)), "F", size=16, bold=True,
           anchor="start", color=APPLY)
    d.reaction((-hb, -ha), 0, 0.26, label="")
    d.text((-hb + 0.30, -ha + 0.07), "N", size=16, bold=True, anchor="start",
           color=REACT)
    d.force((-hb + 0.02, -ha), 90 * s, 0.22, label="", color=APPLY)
    d.text((-hb + 0.05, -ha + 0.17 * (-s)), "F", size=16, bold=True,
           anchor="start", color=APPLY)
    d.dim((-hb, -ha), (-hb, ha), offset=0.26, text="a", side=-1)
    d.dim((-hb, -ha), (hb, -ha), offset=0.32, text="b", side=1)
    d.dim((hb, -ha + 0.02), (x2, -ha + 0.02), offset=0.16,
          text="b/4" if abs(off_ratio - 0.25) < 1e-9 else f"{off_ratio:g}b",
          side=1, size=12)
    return d


# ────────────────────────────── 桁架 ──────────────────────────────
def truss_triangle(base=1.2, height=0.7, scale=300):
    """三角形桁架骨架：A 铰支、B 辊轴、顶点 C 受竖载。"""
    d = Diagram(width=780, height=580, scale=scale, origin=(200, 430),
                title="三角桁架受力图")
    A, B = (0.0, 0.0), (base, 0.0)
    C = (base / 2, height)
    d.support("ground", (0, 0), span=100, size=0.85)
    d.member(A, C, lw=5.0, label="AC", off=(-0.13, 0.0), label_t=0.55)
    d.member(C, B, lw=5.0, label="CB", off=(0.13, 0.0), label_t=0.45)
    d.member(A, B, lw=5.0, label="AB", off=(0.0, 0.09), label_t=0.50)
    d.support("pin", A, size=0.78)
    d.support("roller", B, size=0.78)
    d.text((-0.09, 0.10), "A", size=17, bold=True, anchor="end")
    d.text((base + 0.09, 0.10), "B", size=17, bold=True, anchor="start")
    d.text((C[0], C[1] + 0.16), "C", size=17, bold=True, anchor="middle")
    d.force(C, -90, 0.38, label="P")
    d.reaction(A, 90, 0.38, label="Y_A", lab_off=(-20, 0))
    d.reaction(A, 0, 0.32, label="X_A", lab_off=(0, 18))
    d.reaction(B, 90, 0.38, label="Y_B", lab_off=(20, 0))
    d.dim((0, 0), (base, 0), offset=0.13, text="d", side=1)
    return d


# ─────────────────────── 曲柄连杆滑块机构 ───────────────────────
def crank_slider(theta=40.0, beta=25.0, two_panel=True, scale=108):
    """曲柄连杆滑块机构（《理论力学》4-17 一类）。

    OA 水平、在 O 处铰支，曲柄上力偶 M（**逆时针**，与题图一致）；
    连杆 AB 与铅垂线夹角 theta（度），滑块 B 落在地面、与地面有摩擦；
    F 作用在滑块上，与水平成 beta（度）、指向左下方压向滑块。
    two_panel=True 时右侧附「滑块 B 分离体」（N、F_f、R、F）。
    """
    th = math.radians(theta)
    Ax, Ay, Ox, Oy = 0.8, 2.0, 2.4, 2.0
    bw, bh = 0.92, 0.36
    Bx = Ax + (Ay - bh / 2) * math.tan(th)
    By = bh / 2

    d = Diagram(width=1240 if two_panel else 700, height=700, scale=scale,
                origin=(90, 600), title="曲柄连杆滑块机构受力分析")

    # 地面
    d.support("ground", (2.0, 0.0), span=560)
    if two_panel:
        d.support("ground", (7.4, 0.0), span=380)

    # ── (a) 机构 ──
    bx0, bx1 = Bx - bw / 2, Bx + bw / 2
    for a, b in (((bx0, 0), (bx1, 0)), ((bx1, 0), (bx1, bh)),
                 ((bx1, bh), (bx0, bh)), ((bx0, bh), (bx0, 0))):
        d.member(a, b, lw=3)
    d.hinge((Bx, By), r=5, dot=False)
    d.text((Bx - 0.34, By - 0.02), "B", size=16, bold=True)

    d.member((Ax, Ay), (Ox, Oy), label="OA", lw=5, off=(0.0, 0.24), label_t=0.16)
    d.hinge((Ax, Ay), r=5, dot=False)
    d.text((Ax - 0.28, Ay + 0.16), "A", size=16, bold=True)
    d.hinge((Ox, Oy), r=6, dot=False)
    d.text((Ox + 0.10, Oy + 0.22), "O", size=16, bold=True)
    d.wall((Ox + 0.18, Oy - 0.45), (Ox + 0.18, Oy + 0.45), side=1)
    d.member((Ox, Oy), (Ox + 0.18, Oy), lw=2)

    d.member((Ax, Ay), (Bx, By), label="AB", lw=4, off=(-0.24, 0.02), label_t=0.45)
    d.couple((1.90, 2.0), 0.32, label="M", ccw=True)

    d.member((Ax, Ay), (Ax, 1.15), lw=1.2, dash="6 5")
    d.angle((Ax, Ay), -90, -90 + theta, 0.52, text="θ")

    d.member((bx1, By), (bx1 + 0.72, By), lw=1.2, dash="6 5")
    d.force((bx1, By), 180 + beta, 0.95, label="F", tip=False, lab_off=(52, -30))
    d.angle((bx1, By), 180, 180 + beta, 0.62, text="")
    d.text((bx1 + 0.62, By + 0.14), "β", size=15)
    d.text((1.55, 2.72), "（a）机构", size=15)

    if not two_panel:
        return d

    # ── (b) 滑块 B 分离体 ──
    bx = 7.4
    ex0, ex1 = bx - bw / 2, bx + bw / 2
    for a, b in (((ex0, 0), (ex1, 0)), ((ex1, 0), (ex1, bh)),
                 ((ex1, bh), (ex0, bh)), ((ex0, bh), (ex0, 0))):
        d.member(a, b, lw=3)
    d.hinge((bx, By), r=5, dot=False)
    d.text((bx - 0.30, By + 0.30), "B", size=16, bold=True)
    d.reaction((bx - 0.18, -0.62), 90, 0.55, label="N", lab_off=(-16, 0))
    d.reaction((bx + 0.18, -0.10), 180, 0.72, label="F_f", lab_off=(0, 20))
    d.reaction((bx, By), -90 + theta, 0.95, label="R", lab_off=(14, 8))
    d.force((ex1, By), 180 + beta, 0.95, label="F", tip=False, lab_off=(52, -30))
    d.text((bx - 0.2, 2.72), "（b）滑块 B 分离体", size=15)
    d.text((2.2, -0.80), "R = M/(l cosθ)   N = M/l + F sinβ", size=13, color=DIM)
    return d
