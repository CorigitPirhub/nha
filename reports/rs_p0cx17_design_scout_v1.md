# P0-CX17 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-12`

## 1. Executive Summary

`CX1-CX16` 已经把当前 `RS + planner-hook augmentation` 路线的主要对象基本跑穿：

- `CX1-CX7`：dense field / residual / guard；
- `CX8-CX9`：semantic intervention 与 semantic lifting；
- `CX10-CX12`：sketch / defer / repair；
- `CX13-CX15`：allocation / episode memory / recoverability-trigger-memory；
- `CX16`：macro / viability / motif / substrate 的首轮系统重构尝试。

这些路线共同说明：

1. **强语义 ceiling 真实存在**，但 successor-level 常驻执行不可部署；
2. **仅靠更好的 gating / defer / review 不能稳定保住 sparse positive signal**；
3. **单独的 recoverability object、motif memory 或 macro library 都还不是完整答案**；
4. **要想追求根本性突破，就必须把 “可恢复性对象 + 原生动作语言 + 失败经验编译 + planner substrate” 做成联合系统，而不是分散外挂。**

因此 `CX17` 的问题不应再写成：

> “如何让当前 accepted planner 再聪明一点？”

而应写成：

> **如何把 viability oracle、macro maneuver language、failure→escape memory 和新的 planner substrate 统一为一个新的 planner system，使其哪怕牺牲时间效率，也能先建立新的效果 ceiling。**

本轮不以时间开销为硬门槛，而以**是否可能带来根本性效果突破**为优先判断。

## 2. What `CX16` Changed — and Why It Was Still Not Enough

`CX16` 已经是最接近“系统性重构”的一轮，因此 `CX17` 必须从 `CX16` 的成败里抽象，而不是重新从 `CX8` 开始。

### 2.1 `CX16-B / RS-VGO`

- public `exp4 exp_delta = +11.556`
- `flange exp_delta = 0.0`
- 但 `mean_time_overhead_ratio = +1.309856`

它证明：

- **viability / recoverability 确实比 token / sketch 更接近真正有用的对象**
- 但 oracle 单独存在时，只能提供“哪里值得动”的弱信号，还不能保证“怎么动”

### 2.2 `CX16-A / RS-NML`

- public `exp4 mean_time_overhead_ratio = +0.239169`
- 但 `exp_delta = -10.0`

它证明：

- 原生 macro library 是当前最接近部署边界的系统改造对象；
- 但如果没有更强的 activation / viability selection，它会对 `narrow_passage` 产生负迁移。

### 2.3 `CX16-D / RS-MEC`

- `flange exp_delta = +4.6`
- overall `exp_delta = -35.667`

它证明：

- failure→escape motif 不是错方向；
- 但当前 motif compiler 还不能稳定匹配“何时该触发”和“触发后该信哪条短 prefix”。

### 2.4 `CX16-C / RS-BLR` 与 `CX16-E / RS-PSR`

它们都显示：

- 如果 trigger 或 substrate 早于正确对象被稳定下来，系统只会更大幅度地放大错误；
- 因而后续更激进的系统重构必须建立在：
  - 更强的 viability object；
  - 更原生的 macro language；
  - 更编译化的 motif memory；
  三者至少两者已经可靠的前提上。

## 3. Literature Sweep

下列文献按用户指定的三个重点组织，只保留与当前项目最相关的顶刊/顶会 primary source。

### 3.1 `viability oracle -> 原生 macro library` 联合路线

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
6. **Incremental Generalized Hybrid A\*** — arXiv 2025  
   Link: <https://arxiv.org/abs/2508.13392>
7. **Optimization-based Motion Primitive Automata for Autonomous Driving** — arXiv 2024  
   Link: <https://arxiv.org/abs/2401.14276>

**启发**

- reachability / viability 给出了“是否仍可恢复”的正确对象；
- motion primitive / maneuver automata 给出了“如何把多步语义编成原生动作语言”的正确对象；
- 但现有工作大多把两者分开：要么做安全/可恢复性判定，要么做 primitive library 设计。

**对当前项目的含义**

- `CX17` 最值得押注的不是 viability oracle 本身，也不是 macro library 本身，而是：
  - **由 viability object 决定何时激活 macro maneuver**
  - **由 macro maneuver 承载 heavy semantic ceiling**

### 3.2 `failure -> escape motif` 的更强编译化版本

1. **Experience Graphs: Leveraging Experience for Planning with Sparse Roadmap Spanners** — RSS 2012 / IJRR  
   Link: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
2. **Thunder Framework: Experience-Based Motion Planning in Changing, Partially-Known Environments** — ICRA 2015  
   Link: <https://arxiv.org/abs/1508.01296>
3. **Experience-based Multi-Agent Path Finding with Narrow Corridors** — RSS 2024  
   Link: <https://roboticsconference.org/2024/program/papers/87/>
4. **VisualPredicator: Learning Abstract World Models with Neuro-Symbolic Predicates for Robot Planning** — ICLR 2025  
   Link: <https://openreview.net/forum?id=QOfswj7hij>

