"""力学解题小工具：二维力矩、符号求解、代回验算。

解释器：<你的 python 解释器>
用法见同目录 SKILL.md 第 3 步。
"""
import sys

import sympy as sp

# Windows 控制台默认 GBK，中文输出会变乱码；强制 UTF-8
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 无 reconfigure 的环境忽略
        pass


def mz(r, f):
    """二维力矩，逆时针为正。

    r = (rx, ry) 由取矩点指向力作用点；f = (Fx, Fy)。
    传浮点坐标会保留为 Float（不再 nsimplify 成近似有理数，避免 simplify 变慢）。
    """
    return sp.sympify(r[0]) * f[1] - sp.sympify(r[1]) * f[0]


def solve(eqs, unknowns):
    """解方程组（每式按 = 0 处理），要求唯一解。"""
    eqs = list(eqs)
    sol = sp.solve(eqs, unknowns, dict=True)
    if not sol:
        raise SystemExit("无解：检查方程符号或未知量是否漏项")
    if len(sol) > 1:
        raise SystemExit(f"解不唯一（{len(sol)} 组），需要补几何/物理约束")
    return sol[0]


def verify(eqs, sol, values=None, tol=1e-9):
    """把解代回每个方程，返回最大残差（应 ≈ 0）。

    values: 额外代值，例如 {W: 200, L: 2}

    注意：只要有一式代完还残留符号（例如忘了给 mu 代值），就直接判 FAIL 并返回 inf——
    这种"看起来残差 0"的假通过比算错更危险。
    """
    values = values or {}
    worst, detail, unresolved = 0.0, [], 0
    for i, e in enumerate(eqs, 1):
        try:
            r = sp.simplify(e.subs(sol).subs(values))
            if r.free_symbols:
                unresolved += 1
                detail.append(f"  式{i}: [FAIL] 残留符号 {sorted(map(str, r.free_symbols))}"
                              f" —— 先把这些量代值再 verify")
                continue
            v = abs(float(r))
        except Exception as exc:            # noqa: BLE001 诊断用
            unresolved += 1
            detail.append(f"  式{i}: [FAIL] 无法数值化（{exc}）")
            continue
        worst = max(worst, v)
        detail.append(f"  式{i}: 残差 {v:.3e}")
    if detail:
        print("\n".join(detail))
    if unresolved:
        print(f"[FAIL] {unresolved} 个方程未真正验证，结论不成立")
        return float("inf")
    if worst > tol:
        print(f"[FAIL] 最大残差 {worst:.3e} > {tol:.0e}，答案不可用")
    else:
        print(f"[OK] 全部方程代回通过，最大残差 {worst:.3e}")
    return worst


def numeric(expr, values=None, digits=4):
    """符号式代值取数值，同时打印符号形式。"""
    sym = sp.simplify(expr)
    if values:
        num = sp.N(sym.subs(values), digits)
        return sym, num
    return sym, None


def show(name, expr, values=None, digits=4):
    """一行打印：符号解 = 数值。"""
    sym, num = numeric(expr, values, digits)
    if num is None:
        print(f"{name} = {sym}")
    else:
        print(f"{name} = {sym} = {num}")


def check_limits(expr, var, points, note=""):
    """极限检查：expr 在 var -> 各点时是否退化为显然结果。"""
    for p in points:
        print(f"  极限检查 {var}->{p}: {sp.limit(expr, var, p)}  {note}")
