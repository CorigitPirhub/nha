# P0-CX16 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-12`

## 1. Executive Summary

到 `CX15` 为止，`P0-CX` 的主要路线已经很清楚地分成四个大类：

1. `CX1-CX7`：dense field / residual / guard；
2. `CX8-CX9`：semantic intervention 与 coarse semantic lifting；
3. `CX10-CX12`：sketch / defer / repair；
4. `CX13-CX15`：allocation / episode-memory / recoverability-trigger-memory。

这四类路线已经共同给出一个稳定判断：

- **有效 ceiling 真实存在**，但常驻 successor-level 执行不可部署；
- **仅靠 token discrimination 无法可靠区分 `flange trap` 与 `recoverable narrow passage`**；
- **仅靠 computation allocation 不会自动带来 leverage**；
- **仅靠 episode-local failure memory 也不足以形成稳健优势**。

因此 `CX16` 不能再是 “再聪明一点的 score / gate / memory”。

`CX16` 需要允许较大幅度的系统性改动，把对象抬升为：

1. **原生 macro-primitive / maneuver substrate**；
2. **recoverability / viability oracle**；
3. **event-triggered bounded local review**；
4. **failure-to-escape motif compiler**；
5. **planner substrate redesign**。

换句话说，`CX16` 的目标不是继续补丁式地“让 accepted planner 再聪明一点”，而是尝试：

> **让 planner 原生地拥有更强动作语言、更明确的可恢复性对象、更严格的局部审查入口，以及可复用的失败-逃逸经验。**

## 2. What `CX1-CX15` Actually Proved

### 2.1 已基本跑穿的方向

- `dense field / residual / calibration`：能做保护，不能带来稳定强增益；
- `successor-level heavy semantics`：有 ceiling，但 runtime 过高；
- `coarse semantic atlas / strategy lift`：dev 可行，locked test 不稳；
- `sketch / defer / repair`：能消害，但不能保益；
- `static schedule / contract / allocation`：只会重分配搜索，不会产生 leverage；
- `episode-local repeated-failure memory`：有方向信号，但若不含 recoverability 语义，压缩后容易退化为 tie；
- `recoverability / trigger / memory` 组合：对象更接近本质，但在当前实现下仍没过 public gate。

### 2.2 现在真正还缺什么

当前最缺的不是“更强的预测器”，而是：

1. **动作语言重构**：当前 primitive set 本身可能就不够表达真正有价值的多步 maneuver；
2. **可恢复性对象化**：当前 planner 还没有真正的一等 recoverability / viability object；
3. **有边界的审查机制**：额外 computation 需要被严格限制在事件触发窗口内；
4. **跨 episode 编译式经验**：不是“记住路径”，而是“记住失败入口和可逃逸前缀”；
5. **底层 substrate 重构**：若现有 fixed-step Hybrid A* 本体就是瓶颈，外围 hook 永远只能治标。

## 3. Literature Sweep

以下调研按用户要求的五个方向组织，优先保留顶刊/顶会 primary source。

### 3.1 原生 macro-primitive / maneuver library 重构

1. **Probably Approximately Correct Vision-Based Planning using Motion Primitives** — CoRL 2021  
   Link: <https://arxiv.org/abs/2002.12852>
2. **Policy Optimization to Learn Adaptive Motion Primitives in Path Planning with Dynamic Obstacles** — 2022  
   Link: <https://arxiv.org/abs/2212.14307>
3. **Incremental Generalized Hybrid A\*** — 2025  
   Link: <https://arxiv.org/abs/2508.13392>
4. **Safe-by-Design Motion Primitives for Planning in Autonomous Driving** — ICRA 2024  
   Link: <https://ieeexplore.ieee.org/document/10610346>

**启发**

- motion primitive 的组织方式本身就是 planner 能力的一部分；
- adaptive primitive / generalized hybrid search 的收益来自：
  - 更丰富的动作库；
  - 更合适的模式切换；
  - 对非完整约束和倒车 setup 的原生表达；