**启发**

- experience reuse 在狭窄/重复几何里成立；
- 传统经验图主要复用“成功路径”；
- Neuro-symbolic abstraction 说明：复杂行为可以被压缩为可复用的离散结构。

**对当前项目的含义**

- `CX15-C` / `CX16-D` 的方向是对的，但经验单元定义得还不够强；
- 下一轮应直接把：
  - failure entry
  - bad maneuver cluster
  - short escape prefix
  - recovered basin signature
  做成统一的 **motif graph / motif automaton**，
  而不是简单的 `key -> sequence` 映射。

### 3.3 planner substrate 级重构

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
6. **Hierarchical Temporal Logic Task and Motion Planning for Multi-Robot Systems** — RSS 2025  
   Link: <https://roboticsconference.org/program/papers/99/>

**启发**

- 若固定 primitive tree / fixed lattice 本身限制了 planner 表达力，外围 guidance 再强也只是补丁；
- modern substrate redesign 的共同点是：
  - 更高层的 mode / macro graph；
  - 更低层的连续或局部细化；
  - query-time 重用离线预计算结果。

**对当前项目的含义**

- `CX17` 若还想追求真正的新 ceiling，最终很可能必须改 substrate；
- 但 substrate 不能是空壳，需要被：
  - viability attributes
  - macro maneuvers
  - compiled motifs
  这三种对象共同定义。

## 4. Structural Limit Analysis

### 4.1 为什么“单独的 viability oracle”不够

`CX16-B` 已经证明：

- oracle 能找出值得干预的局部区间；
- 但若干预语言仍是旧 primitive set，最终只能用 expensive online排序去表达语义；
- 这会再次回到 “效果有了，开销爆炸”。

### 4.2 为什么“单独的 macro library”不够

`CX16-A` 已经证明：

- macro library 可以把 online cost 压到接近可部署；
- 但如果激活条件不够准，macro 会变成对 hard family 的负迁移源。

### 4.3 为什么“单独的 motif compiler”不够

`CX16-D` 已经证明：

- motif 记忆能修复一部分 `flange`；
- 但若 motif 匹配没有被 viability 约束，或者 substrate 不支持 motif 原生执行，
- 它仍会掉进“记住了经验，但调用不稳”的陷阱。

### 4.4 为什么 substrate 重构不能先做

`CX16-E` 已经说明：

- 如果在对象未稳定前就重写 substrate，
- 新 substrate 只会更高效地放大错误结构。

所以 `CX17` 的逻辑必须是：

> **先把 viability object、macro language、motif compiler 做成可组合的离线结构，再考虑 substrate 重构。**

## 5. Proposed `CX17` Candidate Families

### CX17-A: `RS-VML` — Viability-Conditioned Macro Library

**对应焦点**

- `viability oracle -> 原生 macro library` 联合路线

**核心想法**

1. 离线阶段：
   - 用 bounded reverse rollout / local reachability proxy 为局部状态抽象生成 viability label；
   - 用 `CX8-D Heavy` / `CX16-D` 的正向片段提取高价值 maneuver motifs；
   - 将这些 motifs 聚类并编成少量 native macro-primitives。
2. 联合训练一个 `Viability-to-Macro` 模块：
   - 输入：局部几何 patch + oracle label / margin
   - 输出：允许激活的 macro subset
3. 在线阶段：
   - 默认走 accepted `CX3-D`；
   - 只有当 viability object 进入特定边界区间，才把对应 macro primitive 注入候选集。

**如何继承当前有效语义**

- `CX8-D Heavy` 的正向 ceiling 来自多步 maneuver；
- `CX16-B` 证明 viability object 抓到了真实信号；
- `CX17-A` 把这两者第一次做成闭环。

**理论抓手**

- viability kernel / reachable continuation margin；
- macro-action search；
- maneuver automata / motion primitive libraries。

**创新点**

- 不是 oracle 和 macro 各自外挂；
- 而是 **oracle 决定 macro activation language**。

**可行性与风险**

- 可行性高于 substrate 重构；
- 风险在于 viability label 质量和 macro clustering 稳定性。

### CX17-B: `RS-MAG` — Motif Automaton Graph

**对应焦点**

- `failure -> escape motif` 的更强编译化版本

**核心想法**

1. 不再把 motif 存成单条短 sequence；
2. 把经验单元升级为：
   - failure entry class
   - bad maneuver family
   - escape prefix family
   - recovered basin class
   构成的 **motif automaton graph**；
3. 在线阶段不是简单检索一条 sequence，而是：
   - 先匹配当前 entry class；
   - 再沿 automaton 选择最合适的 escape branch；
   - 必要时在 2-3 条 motif 分支间做 very small duel。

**如何继承当前有效语义**

- `CX15-C` / `CX16-D` 已经证明 failure→escape 方向本身是对的；
- `CX17-B` 要解决的是它们的表示能力不够，导致经验复用过弱。

**理论抓手**

- case-based planning；
- experience graphs；
- symbolic / neuro-symbolic automata compression；
- retrieval over structured motif graph。

