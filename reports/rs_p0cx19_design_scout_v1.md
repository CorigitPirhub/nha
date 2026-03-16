# P0-CX19 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-13`

## 1. Executive Summary

`CX17-C / RS-HPS` 是到目前为止最重要的新证据：

- public `exp4 exp_delta = +3.278`
- `flange exp_delta = +1.0`
- 但 hard-test `exp_delta = -4.904`

它说明两件事同时成立：

1. **“viability + macro + motif + substrate” 的联合系统路线已经比 `CX1-CX18` 的任何单点模块都更接近真正的新 ceiling**；
2. **但当前联合系统仍不够“原生”**：viability 还没有真正定义动作语言，motif 还没有真正变成 planner 内部图结构，substrate 也还没有完全摆脱外挂式 policy 形态。

因此 `CX19` 的核心命题应被重写为：

> **不再把 viability、macro、motif 当成三个模块，而是把它们统一为一个更强的 planner system：viability 负责定义可用动作语法，motif 负责提供跨 episode 的结构先验，substrate 负责把这两者原生化为搜索图的一部分。**

本轮按用户要求，只聚焦三个方面：

1. **继续做深 `CX17-C` 这类联合 substrate 路线**
2. **`viability oracle -> native macro library` 的更强闭环**
3. **`failure -> escape motif` 的更强编译化版本**

并且本轮**不把时间开销作为 first-pass 否决项**，优先追求新的效果 ceiling。

## 2. What `CX16` and `CX17` Actually Established

### 2.1 `CX16-B` + `CX16-A`：对象是对的，但耦合不够

- `CX16-B` 证明 viability object 本身能在 public overall 上转正；
- `CX16-A` 证明原生 macro library 已接近部署边界；
- 但二者分开时，一个卡在“有信号但太贵”，另一个卡在“代价可控但效果不够”。

这说明当前真正缺的不是其中任一对象，而是：

> **viability 直接决定 macro grammar 的原生闭环。**

### 2.2 `CX16-D` + `CX17-B`：motif 方向没错，但表示太弱

- `CX16-D` 能把 `flange` 修成正项；
- `CX17-B` 把 motif 从简单 prefix 提升到 automaton 后，仍只是 public tie。

这说明 motif 的问题不在“有没有经验”，而在：

- 经验单元还不够结构化；
- motif 没有和 viability / macro language 共享统一状态表示；
- motif 还在作为外挂检索器，而不是 planner 内部图的一部分。

### 2.3 `CX17-C`：现在最关键的跟进对象

`CX17-C` 已经说明：

- public 上，联合 substrate 确实能形成新的正向 ceiling；
- hard-test 上，没有守住，说明：
  - substrate 对 public family 建立了 leverage；
  - 但跨 family 稳定性仍不足；
  - 特别是 `deadend_labyrinth` 与 `parasol_misc` 的负项会吃掉整体收益。

所以 `CX19` 不该重新开很多平行小路线，而应围绕：

> **把 `CX17-C` 中“有效但还不够原生”的部分继续系统化。**

## 3. Literature Sweep

以下只保留与当前三个焦点直接相关、且尽量来自顶刊/顶会 primary source 的工作。

### 3.1 继续做深 `CX17-C` 这类联合 substrate 路线

1. **MeshA\*: Efficient Path Planning by Integrating Vehicle Dynamics into the Search Graph** — CoRL 2025  
   Link: <https://openreview.net/forum?id=yoDmNA48yq>
2. **Incremental Generalized Hybrid A\*** — arXiv 2025  
   Link: <https://arxiv.org/abs/2508.13392>
3. **Shortest Paths in Graphs of Convex Sets** — arXiv 2021  
   Link: <https://arxiv.org/abs/2101.11565>
4. **Multi-Query Shortest-Path Problem in Graphs of Convex Sets** — arXiv 2024  
   Link: <https://arxiv.org/abs/2409.19543>
5. **Efficient Hierarchical Any-Angle Path Planning on Multi-Resolution 3D Grids** — RSS 2025  
   Link: <https://roboticsconference.org/program/papers/49/>

**启发**

- 更强的 planner substrate 往往有明确的层次分工：
  - 高层 mode / macro graph
  - 低层 local executable refinement
  - query-time 复用离线图结构
- 如果 substrate 还是依赖在线 hook 决策，那么它本质上仍然是外挂增强，而不是新 planner。

**对当前项目的直接含义**

- `CX19` 中的 substrate 不应再是“在原 planner 外部做 mode 选择”；
- 它应当原生包含：
  - viability states
  - macro transitions
  - motif priors
  三类对象。

### 3.2 `viability oracle -> native macro library` 的更强闭环

1. **Towards Provably Not-at-Fault Control of Autonomous Robots in Arbitrary Dynamic Environments** — RSS 2019  
   Link: <https://roboticsconference.org/2019/program/papers/011/index.html>
2. **ARMTD: Anytime Robot Motion Planning with Transit-Driving Modes and Reachability-Based Safety** — RSS 2020  
   Link: <https://roboticsconference.org/2020/program/papers/46.html>
