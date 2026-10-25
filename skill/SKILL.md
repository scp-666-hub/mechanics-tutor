---
name: mechanics-tutor
description: >
  Use when solving or checking 理论力学 / 静力学 / 材料力学 homework problems,
  especially ones sent as textbook photos: needs the geometry transcribed back for
  confirmation, a sympy-verified symbolic solution, and a free-body diagram PNG.
  Also use for 受力图 / 剪力图 / 弯矩图 requests, truss and beam reaction problems,
  套筒滑块 / 摩擦临界 problems, or when the user asks whether a mechanics answer is correct.
---

# 力学解题（理论力学 · 静力学 · 材料力学）

## 铁律

四道闸，缺一道不许交答案：

1. **几何转录单** —— 图里读到的每一个数先列出来给用户核。
2. **符号解 + 数值验算** —— sympy 解，残差必须打印出来且 ≈0。
3. **受力图 PNG** —— 每道题都要出图，用绝对路径贴进回复。
4. **力偶转向自检** —— 图里有力偶（M / M_A / M_C）时，另出一张独立小图核对箭头转向，并在回复里说明核过。

只看文字题能算对不算过关（已实测：不给流程时对纯文字题也解得对，但不验算、不出图）。

## 环境

```
解释器  <你的 python>   (sympy 1.14 / numpy / scipy / anastruct)
工具    ~/.dsh/skills/mechanics-tutor\{mechkit.py,fbd.py,templates.py,TYPES.md}
vendor  <dsh-mech-workbench>/mechwb.py                    (内力图 / 题图预处理，见下节)
知识库  <知识库目录>\
          QUESTION_BANK.md                                                                          (题库索引)
          cfd-resources\notes\applied_mechanics\{statics,dynamics,strength_materials,fundamentals}\   (Markdown)
          EngineeringStatics\source\ptx\Chapter_01..10.ptx                                           (PreTeXt 教材)
          theoretical-mechanics-solutions\ / ans_to_mech_XuYanhou\                                   (LaTeX 习题解答)
```
做题顺序：**先查 `TYPES.md` 对号入座 → 有模板就用 `templates.py` → 需要练手/对照时翻 `QUESTION_BANK.md`（每条带原文件行号，用 read 的 offset 直接跳）→ 公式拿不准再 grep 教材**。
做法：**先 grep 知识库对标准写法和公式形式**，再动笔。对不上教材的记号会让学生抄错；拿不准的公式（如摩擦角、桁架零杆判别）在 `strength_materials\` / `statics\` 里能直接搜到原文。

## 内力图、应力图与题图预处理（vendor 自 dsh-mech-workbench，**没装插件**）

`<dsh-mech-workbench>/mechwb.py` 是开源插件 dsh-mech-workbench 0.3.1 的
`scripts/` 薄封装（MIT）。**解释器必须用 DSH 自带的那个**（需要有 numpy + Pillow）：

```powershell
$py = "$env:USERPROFILE\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
$wb = "<dsh-mech-workbench>/mechwb.py"
```

### ① 读图固定三步（别再手写 PIL）

```powershell
# 1) 预处理：EXIF 转正 / 旋转 / 去斜 / 裁切 / 放大 / 一页多题分栏
& $py $wb prep --spec-json '{"src":"<原图>","out":"C:\\CTMP\\q.png","ops":[
  {"op":"auto_orient"},{"op":"rotate","angle":90},
  {"op":"crop_box","box":[0.20,0.42,0.50,0.90]}]}'
# 2) read_image 看 q.png 确认几何
# 3) 出对照图让用户核（左=原图，右=转写，关键量高亮）
& $py $wb compare --spec-json '{"original":"C:\\CTMP\\q.png","out":"C:\\CTMP\\cmp.png",
  "title":"题 X 读题自检",
  "sections":[{"heading":"已知","lines":["..."]},{"heading":"求","lines":["..."]}],
  "highlight":["P₁","θ","C"]}'
