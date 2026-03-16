# P0-CX18 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-13`

## 1. Executive Summary

`CX17` 给出了当前最重要的新证据：

- `CX17-A / RS-VML`：把 viability 与 macro 做成闭环后，整体仍是 tie；
- `CX17-B / RS-MAG`：把 motif 升级为 automaton 后，整体仍是 tie；
- `CX17-C / RS-HPS`：第一次在更强系统层面通过 public positive ceiling gate（`public exp4 = +3.278`, `flange = +1.0`），但在 `rs_root_hard_v2/test` 上未维持转正（`exp_delta = -4.904`）。

这说明：

1. `viability + macro + motif + substrate` 这条联合系统路线不是错方向；
2. 但 `CX17-A/B` 说明，**对象做对但耦合还不够强**；
3. `CX17-C` 说明，**联合 substrate 已经足以带来新的 public ceiling**；
4. 真正缺的不是再加一层弱模块，而是把：
   - viability oracle
   - native macro language
   - motif compiler
   - substrate execution semantics
   做成更强的一体化 planner system。

因此 `CX18` 的问题必须重写为：

> **如何把 `CX17-C` 继续做深，不再把 viability、macro、motif 视为外挂，而是把它们做成 planner 原生语义层；并在不把时间开销作为首要 veto 的前提下，先追求新的 hard-test 效果 ceiling。**

## 2. What `CX17` Actually Established

### 2.1 `CX17-A`：联合闭环还不够强

- `public exp4 exp_delta = 0.0`
- `overhead = 0.387409`

读法：

- viability→macro 这个想法本身没有错；
- 但当前是“由 oracle 选择 macro”，而不是“由 oracle 定义 macro 可用语义空间”；
- 所以它还是像外挂，而不是原生 planner language。

### 2.2 `CX17-B`：motif automaton 还不够强

- `public exp4 exp_delta = 0.0`
- `overhead = 0.323685`

读法：

- motif graph 比 `key -> sequence` 更强；
- 但它目前还是检索层，不是 planner 内部语义层；
- 因此经验被“找到”了，却没有被强到足以改变搜索主导逻辑。

### 2.3 `CX17-C`：最重要的新信号

- public `exp4 = +3.278`
- `flange = +1.0`
- hard-test `exp_delta = -4.904`

读法：

- 这已经是 `CX8-D Heavy` 之后最重要的新 ceiling 信号之一；
- public 上的正向 signal 说明联合 substrate 的方向成立；
- hard-test 没守住，说明：
  - substrate 对 public 家族已经形成了局部 leverage；
  - 但还没有学会更强的跨 family 语义约束；
  - 特别是 `deadend_labyrinth` 与 `parasol_misc` 仍会吃掉收益。

所以 `CX18` 不能再平铺新 family，而应：

> **围绕 `CX17-C` 做更深的一体化 planner system 设计。**

## 3. Literature Sweep

以下只聚焦用户要求的三个方面，并尽量选择顶刊/顶会 primary source。

### 3.1 `CX17-C` 这类联合 planner substrate 路线继续做深

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

- substrate 一旦变成 multi-layer structure，就不应再只依赖一个 local successor policy；
- 高层 mode / macro graph 与低层 executable lattice 之间必须有明确接口；
- query-time 最关键的是重用离线结构，而不是每次在线重新推理。

**对当前项目的含义**

- `CX18` 若继续做 `CX17-C`，不应只是“再复杂一点的 HPS”；
- 而应把：
  - macro transitions
  - viability attributes
  - motif priors
  做成统一 substrate 的三层对象。

### 3.2 `viability oracle -> native macro library` 更强闭环

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

- viability object 和 motion primitive automata 本来就应是强耦合对象；
- 现有工作大多只做到：
  - viability 负责“能不能”
  - macro 负责“怎么做”
  但没有把两者变成一个统一的 activation grammar。

**对当前项目的含义**