- “safe-by-design primitive” 很适合当前项目，因为它把复杂语义编进 primitive，而不是编进在线 classifier。

**局限**

- 现有工作大多在已有 primitive set 上做适配或安全筛选；
- 很少把 **failure-derived maneuver motifs** 直接编进原生 library。

### 3.2 recoverability / viability oracle 作为一等对象

1. **Towards Provably Not-at-Fault Control of Autonomous Robots in Arbitrary Dynamic Environments** — RSS 2019  
   Link: <https://roboticsconference.org/2019/program/papers/011/index.html>
2. **ARMTD: Anytime Robot Motion Planning with Transit-Driving Modes and Reachability-Based Safety** — RSS 2020  
   Link: <https://roboticsconference.org/2020/program/papers/46.html>
3. **Neural Value Functions for Safe Reachability-Based Control of Autonomous Systems** — RSS 2023  
   Link: <https://roboticsconference.org/2023/program/papers/036/>
4. **Real-Time Control for Autonomous Racing Based on Viability Theory and Connected Invariant Sets** — TRO / arXiv  
   Link: <https://arxiv.org/abs/2102.08446>

**启发**

- 真正关键的不是“当前是不是危险”，而是“从这里是否还存在可恢复 continuation”；
- reachability / viability 可被蒸馏成局部 margin 或 oracle；
- neural value / viability 近似说明：复杂可恢复性对象可以离线学、在线查。

**局限**

- full reachability 直接在线执行太贵；
- 必须压缩成小尺度 oracle / cache / lattice attribute 才可能部署到本项目。

### 3.3 事件触发的 bounded local review

1. **Generalized Lazy Search for Robot Motion Planning: Interleaving Search and Edge Evaluation via Event-Based Toggles** — ICAPS 2019  
   Link: <https://icaps19.icaps-conference.org/accepted-papers.html>
2. **When to Replan?** — ICRA 2024  
   Link: <https://www.omron.com/sinicx/research/reserach_result/all/ICRA2024_WhenToReplan.html>
3. **Adaptive Online Replanning with Diffusion Models** — NeurIPS 2023  
   Link: <https://proceedings.neurips.cc/paper_files/paper/2023/hash/f0af4dae6dd13c3847cc2a0f41541f2f-Abstract-Conference.html>
4. **Learning Efficient Abstract Planning Models that Choose What to Predict** — CoRL 2023 / OpenReview  
   Link: <https://openreview.net/forum?id=ba27-RzQssu>

**启发**

- 高开销 computation 必须由异常事件触发；
- “何时额外计算”与“算什么”同等重要；
- bounded review 适合当前项目，因为它可以保留 `CX8-D` 的局部 bundle semantics，而不让其常驻。

**局限**

- 现有工作更多是 replanning / edge evaluation / abstract model selection；
- 很少把事件触发和非完整约束局部 maneuver review 严格绑定。

### 3.4 跨 episode 的 failure→escape motif 编译

1. **Experience Graphs: Leveraging Experience for Planning with Sparse Roadmap Spanners** — RSS 2012 / IJRR  
   Link: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
2. **Thunder Framework: Experience-Based Motion Planning in Changing, Partially-Known Environments** — ICRA 2015  
   Link: <https://arxiv.org/abs/1508.01296>
3. **Generalized Experience-Based Multi-Agent Path Finding with Narrow Corridors** — RSS 2024  
   Link: <https://roboticsconference.org/program/papers/065/>
4. **VisualPredicator: Learning Abstract World Models with Neuro-Symbolic Predicates for Robot Planning** — ICLR 2025  
   Link: <https://openreview.net/forum?id=mqIQE8BftT>

**启发**

- narrow / repetitive geometry 下，experience reuse 是成立的；
- 传统 experience graph 更偏向复用成功路径；
- 对当前项目，最值得编译的对象其实是：
  - 失败入口；
  - 错误 maneuver 族；
  - 短逃逸模式。

**局限**

- 现有工作很少显式存储 “failure-to-escape” 单元；
- 更少把它编译成可在 Hybrid A* 中 O(1) / O(log N) 调用的 motif memory。