```

算子：`auto_orient` `rotate` `deskew` `perspective` `crop_box` `crop` `zoom` `upscale`
`binarize` `denoise` `enhance_text` `grayscale` `autocontrast` `sharpen`；顶层 `split:{"mode":"auto"}`
自动切一页多题。**拍歪、一页几题时先跑 prep，不要再手写 PIL。**

### ② 学科预设图（材料力学主力）

```powershell
& $py $wb diag --spec-json '{"panels":[{"preset":"mohr","sigma_x":80,"sigma_y":-40,"tau_xy":30}]}' --out C:\tmp\mohr.png
```

各预设要的输入：

- `axial` / `shear` / `torque` → `segments:[{x0,x1,value}]`，线性变化时用 `points:[{x,value}]`
- `moment` / `deflection` → `points:[{x,value}]`
- `stress` → `dist:[{y,sigma}]`（可加 `"type":"parabolic"`）
- `mohr` → `sigma_x` / `sigma_y` / `tau_xy`

可以一次给多个 `panels`（纵向叠、内力图自动共享 x 轴；含莫尔圆/应力图时不共享）。
单独出莫尔圆会自动换方画布，保证是正圆。

### ③ 梁的内力图（剪力 + 弯矩双面板）

```powershell
& $py $wb beam-gm --spec-json '<analyze spec>' --out C:\tmp\gm.png
```

梁类 spec（长度 m、力 kN、力矩 kN·m、应力 MPa）：

```json
{"kind":"beam","length":4,
 "supports":[{"x":0,"type":"pin"},{"x":4,"type":"roller"}],
 "loads":[{"type":"distributed","x0":0,"x1":1,"q0":-4,"q1":-4,"dir":"transverse"},
          {"type":"point_force","x":2,"value":-10,"dir":"transverse"}],
 "section":{"shape":"rect","params":{"b":0.12,"h":0.24}}}
```

符号约定：Q 使微段顺时针转为正、M 下侧受拉为正、横向力向上为正、集中力偶逆时针为正、N 拉为正。

### ④ 视觉自检（已开，2026-10-26 用户明确不在乎外发）

出图**定稿前**跑一次（约 25 秒、几分钱以内）：

```powershell
& $py $wb check --spec-json '{"images":["C:\\CTMP\\fbd.png"]}'
```

它把图交给阿里百炼 `qwen3-vl-plus`（key 取 `~/.dsh/.credentials.yaml` 的
`refs.QWEN_TOKEN_PLAN_CN_API_KEY`），让**另一个模型**查：文字互压、文字压箭头、出画布被裁、
乱码/缺字形、力偶转向与标注是否自相矛盾。返回 `verdict` 为自然语言逐条结论。

**结论只当提示，不当判决**：实测它会误读——把点标注 `C` 当成一个力名，进而判「严重不自洽」。
正确用法是它点名某处 → 我自己放大图核 → 是我的问题就改，是它看错就不动。

迭代中（改参数那几轮）不要跑，只在**最后一次出图**跑。

### 规矩

- **梁题必须出 Q、M 图**，用它，别再手画；极值直接引返回的 `extrema`，不要另估。
- 返回 `determinate: false` 就是静不定——如实说明需变形协调/刚度法，**不许猜**。
- 本机没有 matplotlib，出图走 Pillow：数值对、版式素，会多一条贴着首值的横线（可忽略）。
- **视觉自检 / `second_reader` 默认不开**：会把题图 base64 发出去。要用就把 `VISION_FALLBACKS`
  指向 `https://dashscope.aliyuncs.com/compatible-mode/v1` + `qwen3-vl-plus`。
- 它自带的 `templates.py` 与我们自己的 `templates.py` 不是一回事，别混。

## 流程