- `CX18` 应把 viability object 从一个查询值，升级成 **macro language 的类型系统 / enable condition**；
- 即：某个 macro 是否存在，不只由匹配分数决定，而由 viability state machine 决定。

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

- 经验复用若想真正泛化，必须从 path memory 升级到 structured behavior memory；
- motif 应具备：
  - compositionality
  - symbolic abstraction
  - transition semantics
  而不仅是 `entry -> prefix` 检索。

**对当前项目的含义**

- `CX18` 中的 motif 不应再是 sequence list；
- 它应成为：
  - failure class
  - escape class
  - recovered basin class
  之间的可组合图结构，并且能够与 macro layer 共用状态表示。

## 4. Structural Diagnosis for `CX18`

`CX17` 已经足够说明，接下来若还要继续推进，必须绕开三类陷阱：

### 4.1 不能再把 viability 当成“分数”

`CX16-B`、`CX17-A` 说明：

- viability 若只作为一个 scalar / gate score，
- 最终仍然只是决定“要不要稍微动一下”，
- 不能真正决定 planner 的动作语言。

### 4.2 不能再把 motif 当成“检索结果”

`CX16-D`、`CX17-B` 说明：

- motif 若只是一个被查到的 prefix，
- 它很难稳定地改变搜索主干；
- 需要让 motif 成为 graph / automaton 里的 transition prior。

### 4.3 不能让 substrate 只是“更大的容器”

`CX16-E` 与 `CX17-C` 共同说明：

- substrate 若只是把旧对象堆进去，会放大误差；
- 新 substrate 必须以：
  - viability state
  - macro language
  - motif transitions
  为原生对象。

## 5. Proposed `CX18` Candidate Families

### CX18-A: `RS-VMS` — Viability Macro System

**核心想法**

1. 把 viability oracle 从 score 升级为 **discrete viability state machine**：
   - safe-progress
   - recoverable-boundary
   - reverse-required
   - near-trap
2. 每个 viability state 只允许一小组 native macro families；
3. planner 在线阶段不是“根据 oracle 分数选 macro”，而是：
   - 先进入某个 viability state；
   - 再在该 state 的合法 macro grammar 内搜索。

**为什么比 `CX17-A` 更强**

- `CX17-A` 还是“oracle 选择 macro subset”；
- `CX18-A` 直接让 oracle 成为 macro language 的类型系统。

**理论抓手**

- viability kernel；
- maneuver automata；
- grammar-constrained search。

**创新点**

- 把 viability 与 macro 统一成同一个动作系统，而不是两个模块。

**风险**

- viability state 的离散化若错误，会过度限制 planner；
- 需要更可靠的 state label 管道。

### CX18-B: `RS-MCG` — Motif Compiler Graph

**核心想法**

1. 把 `failure -> escape` memory 升级为 compiler graph：
   - nodes：failure class / escape class / recovered basin class
   - edges：macro family transitions
2. motif graph 不只返回 sequence，而是返回：
   - 下一步应进入的 escape class
   - 合法 macro family 集
   - 预期恢复 basin
3. planner 运行时在 motif graph 上做 very small policy-over-graph，而不是直接调用 raw prefix。

**为什么比 `CX17-B` 更强**

- `CX17-B` 还是 automaton 检索；
- `CX18-B` 把 motif 变成真正的 graph compiler，与 substrate 共享状态对象。

**理论抓手**

- structured memory；
- symbolic behavior graph；
- case-based planning with abstraction transitions。

**创新点**

- 经验被编译成图结构，而不是表项。

**风险**

- 图结构定义复杂；
- 若节点/边定义不稳，可能再次过拟合 hard families。

### CX18-C: `RS-GPS` — Graph Planner Substrate

**核心想法**

1. 用统一 graph substrate 替换当前 `successor_policy` 体系：
   - **Viability Graph**：标记局部可恢复状态
   - **Macro Graph**：表示高价值 maneuver transitions
   - **Motif Prior Graph**：表示 failure-to-escape 结构先验