### 3.5 planner substrate 级别重构

1. **MeshA\*: Efficient Path Planning by Integrating Vehicle Dynamics into the Search Graph** — CoRL 2025  
   Link: <https://openreview.net/forum?id=yoDmNA48yq>
2. **Incremental Generalized Hybrid A\*** — 2025  
   Link: <https://arxiv.org/abs/2508.13392>
3. **Motion Planning around Obstacles with Convex Optimization** — TRO 2018 (Graph-of-Convex-Sets lineage precursor)  
   Link: <https://ieeexplore.ieee.org/document/7989152>
4. **Shortest Paths with Graphs of Convex Sets** — arXiv / optimization-planning line  
   Link: <https://arxiv.org/abs/2101.11565>

**启发**

- 如果固定 primitive tree / fixed lattice 本身有瓶颈，那么外围 guidance 再聪明也只是补丁；
- substrate 级重构可以从两条路入手：
  - 更强的离散搜索图（generalized hybrid / mesh / reversible lattice）；
  - 连续/混合结构（convex-set graph / mode graph / macro graph）。

**局限**

- 这些工作往往解决的是效率、动态一致性或连续优化接口；
- 尚未把 recoverability oracle、macro library、failure motif 统一到同一 substrate。

## 4. Structural Limit Analysis

现有文献虽然各自很强，但直接照搬仍解决不了当前项目的核心问题：

1. **macro primitive 论文** 往往假设 library 已给定，缺少从 hard failure 中自动编译新 macro 的机制；
2. **viability / reachability 论文** 有正确对象，但直接在线算太贵；
3. **lazy / replanning 论文** 会告诉你“什么时候该多算一点”，但不告诉你“应该复查哪种 nonholonomic maneuver”；
4. **experience graph 论文** 更擅长复用成功路径，不擅长复用失败-逃逸对；
5. **substrate 重构论文** 会改变图结构，但不自动提供 recoverability semantics。

因此 `CX16` 不能照抄某篇现成论文，而应把上述五条线真正组合起来。

## 5. Proposed `CX16` Candidate Families

### CX16-A: `RS-NML` — Native Macro Library

**对应焦点**

- 原生 macro-primitive / maneuver library 重构

**核心想法**

1. 不再把 `reverse-setup` 视作 planner 偶然拼出来的多步行为；
2. 直接把少量高价值 maneuver 编成原生 macro-primitives：
   - reverse-setup-left
   - reverse-setup-right
   - escape-swerve-left/right
   - micro-k-turn / stall-recover
3. macro library 既可手工初始化，也可从 `CX8-D Heavy` / `CX15-C` 的 failure→escape 数据中离线编译；
4. planner 在线不再“猜测要不要反向 setup”，而是原生可选。

**如何继承当前有效语义**

- 直接继承 `CX8-D Heavy` 唯一被证明有价值的部分：关键多步 maneuver。

**理论抓手**

- macro-action search；
- maneuver automata；
- hierarchical motion primitives。

**创新点**

- 不是 learned bias；
- 不是 semantic token；
- 而是 **把正向语义硬编码进 planner 原生动作语言**。

**可部署性**

- 在线只增加固定少量 macro primitive；
- 单次扩展代价仍是常数倍，而不是调用重模型。

**风险**

- macro 设计不当会让 branching factor 膨胀；
- 需要谨慎控制 primitive 数量与适用窗口。

### CX16-B: `RS-VGO` — Viability-Guided Oracle

**对应焦点**

- recoverability / viability oracle 作为一等对象

**核心想法**

1. 为局部状态抽象建立 viability / recoverability oracle：
   - 这里仍可恢复；
   - 这里处于半可恢复边界；
   - 这里已接近不可恢复 trap。
2. oracle 的标签不从 family 来，而是从 bounded reverse rollout / local reachability proxy 蒸馏得到；
3. 在线阶段 oracle 既可以是小网络，也可以是 coarse cache / lattice attribute。