**一趟做完**：照片转正/裁图 → 符号解 → 验算 → 出图，写进**同一个**脚本，一次 pwsh 跑完，只回读一张成品图；整题工具往返控制在 3 次左右。实测的慢几乎全来自「一步一个脚本」（转正一趟、裁图一趟、求解一趟、出图四趟）。

### 0. 读图 → 转录单（先发给用户核）

**先转正再读**：横拍/倒拍的照片先旋转（必要时镜向），并重新裁切到只剩题图再 `read_image`。回复里写明「照片方向已校正」——否则用户不知道你看到的是哪一版。转正和裁切放在第 2 步那个总脚本里做。

从照片里读出的量逐条列出，一行一个：

```
已知：L = 2 m, W = 200 N, 杆与墙夹角 60°, 索与水平夹角 30°
坐标：A 为原点, x 垂直墙面向外, y 沿墙向上
待求：索张力 T, A 处反力
待确认：杆是否均质（影响 G 位置）、柔索系点 C 是否在 A 正上方
```

图里模糊或没拍到的，标「待确认」一次性问清。**不要猜着一个含糊的几何关系往下算**——几何错一步，后面全废，而用户看不到你的推导过程，只会看到一个错答案。

**角度标注歧义**（典型：图里两处 `30°`，看不清各自从哪条线量起）：把每种读法都写进待确认；用户答不上来时，**用几何可行性排除**并写出理由，例如「若 A 处 30° 也读成 AD 与墙成 30°，两杆与墙夹角相同 → 两杆平行 → B 必须同时落在两杆上，交点不存在 → 该读法题无解」，然后定下所选读法（如「CB 与墙 30° 即与水平 60°，AD 与水平 30°」）再往下算。含糊带过=交一个可能全错的答案。

**纯文字题**（没有照片）照样要出转录单：逐条抄题面给的量，把题面没明说但你要用的假设列进「待确认」（夹角从哪条线量起、接触点会不会脱离、摩擦系数属于哪一对接触面），并在解完后回代验证这些假设。

### 1. 受力分析

研究对象 → 解除约束 → 逐个力写清：作用点、方向、大小（已知/未知）。约束对照：

| 约束 | 反力 |
|---|---|
| 光滑接触面 | 1 个，沿公法线，只能是压力 |
| 柔索 / 皮带 | 1 个，沿索背离物体（只能受拉） |
| 固定铰链 / 圆柱铰 | 2 个正交分量，方向可先假设 |
| 可动铰（辊轴） | 1 个，垂直支承面 |
| 固定端 | 2 个分量 + 1 个反力偶 |
| 套筒 / 滑块套在杆上 | 垂直杆的 1 个正压力 N + 沿杆的摩擦力 F，\|F\| ≤ f_s N |

均质物体重心在几何中心；非均质按质心公式。二力构件先认出来，能省一半方程。有套筒时注意：正压力方向可先假设，解完看 N 是否 > 0，负值说明压力方向反了。

### 2. 符号解

写临时脚本（放 `C:\tmp\`），用 mechkit 解：

```python
import sys
sys.path.insert(0, r"~/.dsh/skills/mechanics-tutor")
import sympy as sp
from mechkit import mz, solve, verify, show