**创新点**

- 不是经验路径图；
- 不是 scene-level sketch；
- 而是 **failure-to-escape automaton**。

**可行性与风险**

- 数据管道会比 `CX16-D` 重很多；
- 但这是最像“把 sparse positive signal 真正编译出来”的方向。

### CX17-C: `RS-HPS` — Hybrid Planner Substrate

**对应焦点**

- planner substrate 级重构

**核心想法**

1. 用三层 substrate 替代当前单层 fixed primitive tree：
   - **Viability Layer**：标记可恢复 / 边界 / trap-like 区域
   - **Macro Layer**：连接可恢复边界之间的 macro transitions
   - **Local Lattice Layer**：做执行级细化
2. 搜索先在 viability-aware macro graph 上快速排除 hopeless branch；
3. 仅在选中的 macro segment 上下沉到局部 lattice 细化。

**如何继承当前有效语义**

- `CX8-D` 的多步 maneuver semantics 进入 macro layer；
- `CX16-B` 的 viability object 进入 viability layer；
- `CX17-B` 的 motif automaton 进入 macro-edge prior。

**理论抓手**

- generalized hybrid search；
- hierarchical substrate；
- graph-of-convex-sets / multi-query graph reuse；
- multi-resolution planning。

**创新点**

- 不再把新逻辑写成 `successor_policy`；
- 而是把它们做成 planner 原生 substrate。

**可行性与风险**

- 风险最高，工程最大；
- 但如果前两个方向成立，这是最可能带来真正 ceiling shift 的路线。

## 6. Recommended Execution Order

推荐顺序：`CX17-A -> CX17-B -> CX17-C`

1. **先做 `CX17-A / RS-VML`**
   - 这是当前最有证据基础的突破口；
   - 也是最直接验证“oracle + macro 是否真能闭环”的路线。
2. **再做 `CX17-B / RS-MAG`**
   - 若 `CX17-A` 只得到局部 gain，则用更强 motif compiler 放大并稳定 sparse signal。
3. **最后做 `CX17-C / RS-HPS`**
   - 只有当 `A/B` 已明确对象正确，才值得把它们嵌入新的 planner substrate。

## 7. Protocol and Acceptance Boundary

由于本轮明确“不必在意时间开销”，`CX17` 的第一轮不再用 `<0.30` overhead 作为 go/no-go 的首要门槛。

推荐的第一轮判断顺序应改为：

1. **Primary gate**
   - public `exp4 exp_delta > 0`
   - `flange exp_delta >= 0`
2. **Secondary diagnostics**
   - overhead 仍必须记录；
   - 但只作为后续压缩工作的输入，而不是立即否决信号。
3. **Hard escalation**
   - 只要 public overall 明确转正且 `flange` 不退化，就允许消费 `rs_root_hard_v2/test`；
   - 目标是先确认是否出现新的效果 ceiling。

## 8. Main Recommendation

如果只押一条最可能带来根本突破的主线，应押：

> **`CX17-A / RS-VML`**

原因：

- `CX16-B` 已证明 oracle object 有效；
- `CX16-A` 已证明 macro language 接近可部署；
- `CX17-A` 是第一次把两者真正做成联合系统，而不是串联的弱耦合外挂。

如果 `CX17-A` 成功，`CX17-B` 会是自然的第二步，用来把 sparse maneuver ceiling 编译成更强的结构记忆；若 `A/B` 同时成功，才有理由推进 `CX17-C`。

## 9. Source Links

- RSS 2019 not-at-fault control: <https://roboticsconference.org/2019/program/papers/011/index.html>
- RSS 2020 ARMTD: <https://roboticsconference.org/2020/program/papers/46.html>
- RSS 2023 neural safe reachability values: <https://roboticsconference.org/2023/program/papers/036/>
- RSS 2024 SPARROWS: <https://roboticsconference.org/2024/program/papers/35/>
- CoRL 2020 PAC motion primitives: <https://proceedings.mlr.press/v155/veer21a.html>
- 2022 adaptive motion primitives: <https://arxiv.org/abs/2212.14307>
- IGHA*: <https://arxiv.org/abs/2508.13392>
- optimization-based motion primitive automata: <https://arxiv.org/abs/2401.14276>
- Experience Graphs: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
- Thunder: <https://arxiv.org/abs/1508.01296>
- RSS 2024 experience-based MAPF with narrow corridors: <https://roboticsconference.org/2024/program/papers/87/>
- ICLR 2025 VisualPredicator: <https://openreview.net/forum?id=QOfswj7hij>
- MeshA*: <https://openreview.net/forum?id=yoDmNA48yq>
- Shortest Paths in Graphs of Convex Sets: <https://arxiv.org/abs/2101.11565>
- Multi-Query GCS: <https://arxiv.org/abs/2409.19543>
- RSS hierarchical any-angle multi-resolution planning: <https://roboticsconference.org/program/papers/49/>
- RSS hierarchical TAMP with GCS: <https://roboticsconference.org/program/papers/99/>