**如何继承当前有效语义**

- 把 `CX8-D` 中“什么时候必须 reverse-setup 才能继续”的语义改写为 viability margin。

**理论抓手**

- viability kernel；
- reachable set approximation；
- fail-safe margin。

**创新点**

- 把 `recoverability` 从隐含逻辑变成 planner 可查询的一等对象；
- 不是 semantic classifier，而是 planner state attribute。

**可部署性**

- 若采用 cache / distilled oracle，在线可做到 `O(1)` 查询。

**风险**

- oracle 若失真，可能再次误伤 `flange` / `narrow` 边界；
- 需要可靠标签管道。

### CX16-C: `RS-BLR` — Bounded Local Review

**对应焦点**

- 事件触发的 bounded local review

**核心想法**

1. accepted `RS + refined CX3-D` 作为默认主干；
2. 只有在 anomaly trigger 出现时才启动 review：
   - duplicate burst
   - accepted successor ratio collapse
   - open-list entropy collapse
   - viability margin sudden drop
3. review 只在局部窗口内运行少量 alternative macro / reverse rollout / local bundle duel；
4. review 完成后把结果写回局部优先级，再立即退回 baseline。

**如何继承当前有效语义**

- 保留 `CX8-D` 的局部 maneuver comparison；
- 但把执行范围限制在少数异常窗口。

**理论抓手**

- event-triggered computation allocation；
- lazy search；
- bounded local counterfactual review。

**创新点**

- 不是 replanning；
- 不是 global schedule；
- 而是 **局部异常窗口上的 conditional search fork**。

**可部署性**

- 若触发器稀疏，总代价与窗口数成正比，而不与全部 expansions 成正比。

**风险**

- 触发器若不稳，会再次走向 `CX15-B` 的 public collapse。

### CX16-D: `RS-MEC` — Motif Escape Compiler

**对应焦点**

- 跨 episode 的 failure→escape motif 编译

**核心想法**

1. 以 `failure entry -> short escape prefix -> recovered basin` 为最小经验单元；
2. 对这些 motif 做离线聚类、量化、压缩，得到一个可查询的 motif compiler；
3. 在线阶段只做：
   - 检索当前 entry 是否匹配既有失败模式；
   - 若匹配，则注入一个极短 escape prefix bias。

**如何继承当前有效语义**

- `CX8-D` 的正向语义常体现为少数关键 reverse / setup maneuver；
- `MEC` 试图把它们从 full semantic policy 中提纯成可复用 motif。

**理论抓手**

- case-based planning；
- experience compilation；
- vector-quantized memory / symbolic compression。

**创新点**

- 不是存成功整条路径；
- 而是把“失败经验”直接编译成 planner 可调用的局部指令。

**可部署性**

- 若索引结构合理，在线代价可做到 `O(1)` hash 或 `O(log N)` ANN 检索。

**风险**

- motif 泛化不足时，可能再次造成 public 上的误注入；
- 需要新的数据管道与 motif schema。

### CX16-E: `RS-PSR` — Planner Substrate Redesign

**对应焦点**

- planner substrate 级别重构

**核心想法**

1. 不再把当前 fixed primitive Hybrid A* 视为不可动的 substrate；
2. 重构为多层 substrate，例如：
   - macro graph layer：原生 maneuver / border-to-border transitions
   - local lattice layer：细粒度可执行 primitive
   - viability attribute layer：为每个 macro / local state 提供 recoverability attributes
3. 搜索先在 macro / mode graph 上做粗筛，再进入局部细化。

**如何继承当前有效语义**

- 把 `CX8-D` 的多步 maneuver semantics、`CX15` 的 recoverability object、`CX14` 的 failure memory 统一到新的 substrate 中。

**理论抓手**

- hierarchical search substrate；
- generalized hybrid search；
- graph-of-convex-sets / hybrid graph。

**创新点**

- 不是再外挂一个 policy hook；
- 而是直接���写 planner backbone 的表达能力。

**可部署性**