T, Xa, Ya, W = sp.symbols("T X_a Y_a W")
eqs = [
    Xa - T*sp.cos(sp.pi/6),
    Ya + T*sp.sin(sp.pi/6) - W,
    mz((sp.sqrt(3), 1), (-T*sp.cos(sp.pi/6), T*sp.sin(sp.pi/6)))
    + mz((sp.sqrt(3)/2, 1/2), (0, -W)),
]
sol = solve(eqs, [T, Xa, Ya])
show("T", sol[T], {W: 200})          # 先符号后数值
verify(eqs, sol, {W: 200})           # 残差必须 ≈0
```

规矩：

- **先出符号解，再代数值**，中途不许四舍五入。
- 角度用 `sp.pi/6` 这类精确值，不要写 0.5236。
- 力矩统一逆时针为正，`mz(r, f)` 的 `r` 是**取矩点指向作用点**，正负号错是最高频错误。
- **`verify()` 只认全部代完值的方程**：任何一式代完还残留符号（典型是忘了把 μ、θ 代值），它会打 `[FAIL] 残留符号 [...]` 并返回 `inf`。看到 `[FAIL]` 就是没验成，不许当通过。
- **三角方程别直接丢给 `sp.solve(..., sp.tan(th))`**（会返回空表）。令 `t = sp.tan(th)` 代换解出 t，再 `th = sp.atan(t)`；或直接用 `sp.solve(sp.Eq(lhs, rhs), th)` 解角度本身。

### 3. 验算（必须做，且把结果贴出来）

四项至少做前三项：

1. **残差**：`verify()` 返回最大残差，应 < 1e-9。
2. **量纲**：每一项都该是力或力矩，混了长度就是公式错。
3. **极限 / 特例**：让某个角 → 0° 或 90°、某个力 → 0，答案应退化成显然结果（如索与杆共线时 T 应为 0）。
4. **换点重算**：对另一个点（如 B）再写一次力矩方程，答案应一致。

过不了就重算，**不许交一个没验算的答案**。

### 4. 受力图

**先用模板，别从零画。** `templates.py` 里已有 9 个高频题型的骨架，改参数就出图：

```python
import sys; sys.path.insert(0, r"~/.dsh/skills/mechanics-tutor")
import templates as T
print(T.ladder_wall(theta=59.0, mu=0.3).png(r"C:\tmp\a.png"))
```

`beam_simple` 简支梁 · `beam_cantilever` 悬臂梁 · `block_incline` 斜面滑块 ·
`ladder_wall` 梯子摩擦 · `two_rope_knot` 两索吊重（三力汇交）· `slider_rod` 套筒滑块机构 ·
`box_between_rails` 升降箱卡滞 · `truss_triangle` 三角桁架 ·
`crank_slider` 曲柄连杆滑块机构（附滑块分离体）。

题型对不上号时，先看 `TYPES.md`（23 个题型的识别特征 / 标准步骤 / 易错点），再手写图：

```python
import sys; sys.path.insert(0, r"~/.dsh/skills/mechanics-tutor")
from fbd import Diagram, APPLY, REACT
d = Diagram(title="杆 AB 受力图")
d.wall((0, 0), (0, 2.6), side=1, label="墙")
d.member((0, 0), (1.732, 1), label="AB", off=(0.18, -0.12))
d.rope((1.732, 1), (0, 2))
d.support("pin", (0, 0), label="A")
d.force((0.866, 0.5), -90, 1.1, label="W")        # 角度按数学惯例，y 向上
d.force((1.732, 1), 150, 0.9, label="T")
d.reaction((0, 0), 0, 0.7, label="X_A", lab_off=(0, -16))
d.reaction((0, 0), 90, 0.9, label="Y_A", lab_off=(-18, 0))
d.angle((0, 0), 30, 90, 0.55, text="60°")
print(d.png(r"C:\tmp\fbd.png"))                   # SVG → PNG, 返回绝对路径
```

- 颜色常量只有 `INK / APPLY / REACT / DIM`，**全是 #RRGGBB**；不要写 `rgba()`，写进 PPT 会判定文件损坏。
- 常用件：`member` `rope` `support("pin"|"roller"|"fix"|"ground")` `hinge` `sleeve` `wall` `force` `reaction` `couple` `dist_load` `dim` `angle` `legend`。
- 容易踩的四个参数：`wall(a, b, side=)` 剖面线在 a→b 的法线侧（竖墙自下而上画时 side=1 朝右）；地面线长度用 `support("ground", at, span=px)`；`dim(..., orient="auto")` 文字沿尺寸线旋转，`orient="h"` 才水平；`force(..., lab_off=)` / `member(..., off=)` 用来躲开重叠。

**套筒滑块 / 销轴（fbd.py 已内置，别手绘）**

- `sleeve(at, ang, length=0.16, width=0.09, color=INK, lw=1.8, dot=True, fill=BG)`：中心在 `at`、长边沿 `ang` 方向的长方形，`length` / `width` 用**模型单位**；`dot=True` 在中心画铰点。滑块套在杆上时用它，`ang` 取杆的方向。标签仍挂在力/构件上（`force(..., label="N")` 或构件的 `label=`），别给它编新参数。

```python
d.member((0, 0), (1.732, 1), label="AD", off=(0.18, -0.12))
d.sleeve((0.87, 0.5), 30)              # 套在 30° 杆上的滑块
d.hinge((0, 1.0), dot=False)           # A 处销轴圆圈
d.hinge((0, 0.0), dot=False)           # C 处销轴圆圈
```

- `hinge(at, r=6.0, color=INK, fill=BG, lw=2.0, dot=False)`：墙上/板上的销轴小圆圈，`r` 是**像素**半径；`dot=False` 即不画中心实心点（教科书里的销轴是空心的，默认就这样）。A、C 这类铰点用它，不要拿 `support("pin")` 的支座剖面线冒充墙上的铰。

**排版检查分两级（这是门槛的定义）**

- **硬冲突 = 不可交图**：文字互压（真实四边形相交）、元素出画布。
- **软提示 = 可接受**：文字压在箭头/构件线上（`[提示] 文字压构件：「…」（可接受，想更好看就调 off/lab_off）`）。教科书里标签压线本来就正常，**不要为它重画**。

`png()` 会自动跑检查并打印 lint。通过线是 **0 硬冲突**：全新输出为 `[lint] 0 硬冲突，可交图`；一处提示都没有时仍是 `[lint] 排版 0 冲突`。看到「共 N 处冲突」就是没过。

**lint 冲突的批量调参收敛套路**（避免一版一版手改脚本）

1. **一次只动标签/构件的位置参数**：`member(off=, label_t=)`、`force(lab_off=)`、`reaction(lab_off=)`、`wall(side=)`、`support(span=)`。不要靠缩小字号糊过去。
2. **用 PowerShell 逐字替换**脚本里的那几处参数，一轮改 2–3 处相关量，不重写整份脚本：

```powershell
$p="C:\tmp\p416_fbd3.py"; $t=Get-Content $p -Raw -Encoding UTF8
$t=$t.Replace('label="CB", off=(0.17, 0.02), label_t=0.30','label="CB", off=(-0.17, 0.02), label_t=0.64')
$t=$t.Replace('lab_off=(-58, -30)','lab_off=(-46, -44)')
Set-Content $p -Value $t -Encoding UTF8 -NoNewline
& "<你的 python>" $p 2>&1 | Select-String -Pattern 'lint|提示'
```

   替换串必须与脚本原文**逐字一致**（含空格、引号、括号），否则静默不生效——替换后先 `Select-String` 确认目标行真的变了，再渲染。
3. **渲染完只读 lint 行，先不读图**；有冲突就继续第 1 步，直到 `0 硬冲突`。一般 2–3 轮收敛。
4. **同一处连续两轮没动静就换方向**：`off` 改符号；`label_t` 从 0.30 挪到 0.50 / 0.64 换到杆的另一段；把标签从 `member` 挪到 `force`，或反过来。
5. **收敛后才 `read_image` 看真图**——lint 估的文字宽度有误差，这一步不能省。

**力偶（M、M_A、M_C）**

- `couple(..., lab_off=None)` 时标注自动落在圆弧对侧（约 170° 方向、半径 r+22 px），**别再手填偏移**；只有它压到别的元素时才给 `lab_off`。
- **转向必须单独自检**：另出一张小图，同页并排画 `ccw=True` 与 `ccw=False`，对照题图确认每个力偶是顺还是逆：

```python
import sys; sys.path.insert(0, r"~/.dsh/skills/mechanics-tutor")
from fbd import Diagram, DIM
d = Diagram(width=520, height=260, scale=100, origin=(120, 170),
            title="couple 方向自检：左 ccw=True 右 ccw=False")