2. 搜索流程：
   - 先在 graph substrate 上做 mode routing；
   - 再在 local lattice 中做 executable refinement；
   - 若 local refinement 失败，反馈更新 graph state，而不是简单回退。

**为什么比 `CX17-C` 更强**

- `CX17-C` 还是把多对象拼成一个 policy；
- `CX18-C` 直接把这些对象做成统一 graph substrate 的不同层。

**理论抓手**

- hierarchical graph search；
- multi-query reusable planning graphs；
- graph-of-convex-sets / generalized hybrid search。

**创新点**

- 不再存在“外挂 planner hook”这一概念；
- 新系统的 planner 本体就是由 graph substrate 定义的。

**风险**

- 工程量最大；
- 需要重新定义对照边界；
- 若前两条对象还不稳，这条路线会再次放大误差。

## 6. Recommended Execution Order

推荐顺序：`CX18-A -> CX18-B -> CX18-C`

1. **先做 `CX18-A / RS-VMS`**
   - 先验证 viability 是否能真正约束 macro language，而不是只做 activation score。
2. **再做 `CX18-B / RS-MCG`**
   - 若 `A` 能产生局部 ceiling，则用更强 motif compiler 稳定和放大这些 gains。
3. **最后做 `CX18-C / RS-GPS`**
   - 只有 `A/B` 证明对象足够稳，才值得推进 graph substrate 重构。

## 7. Protocol and Acceptance Boundary

`CX18` 仍然以“先追求新 ceiling，再谈压缩”为原则：

1. first-pass gate：
   - public `exp4 exp_delta > 0`
   - `flange exp_delta >= 0`
2. 若通过 public gate，则允许升级到 `rs_root_hard_v2/test`
3. hard-test 上若仍转正，才进入下一阶段 compression planning
4. `mp/csm` 继续做 ordinary-support audit，避免 protocol drift

## 8. Main Recommendation

如果只押一条主线，当前最值得押的是：

> **`CX18-A / RS-VMS`**

原因：

- `CX16-B` 已证明 viability signal 真存在；
- `CX16-A` 已证明 macro language 接近部署边界；
- `CX17-C` 已证明联合 substrate 能带来新的 public ceiling；
- `CX18-A` 正好是这三条证据的最小闭环版本。

如果 `CX18-A` 仍只能给出局部正项而难以泛化，再投入 `CX18-B / RS-MCG`；只有前两者都成立，才值得推进 `CX18-C / RS-GPS`。

## 9. Source Links

- RSS 2019 not-at-fault control: <https://roboticsconference.org/2019/program/papers/011/index.html>
- RSS 2020 ARMTD: <https://roboticsconference.org/2020/program/papers/46.html>
- RSS 2023 neural safe reachability values: <https://roboticsconference.org/2023/program/papers/036/>
- RSS 2024 SPARROWS: <https://roboticsconference.org/2024/program/papers/35/>
- CoRL 2020 PAC motion primitives: <https://proceedings.mlr.press/v155/veer21a.html>
- IGHA*: <https://arxiv.org/abs/2508.13392>
- Motion primitive automata: <https://arxiv.org/abs/2401.14276>
- Experience Graphs: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
- Thunder: <https://arxiv.org/abs/1508.01296>
- RSS 2024 experience-based narrow-corridor planning: <https://roboticsconference.org/2024/program/papers/87/>
- ICLR 2025 VisualPredicator: <https://openreview.net/forum?id=QOfswj7hij>
- RSS 2025 compositional behavior: <https://roboticsconference.org/program/papers/141/>
- MeshA*: <https://openreview.net/forum?id=yoDmNA48yq>
- GCS shortest paths: <https://arxiv.org/abs/2101.11565>
- Multi-query GCS: <https://arxiv.org/abs/2409.19543>