3. **Neural Value Functions for Safe Reachability-Based Control of Autonomous Systems** — RSS 2023  
   Link: <https://roboticsconference.org/2023/program/papers/036/>
4. **Safe Planning for Articulated Robots Using Reachability-based Obstacle Avoidance With Spheres (SPARROWS)** — RSS 2024  
   Link: <https://roboticsconference.org/2024/program/papers/35/>
5. **Probably Approximately Correct Vision-Based Planning using Motion Primitives** — CoRL 2020  
   Link: <https://proceedings.mlr.press/v155/veer21a.html>
6. **Optimization-based Motion Primitive Automata for Autonomous Driving** — arXiv 2024  
   Link: <https://arxiv.org/abs/2401.14276>

**启发**

- viability / reachability 给出了“能不能继续”的正确对象；
- maneuver automata / primitive grammar 给出了“允许哪些动作语言”的正确对象；
- 但现有工作通常没有把二者统一成同一个 formal object。

**对当前项目的直接含义**

- `CX19` 应尝试把 viability 从 scalar 分数升级为：
  - discrete state
  - transition guard
  - macro language type system
- 也就是：不是 “先算一个分数，再选择 macro”，而是 “当前 viability state 本身就定义了 macro grammar”。

### 3.3 `failure -> escape motif` 的更强编译化版本

1. **Experience Graphs: Leveraging Experience for Planning with Sparse Roadmap Spanners** — RSS 2012 / IJRR  
   Link: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
2. **Thunder Framework: Experience-Based Motion Planning in Changing, Partially-Known Environments** — ICRA 2015  
   Link: <https://arxiv.org/abs/1508.01296>
3. **Experience-based Multi-Agent Path Finding with Narrow Corridors** — RSS 2024  
   Link: <https://roboticsconference.org/2024/program/papers/87/>
4. **VisualPredicator: Learning Abstract World Models with Neuro-Symbolic Predicates for Robot Planning** — ICLR 2025  
   Link: <https://openreview.net/forum?id=QOfswj7hij>
5. **Learning Compositional Behavior from Demonstration and Task Specifications** — RSS 2025  
   Link: <https://roboticsconference.org/program/papers/141/>

**启发**

- 经验若想真正泛化，需要：
  - compositionality
  - abstraction
  - transition semantics
- 简单的路径记忆或 prefix 检索都太弱。

**对当前项目的直接含义**

- `CX19` 中的 motif 不应只是:
  - `entry_key -> sequence`
- 而应变成：
  - `failure class`
  - `bad maneuver family`
  - `escape class`
  - `recovered basin`
  之间的 graph / compiler。

## 4. Structural Diagnosis for `CX19`

### 4.1 为什么 `CX17-A` / `CX18-A` 只能 tie

因为它们仍在做：

- viability 作为 score / gate；
- macro 作为被激活对象；

而没有做到：

- **viability = 动作语言的语法约束**。

### 4.2 为什么 `CX17-B` / `CX18-B` 仍不够强

因为它们仍在做：

- motif 作为“被查到的经验”

而不是：

- **motif = 搜索图中的状态转移结构**。

### 4.3 为什么 `CX17-C` public 正、hard-test 负

最可能的解释不是“对象错了”，而是：

- public 上它已经建立了局部正确的 mode system；
- hard-test 上 mode system 还不够强，无法稳定约束更广的 bad basin / deadend 模式；
- 这说明 `CX19` 应优先增强：
  - viability state discretization
  - macro grammar binding
  - motif graph transition semantics
而不是继续写更多 local ranking bias。

## 5. Proposed `CX19` Candidate Families

### CX19-A: `RS-VMG` — Viability Macro Grammar

**对应焦点**

- `viability oracle -> native macro library` 的更强闭环

**核心想法**

1. 把 viability oracle 升级成 **discrete viability state machine**：
   - `safe_progress`
   - `recoverable_boundary`
   - `reverse_required`
   - `near_trap`
2. 每个 viability state 对应一套 native macro grammar：
   - 可用 macro family 集
   - family 间转移规则
   - 禁止的 maneuver classes
3. planner 在线时不再“根据分数激活 macro”，而是：
   - 先进入一个 viability state；
   - 再在该状态允许的 macro grammar 内扩展。

**如何继承现有有效语义**

- `CX16-B` 给出的 viability signal；
- `CX16-A` 的原生 macro library；
- `CX17-C` 的 public-level ceiling。

**理论抓手**

- viability kernel；
- maneuver automata；
- grammar-constrained search。

**创新点**

- 把 viability 和 macro 从 weak coupling 变成 **同一动作系统的语法层**。

**为什么可能带来突破**

- 这条路线最直接瞄准当前最大断点：`oracle 有效，但还没真正定义动作语言`。

**风险**

- viability state 离散化若不稳，会过度约束搜索；
- grammar 设计不当会让 macro language 太僵硬。

### CX19-B: `RS-MCG` — Motif Compiler Graph