d.couple((0.0, 0.0), 0.6, label="ccw=True", ccw=True, lab_off=(0, -70))
d.couple((2.6, 0.0), 0.6, label="ccw=False", ccw=False, lab_off=(0, -70))
print(d.png(r"C:\tmp\couple_dir.png"))
```

  `read_image` 看这张小图，确认主图里 M_A、M_C 的箭头与题图一致（题图顺时针 → `ccw=False`），并在回复里写一句「力偶转向已核对」。画反的力偶比排版丑严重得多。

回复里用绝对路径引用：`![受力图](C:\tmp\fbd.png)`。

### 5. 输出格式

```
【已知】【求】【解】分步，每步一句理由（用哪个定理/为什么取这个研究对象）
【答】框起来，带单位、带方向，写成"大小 … ，方向 …"
【易错点】1–2 条，针对这道题（符号约定、二力构件、摩擦角边界…）
```

中间过程写到「学生能照着抄」的程度，但不要复述代入算术——那是废字。

**公式一律用渲染式**：行内 `$M_C=\frac{3}{2}M_A-\frac{l}{2}F$`，独立行 `$$...$$`。**不要用 ``` 代码块包公式**（用户已明确偏好，代码块里的公式不可读）。纯数值结果（如 `N = 34.6 N`）照常用文本。