- 风险最高，但一旦成立，最有机会带来质变而非局部修补。

**风险**

- 工程复杂度最高；
- 与现有代码差异最大；
- 需要重新定义实验边界与对照。

## 6. Recommended Execution Order

候选标签按用户要求对应五个焦点，但推荐执行顺序不按字母，而按证据链组织：

### 推荐执行顺序：`CX16-B -> CX16-C -> CX16-D -> CX16-A -> CX16-E`

1. **先做 `CX16-B / RS-VGO`**
   - 先验证 recoverability object 本身是否终于具备区分力；
   - 这是后续所有路线的共同前提。
2. **再做 `CX16-C / RS-BLR`**
   - 若有了 oracle，再测试 bounded local review 是否能低成本保住正向语义。
3. **第三做 `CX16-D / RS-MEC`**
   - 如果 `B/C` 有局部信号，再把 sparse escape semantics 编译为跨 episode memory。
4. **第四做 `CX16-A / RS-NML`**
   - 若前面三步确认正向 maneuver 真的稳定，再把它们原生化为 macro library。
5. **最后做 `CX16-E / RS-PSR`**
   - 这是最高风险、最高潜力的基座重构路线，应在前述证据足够时再投入。

## 7. Main Recommendation

如果只允许押一条主线，最值得押的是：

> **`CX16-B / RS-VGO` + `CX16-C / RS-BLR`**

原因：

- `VGO` 解决的是“到底缺什么对象”；
- `BLR` 解决的是“如何把高价值 computation 限制在少量窗口内”；
- 这两个问题若不先解决，`macro library` 和 `substrate redesign` 都很容易变成高复杂度重构但缺乏可验证 leverage 的工程冒险。

## 8. Source Links

- CoRL 2021 PAC motion primitives: <https://arxiv.org/abs/2002.12852>
- 2022 adaptive motion primitives: <https://arxiv.org/abs/2212.14307>
- 2025 Incremental Generalized Hybrid A*: <https://arxiv.org/abs/2508.13392>
- ICRA 2024 safe-by-design motion primitives: <https://ieeexplore.ieee.org/document/10610346>
- RSS 2019 not-at-fault control: <https://roboticsconference.org/2019/program/papers/011/index.html>
- RSS 2020 ARMTD: <https://roboticsconference.org/2020/program/papers/46.html>
- RSS 2023 neural safe reachability values: <https://roboticsconference.org/2023/program/papers/036/>
- TRO viability theory / connected invariant sets: <https://arxiv.org/abs/2102.08446>
- ICAPS 2019 generalized lazy search: <https://icaps19.icaps-conference.org/accepted-papers.html>
- ICRA 2024 When to Replan?: <https://www.omron.com/sinicx/research/reserach_result/all/ICRA2024_WhenToReplan.html>
- NeurIPS 2023 adaptive online replanning: <https://proceedings.neurips.cc/paper_files/paper/2023/hash/f0af4dae6dd13c3847cc2a0f41541f2f-Abstract-Conference.html>
- CoRL 2023 choose what to predict: <https://openreview.net/forum?id=ba27-RzQssu>
- RSS 2012 Experience Graphs: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
- ICRA 2015 Thunder: <https://arxiv.org/abs/1508.01296>
- RSS 2024 generalized experience-based MAPF with narrow corridors: <https://roboticsconference.org/program/papers/065/>
- ICLR 2025 VisualPredicator: <https://openreview.net/forum?id=mqIQE8BftT>
- AAAI 2018 avoiding dead ends in real-time heuristic search: <https://ojs.aaai.org/index.php/AAAI/article/view/11508>
- JAIR 2012 depression avoidance and learning: <https://www.jair.org/index.php/jair/article/view/10817>
- CoRL 2025 MeshA*: <https://openreview.net/forum?id=yoDmNA48yq>
- TRO 2018 motion planning around obstacles with convex optimization: <https://ieeexplore.ieee.org/document/7989152>
- Graphs of Convex Sets shortest paths: <https://arxiv.org/abs/2101.11565>