**对应焦点**

- `failure -> escape motif` 的更强编译化版本

**核心想法**

1. 将经验编译为 graph，而不是 automaton 检索器：
   - nodes: failure class / escape class / recovered basin
   - edges: bad family -> escape family transitions
2. edge 上携带：
   - expected gain
   - legality under current viability state
   - preferred macro families
3. planner 在线使用 motif graph 不是为了直接执行某条 prefix，
   而是为了给当前 macro grammar 提供 transition prior。

**如何继承现有有效语义**

- `CX16-D` / `CX17-B` 已经证明 failure→escape 经验本身有价值；
- `CX19-B` 要解决的是它们“表示太弱、不能真正主导搜索图”的问题。

**理论抓手**

- structured memory；
- symbolic behavior graph；
- case-based planning with abstraction transitions。

**创新点**

- 不是 memory lookup；
- 而是 **memory-compiled transition graph**。

**为什么可能带来突破**

- 这是把 sparse positive maneuver 真正变成 reusable graph prior 的最直接方式。

**风险**

- graph schema 复杂；
- 若 failure / basin 抽象不好，仍可能过拟合 public families。

### CX19-C: `RS-UGS` — Unified Graph Substrate

**对应焦点**

- `CX17-C` 这类联合 substrate 路线继续做深

**核心想法**

1. 用统一 graph substrate 取代当前“policy 驱动的 mode 切换”：
   - viability graph
   - macro grammar graph
   - motif compiler graph
   - local executable lattice
2. 搜索先在 graph substrate 上决定：
   - 当前 viability state
   - 允许的 macro grammar
   - motif-provided transition prior
3. 只有在这些高层对象达成一致后，才在 local lattice 上做 executable refinement。

**如何继承现有有效语义**

- `CX17-C` 是它的直接前身；
- `CX19-A/B` 提供它真正需要的“原生对象”。

**理论抓手**

- hierarchical graph search；
- multi-query reusable graph；
- generalized hybrid substrate；
- graph-of-convex-sets style decomposition。

**创新点**

- 不再存在外挂 hook；
- planner 本体就是 graph substrate。

**为什么可能带来突破**

- 若前两条路线站住脚，这条路线最有可能把当前 public ceiling 进一步推到 hard-test。

**风险**

- 工程和验证代价最高；
- 若 `A/B` 还不稳，容易再次放大误差。

## 6. Recommended Execution Order

推荐顺序：`CX19-A -> CX19-B -> CX19-C`

1. **先做 `CX19-A / RS-VMG`**
   - 先验证 viability 能否真正定义动作语法，而不仅是做 activation score。
2. **再做 `CX19-B / RS-MCG`**
   - 若 `A` 形成局部 ceiling，则用 motif compiler graph 稳定并放大这些 gains。
3. **最后做 `CX19-C / RS-UGS`**
   - 只有当前两个对象都站住脚，才值得重写统一 substrate。

## 7. Protocol and Acceptance Boundary

`CX19` 仍延续 `CX17/CX18` 的 first-pass ceiling-first 规则：

1. public first-pass gate：
   - `exp4 exp_delta > 0`
   - `flange exp_delta >= 0`
2. 通过后才允许消费 `rs_root_hard_v2/test`
3. hard-test 若也维持正向，则进入下一轮 compression / deployment planning
4. `mp/csm` ordinary-support audit 继续强制执行

## 8. Main Recommendation

如果只押一条主线，应押：

> **`CX19-A / RS-VMG`**

原因：

- `CX16-B` 已证明 viability object 有信号；
- `CX16-A` 已证明 macro library 已接近可部署；
- `CX17-C` 已证明联合 substrate 能带来新的 public ceiling；
- `CX19-A` 正是把这三条证据收敛成最小闭环的路线。

## 9. Source Links

- RSS 2019 not-at-fault control: <https://roboticsconference.org/2019/program/papers/011/index.html>
- RSS 2020 ARMTD: <https://roboticsconference.org/2020/program/papers/46.html>
- RSS 2023 neural safe reachability values: <https://roboticsconference.org/2023/program/papers/036/>
- RSS 2024 SPARROWS: <https://roboticsconference.org/2024/program/papers/35/>
- CoRL 2020 PAC motion primitives: <https://proceedings.mlr.press/v155/veer21a.html>
- Motion primitive automata: <https://arxiv.org/abs/2401.14276>
- Experience Graphs: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
- Thunder: <https://arxiv.org/abs/1508.01296>
- RSS 2024 experience-based narrow-corridor planning: <https://roboticsconference.org/2024/program/papers/87/>
- ICLR 2025 VisualPredicator: <https://openreview.net/forum?id=QOfswj7hij>
- RSS 2025 compositional behavior: <https://roboticsconference.org/program/papers/141/>
- MeshA*: <https://openreview.net/forum?id=yoDmNA48yq>
- GCS shortest paths: <https://arxiv.org/abs/2101.11565>
- Multi-query GCS: <https://arxiv.org/abs/2409.19543>