## 常见错误

| 错误 | 后果 | 对策 |
|---|---|---|
| 力矩符号约定换了又换 | T 出现负号，方向判反 | 全题统一逆时针为正，取矩点写在方程旁 |
| 把柔索当二力杆（能受压） | 解出 T < 0 的反物理答案 | 解完看 T 是否 > 0，负值说明受力假设反了 |
| 分布载荷忘了等效集中力 | 反力整体偏小 | 合力 = 面积，作用点 = 形心 |
| 桁架没先判零杆 | 方程数暴涨 | 先找两杆汇交无载节点 |
| 照片里角度读错 / 读法歧义硬猜 | 全错 | 转录单让用户核；歧义用几何可行性排除并写明理由 |
| 力偶箭头画反 | 学生照着抄就错 | 单独小图核对转向（铁律 4） |
| 把「文字压箭头」当失败反复重画 | 一句题耗掉四轮以上 | 只有文字互压/出画布才重画，压线只算提示 |
| 一步一个脚本往返 | 十几趟，慢到用户抱怨 | 转正+裁图+求解+出图合成一个脚本 |
| 只验残差不验极限 | 方程列错但自洽（真的会发生） | 极限检查必做 |

## 交卷前自检

- [ ] 有照片时已转正/裁切，并在回复里说明方向已校正
- [ ] 转录单里没有「我猜的」量；歧义读法已用几何可行性排除并写明理由
- [ ] 先用符号、后代入
- [ ] `verify()` 打出 `[OK] 全部方程代回通过`（出现过 `[FAIL]` / `残留符号` 就是没验成）
- [ ] 极限检查退化成显然结果
- [ ] 出图 lint 到 **0 硬冲突**（`[lint] 排版 0 冲突` 或 `[lint] 0 硬冲突，可交图`），且没有为「文字压线」返工
- [ ] 套筒用 `sleeve()`、墙上销轴用 `hinge(..., dot=False)`，没有手绘矩形/圆圈
- [ ] 有力偶时另出了方向自检小图，并在回复里说明已核对转向
- [ ] PNG 打开看过一眼，版面合理
- [ ] 公式用 `$…$` / `$$…$$`，没有用代码块包公式
- [ ] 答案带单位和方向
