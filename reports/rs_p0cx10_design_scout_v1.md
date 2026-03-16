# P0-CX10 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-10`

## 1. Executive Summary

`P0-CX1-9` 的累计证据已经把当前主矛盾压缩得非常清楚：

- `CX8-D Heavy` 证明 **语义干预本身是真实有效的**。在 `rs_root_hard_v2/test` 上，相对 accepted `RS + refined CX3-D / RS-HPG` 仍有 `exp_delta = +58.575`，但同时带来 `mean_time_overhead_ratio = 1.2856` 的不可部署开销；
- `CX9-A` 证明 **把语义上提到更高层** 可以把在线成本压到近零，但其 tuned 版本虽然在 dev 上达到 `exp_delta = +814.714`，锁定参数后在 `rs_root_hard_v2/test` 上 `exp_delta = 0.0`，说明“粗粒度语义图谱”没有形成稳定泛化；
- 因而 `CX10` 的任务不再是“找一个更强网络”，而是：**把 `CX8-D Heavy` 的高复杂度有效语义，编译成低成本、可验证、可泛化的执行结构**。

这意味着 `CX10` 必须显式跳出 `CX1-CX9` 的两条失败路径：

1. **继续做更强的 dense/scalar field 修正**：这条路已被 `CX1-CX7` 基本耗尽，难以表达“reverse-setup -> forward-thread”这种多步策略；
2. **继续做 per-successor 的在线仲裁**：这条路被 `CX8-D Heavy` 证明有效但代价爆炸。

`CX10` 的正确问题定义应为：

> 如何把“瓶颈识别 + bundle 策略 + setup/commit 时序”编译成 `rulebook / automaton / sketch / sparse script` 这样的低成本执行结构，使在线代价近似 `O(1)` 或 `O(K)`，而不是 `O(N_expand · |A| · C_phi)`？

## 2. Problem Reframing

### 2.1 从 `CX8-D Heavy` 与 `CX9-A` 得到的硬事实

1. `CX8-D Heavy` 的正增益主要来自 **瓶颈区域的正确 maneuver bundle 选择**，而不是更精细的标量 heuristic；
2. `CX8-D Heavy` 的失败原因不是“语义无效”，而是 **成功语义被放在了错误的计算层级上**；
3. `CX9-A` 的失败原因不是“语义上提必然无效”，而是 **上提后的表示过于粗糙，无法稳定保真地携带 `CX8-D` 的时序语义**；
4. 因而 `CX10` 的对象不应再是 `value correction`，而应是 **可执行的条件策略结构**。

### 2.2 `CX10` 的新问题定义

不再问“如何给每个 state/successor 一个更准的分数”，而要问：

> 如何在极少数关键区域，触发少量结构化、多步、可回退的语义程序？

更具体地，`CX10` 需要同时做到：

- **保留 `CX8-D` 的成功语义**：瓶颈检测、reverse-setup、forward-thread、phase persistence；
- **避免 `CX8-D` 的代价形态**：严禁 per-successor 深模型前向；
- **避免 `CX9-A` 的泛化失败**：不能只靠 coarse region atlas，需要把语义绑定到更稳定的谓词、事件或程序结构上；
- **保留 accepted baseline 的安全边界**：默认 `neutral`，高置信才干预，始终保留 anchor fallback。

### 2.3 复杂度目标

设：

- `N`：搜索扩展节点数；
- `|A|`：每节点 primitive 数；
- `C_phi`：重语义模块一次推理成本；
- `C_compile`：scene-level 一次性编译成本；
- `C_exec`：在线执行 compiled structure 的成本。

目标从 `CX8` 的：

- `O(N · |A| · C_phi)`

转为 `CX10` 的：

- `O(C_compile) + O(N · C_exec)`，且 `C_exec` 近似常数、`C_compile` 与瓶颈数 `K` 或原型数 `P` 成正比，而不是与 `N · |A|` 成正比。

### 2.4 `CX10` 的非协商设计约束

1. **禁止 per-successor 深模型推理**；
2. **默认 abstain / neutral**，只有高置信且在支持域内才激活策略；
3. **干预对象必须是结构化语义对象**：如 rule、state、script、macro event，而不是新的 dense scalar map；
4. **必须能对接当前架构**：`rs_cx` 模块 + planner hook，不允许重写整套 planner；
5. **必须可做 honest locked eval**：dev 上选型后，test 上不再调参。

## 3. Literature Scan: What the Field Already Knows

下面只保留与“高语义 / 低在线成本”最相关的 primary-source 文献，并围绕三个方向做批判性归纳。

### 3.1 Neuro-Symbolic / Programmatic Planning

| Work | Venue / Source | 对 `CX10` 的启发 | 对当前项目的局限 |
| --- | --- | --- | --- |
| *Programmatic Reinforcement Learning without Oracles* | ICLR 2022 / OpenReview — <https://openreview.net/forum?id=G8EkpJ7mgRT> | 证明策略可以被合成为显式程序，而不必保留为黑箱网络 | 面向完整 RL policy；我们需要的是“planner 上的局部语义增量”而不是整策略替换 |
| *Hierarchical Programmatic Reinforcement Learning* | ICML 2023 / PMLR — <https://proceedings.mlr.press/v202/liu23at.html> | 用层级程序表达长程任务结构，适合承载多步 maneuver 语义 | 仍偏控制/任务策略，不直接讨论 search-loop 成本 |
| *POETREE: Policy Extraction from Deep Reinforcement Learning for Interpretable Decision-Making with Adaptive Expertise Distillation* | ICLR 2022 / OpenReview — <https://openreview.net/forum?id=0u6pqUvCYlN> | 证明可以把黑箱策略蒸馏成浅层树结构，以换取可解释与低成本执行 | 目标是拟合整策略；我们更适合提炼“只在 bottleneck 激活的 delta rulebook” |
| *VisualPredicator: Learning Abstract World Models with Neuro-Symbolic Predicates for Robot Planning* | ICLR 2025 / OpenReview — <https://openreview.net/forum?id=mqIQE8BftT> | 用 predicate-level 表示学习可泛化世界模型，说明“谓词化”有利于组合泛化 | 主要解决对象-关系抽象；我们要解决 nonholonomic bottleneck 时序 |
| *Provably Correct Compositional Policies via Automata Embeddings* | arXiv / primary source — <https://arxiv.org/abs/2410.03814> | 自动机是压缩长程语义且保持可验证性的自然载体 | 关注组合任务规格，不直接面向 classical planner 的局部 bias 控制 |
| *Planning with a Learned Policy Basis to Optimally Solve Complex Tasks* | OpenReview / primary source — <https://openreview.net/forum?id=Ht90v3Wqvb> | 用小型 policy basis + 高层规划求解复杂任务，说明“先学 basis 再组合”可行 | 仍是 policy-composition 视角；尚未回答如何与 Hybrid A* 的 node expansion 对接 |

**批判性结论**：

- 这一脉络证明：**复杂策略逻辑可以被编译到程序、树、自动机或 predicate 图中**；
- 但现有工作大多默认“我要替换整策略/整规划器”；
- 当前项目真正的创新窗口是：**只编译 `CX8-D Heavy` 已被验证有效的那一小段 bottleneck semantics**，并把它作为 accepted `CX3-D` 之上的“稀疏 delta intervention layer”。

### 3.2 Adaptive Sampling / Query-Efficient Guidance

| Work | Venue / Source | 对 `CX10` 的启发 | 对当前项目的局限 |
| --- | --- | --- | --- |
| *Query-Efficient Planning in Deterministic MDPs under Linear Realizability and Optimal Partial Feedback* | COLT 2021 / PMLR — <https://proceedings.mlr.press/v134/chen21a.html> | 理论上支持“不是每个节点都值得昂贵查询”，关键是把昂贵计算集中在信息增益最高的部分 | 偏理论，不直接给 nonholonomic planning 的实现模板 |
| *Learned Critical Probabilistic Roadmaps for Robotic Motion Planning* | primary source — <https://arxiv.org/abs/1910.14634> | 关键节点/critical states 可以大幅提升规划效率，说明“瓶颈而非全局”才是稀缺对象 | 目标是 roadmap sampling，不是对 Hybrid A* primitive bias 做条件干预 |
| *Long Range Navigator: Yet Another Way to Inject Language Models in Robotics* | CoRL 2025 / OpenReview — <https://openreview.net/forum?id=JwrnoB1tR0> | 通过高层稀疏 guidance 解决长程任务，而非在每一步做昂贵推理 | 语言与语义导航设定和本项目不同，但其“稀疏高层指导”思路 relevant |
| *PIVOT-R: Primitive-Driven Waypoint-Oriented Task and Motion Planning for Runtime-Aligned Long-Horizon Robotic Manipulation* | CoRL 2024 / OpenReview — <https://openreview.net/forum?id=YXik8d8ou0> | 强调 primitive-driven sparse coordination 与 runtime-aligned 执行频率 | 更偏 manipulation TAMP；但“高低频控制解耦”对我们非常关键 |

**批判性结论**：

- 真正昂贵的语义判断不该平均施加到所有节点；
- 这一方向最重要的启发不是“学更强的 sampler”，而是：
  - **把计算预算绑定到 critical windows / bottleneck gates / support-critical clusters 上**；
  - 让 planner 在绝大多数 trivial nodes 上完全回退 baseline；
- 当前项目缺的不是再做一个 sampling policy，而是 **把 `CX8-D` 的 bundle semantics 绑定到“何时值得计算”的机制上**。

### 3.3 Model-Based Reasoning with Prediction Horizon

| Work | Venue / Source | 对 `CX10` 的启发 | 对当前项目的局限 |
| --- | --- | --- | --- |
| *Learning over Subgoals for Efficient Navigation of Structured, Unknown Environments* | CoRL 2018 / PMLR — <https://proceedings.mlr.press/v87/huang18a.html> | 子目标可以把长程依赖压缩成少量战略决策 | 只输出 waypoint，不表达 maneuver semantics |
| *Learning Efficient Abstract Planning Models that Choose What to Predict* | CoRL 2022 / OpenReview — <https://openreview.net/forum?id=ba27-RzQssu> | 抽象模型不需要预测一切，只需预测对计划最重要的少量变量 | 非常契合 `CX10` 的“只编译 bottleneck semantics” |
| *Overcoming the Pitfalls of Prediction Error in Model-Based Planning* | arXiv / primary source — <https://arxiv.org/abs/2403.17991> | 指出长 horizon 规划中最怕错误传播，因此应限制预测对象与验证路径 | 支持我们引入 verifier / abstain，而不是让 learned script 直接接管 planner |
| *Subgoal Diffuser: Offline Goal-Conditioned Trajectory Diffusion for Subgoal Generation in Robot Manipulation* | ICRA 2024 / arXiv — <https://arxiv.org/abs/2402.05157> | 一次性生成稀疏 subgoal sequence 比逐步决策更省在线成本 | 仍是 subgoal/trajectory object，而不是非完整约束 bundle program |
| *Hybrid Search for Efficient Planning with Completeness Guarantees* | arXiv 2023 — <https://arxiv.org/abs/2310.12819> | 高层引导 + 底层完备搜索的组合，是当前项目能兼容的正确骨架 | 还没有把 bottleneck semantic script 显式做成对象 |
| *Combined Task and Motion Planning via Sketch Decompositions* | OpenReview / primary source — <https://openreview.net/forum?id=ojc4aWQfP2> | “Sketch” 是在全规划之前压缩长期结构的一种方式 | 现有 sketch 多是 symbolic task skeleton，不包含 local maneuver choice |

**批判性结论**：

- `CX10` 不需要一个更会“预测整条轨迹”的模型；
- 它需要一个只预测 **瓶颈位置、策略 phase、激活条件** 的极稀疏 structure；
- 因而最值得借鉴的不是 generative planner 本身，而是其中的三条原则：
  1. **只预测关键变量**；
  2. **把长期依赖压缩成 sketch/program**；
  3. **保留 verifier 与底层完备搜索，避免 learned proposal 直接接管全局决策**。

## 4. What `CX10` Must Add Beyond the Literature

相对于现有工作，`CX10` 需要同时新增四个东西：

1. **局部但高价值的语义对象**：不是整策略、不是整图谱，而是 `bottleneck-triggered maneuver semantics`；
2. **编译式执行**：训练时允许使用昂贵 teacher / counterfactual rollout，但测试时只能执行编译后的 rule / state / sketch；
3. **保守 fallback**：默认 `neutral`，不在支持域内就回到 accepted `CX3-D`；
4. **planner-hook compatibility**：所有候选都必须能在现有 `planner hook` 上落地，而不是另起炉灶。

这也是 `CX10` 与 `CX9` 的本质区别：

- `CX9` 想把语义存成图谱/场；
- `CX10` 想把语义**编译成程序结构**。

## 5. Frozen Candidate Families

### Candidate Summary

| ID | Name | 编译对象 | 在线成本形态 | 继承 `CX8-D` 的方式 | 主要风险 |
| --- | --- | --- | --- | --- | --- |
| `CX10-A` | `RS-CEC` | prototype rulebook / shallow decision list | `O(1)` feature calc + lookup | 用 `CX8-D Heavy` counterfactual win states 蒸馏 bottleneck bundle rule | teacher bias / prototype 覆盖不足 |
| `CX10-B` | `RS-HBC` | scene-specific bottleneck script | `O(K)` scene compile + `O(1)` gate check | 把 reverse-setup / thread-through 编译为稀疏窗口脚本 | 漏检关键 gate 时收益消失 |
| `CX10-C` | `RS-NFA` | finite-state automaton over predicates | `O(1)` state update + template lookup | 把 bundle commit 的时序依赖转成状态迁移 | trace mining 与状态设计难度较高 |
| `CX10-D` | `RS-LAS` | one-shot maneuver sketch | one-shot prediction + `O(K)` gate checks | 把多步语义压缩为极短 macro sketch | sketch 分布漂移、验证器设计难 |

---

### CX10-A: `RS-CEC` — Counterfactual Experience Compilation

**方案名称与类型**：
- `RS-CEC`；
- 类型：`teacher-distilled sparse rulebook / prototype retrieval`。

**核心想法**：
1. 用 `CX8-D Heavy` 作为离线 teacher，在 hard scenes 上采集“何时它的 bundle arbitration 真正改善了 search effort”的 counterfactual states；
2. 只保留这些 states 的廉价解析几何特征，例如 clearance、corridor asymmetry、reverse pocket score、heading misalignment、goal-side visibility、local RS gradient；
3. 将 teacher 决策编译为一小套 `prototype + shallow rule`，在线只做便宜特征计算和查表，不再做任何深模型前向。

**如何继承 `CX8-D` 的成功语义**：
- `CX8-D Heavy` 的有效内容不是网络本身，而是“在某类瓶颈几何下，应优先进入某个 maneuver family”；
- `RS-CEC` 直接蒸馏这个 mapping：`bottleneck predicate -> preferred bundle tag -> fixed primitive bias`；
- 重型版的 bundle 语义被保留下来，但执行载体从黑箱模型变成了显式 rulebook。

**理论抓手**：
- 这是一个 **partial-policy compilation** 问题，而不是 full policy distillation；
- 只编译“高 counterfactual gain / 高 support”的 states，可把描述长度压到少量 prototype；
- 在线复杂度为 `O(F + D)`，其中 `F` 是廉价特征数、`D` 是树深或 prototype 检索常数，远低于 `O(|A| · C_phi)`。

**预期优势轴**：
1. 最直接打击 `CX8-D Heavy` 的 runtime 瓶颈；
2. 比 `CX9-A` 更有希望泛化，因为表示依赖解析几何谓词，而不是场景级 region atlas；
3. 可天然支持 `neutral-by-default` 与 support-aware abstain，降低 `parasol_misc` 式误干预。

**与已有工作的差异**：
- 最相关工作：
  - *Programmatic Reinforcement Learning without Oracles* — <https://openreview.net/forum?id=G8EkpJ7mgRT>
  - *POETREE* — <https://openreview.net/forum?id=0u6pqUvCYlN>
- 差异与创新点：
  1. 现有 program/tree extraction 多在拟合“整策略”；`RS-CEC` 只编译 accepted baseline 之上的 **稀疏语义增量**；
  2. 现有工作通常以 imitation fidelity 为核心；`RS-CEC` 以 **counterfactual search gain** 过滤训练样本，只保留真正改变 planner dynamics 的 teacher 决策；
  3. `RS-CEC` 不是把所有状态都交给 compiled model，而是只在支持域内激活，其余默认回退 `CX3-D`。

**如何打破 `CX8` 的 Pareto 冲突**：
- 把“昂贵但有效”的语义 teacher 只留在离线数据生成阶段；
- 在线执行体变成常数级规则，保留语义而丢掉推理成本。

**实现路径与主要风险**：
- 复用 `CX8-D Heavy` 已有输出，优先从 `maze / flange / deadend_labyrinth` 的正收益样本抽 counterfactual labels；
- 新增离线 compiler，把 teacher labels 聚成少量支持域 prototype；
- 风险在于 teacher 正项过于集中，导致 rulebook 只会记住窄 family 模式；需通过 support-aware abstain 和 prototype pruning 控制过拟合。

---

### CX10-B: `RS-HBC` — Horizon Bottleneck Compiler

**方案名称与类型**：
- `RS-HBC`；
- 类型：`model-based scene-level bottleneck script compiler`。

**核心想法**：
1. 不再学习整张 semantic atlas，而是在搜索开始前，用 accepted `CX3-D` field + `RS` 运动学做少量 horizon-limited probe；
2. probe 只回答三个问题：`哪里可能是 gate`、`进入 gate 前是否需要 setup`、`通过 gate 后应保持哪类 thread mode`；
3. 把结果编译为一个极短的 scene-specific script：`[(window_i, trigger_i, bundle_tag_i, exit_i)]`，在线只做窗口命中检测与静态 bias。

**如何继承 `CX8-D` 的成功语义**：
- `CX8-D` 的本质是：在 bottleneck 前切换 phase，在瓶颈中 commit 某个 maneuver family；
- `RS-HBC` 不再对每个 successor 仲裁，而是把这种 phase shift 编译成少量 `window-level` 事件；
- `reverse-setup -> thread-through -> recover` 仍然存在，只是被编码到脚本节点里。

**理论抓手**：
- 采用“只预测关键变量”的抽象模型视角；
- 额外代价为 `O(K · L · |B|)`，其中 `K` 是候选瓶颈窗口数、`L` 是短 horizon probe 长度、`|B|` 是少量 bundle family 数；
- 在线则仅为 `O(1)` 的窗口 membership check 和 tag lookup。

**预期优势轴**：
1. 比 `CX9-A` 的全图 region partition 更稳，因为只在瓶颈窗口上做工作；
2. 比 `RS-CEC` 更不依赖 teacher coverage，因为核心判断来自 `RS` 几何 probe 与局部验证；
3. 对 `maze` 和 `flange` 这类“少量关键门控主导整体搜索”的场景尤其有希望。

**与已有工作的差异**：
- 最相关工作：
  - *Learning Efficient Abstract Planning Models that Choose What to Predict* — <https://openreview.net/forum?id=ba27-RzQssu>
  - *Subgoal Diffuser* — <https://arxiv.org/abs/2402.05157>
- 差异与创新点：
  1. 现有抽象/子目标方法通常输出 waypoint 或 latent subgoal；`RS-HBC` 输出的是 **带 maneuver semantics 的 bottleneck script**；
  2. 现有 generative/subgoal 方法往往直接把 learned proposal 送给 planner；`RS-HBC` 引入 scene-level analytic probe 作为 verifier，学习对象只负责缩小候选空间；
  3. 相比 `CX9-A` 的 dense atlas，`RS-HBC` 只编译稀疏窗口，因此更符合 `CX8-D Heavy` 的真实信号形态。

**如何打破 `CX8` 的 Pareto 冲突**：
- 将高复杂度语义计算搬到搜索前的一次性短 horizon 编译阶段；
- 在线期只执行脚本，而不是重复“想一遍”。

**实现路径与主要风险**：
- 先用 skeleton minima、clearance saddle、forward-progress stall 等廉价 detector 生成候选窗口；
- 再对每个窗口做少量 local counterfactual probe，选出需要 `reverse-setup` 或 `thread` 的标签；
- 风险是漏掉真正关键窗口；需要允许脚本为空并回退 baseline，避免误编译造成大面积退化。

---

### CX10-C: `RS-NFA` — Neuro-Finite Automaton

**方案名称与类型**：
- `RS-NFA`；
- 类型：`compiled finite-state intervention controller`。

**核心想法**：
1. 将 `CX8-D Heavy` 的有效多步语义压缩成一个很小的自动机，候选状态例如：`neutral`、`prepare_reverse`、`commit_thread`、`recover`；
2. 自动机转移只依赖解析谓词，如 `is_bottleneck`、`has_reverse_pocket`、`entered_gate`、`heading_recovered`；
3. 每个状态绑定一组固定 primitive-family bias 模板，从而在多节点跨度上保持 phase consistency，而不必重复做重推理。

**如何继承 `CX8-D` 的成功语义**：
- `CX8-D Heavy` 真正难以被 `CX9-A` 保住的，是 **时序 persistence**：某次正确的 setup 决策应该持续影响随后若干节点；
- `RS-NFA` 直接把这种 persistence 显式建模为状态与转移；
- 因此它比静态 atlas 或单次 gate 更接近 `CX8-D` 的有效机制。

**理论抓手**：
- 有限状态压缩等价于对 planner-side intervention memory 做强信息瓶颈约束；
- 在线复杂度是 `O(1)` 的谓词评估 + 状态转移 + bias lookup；
- 自动机比 dense policy 更容易做 reachability audit 与 error localization。

**预期优势轴**：
1. 若 `CX8-D Heavy` 的优势主要来自“多步 setup/commit 的时序一致性”，则 `RS-NFA` 最可能在保持低成本的同时恢复该语义；
2. 通过明确的 phase 记忆，有望比 `CX9-A` 在 `maze`、`narrow_passage` 上更稳；
3. 比 `RS-LAS` 更保守，因为它仍然在 planner loop 内局部响应，而不是依赖整场景一次性预测。

**与已有工作的差异**：
- 最相关工作：
  - *Hierarchical Programmatic Reinforcement Learning* — <https://proceedings.mlr.press/v202/liu23at.html>
  - *Provably Correct Compositional Policies via Automata Embeddings* — <https://arxiv.org/abs/2410.03814>
- 差异与创新点：
  1. 这些工作多为任务级 policy / reward-machine 控制；`RS-NFA` 是 **planner-side semantic controller**，不替换底层 planner；
  2. 现有自动机工作通常把状态和任务规格绑定；`RS-NFA` 把状态绑定到 **nonholonomic bottleneck phase**；
  3. `RS-NFA` 的输出不是动作本身，而是 accepted `CX3-D` 上的 primitive bias delta，因此保持 anchor fallback 语义。

**如何打破 `CX8` 的 Pareto 冲突**：
- 通过显式状态记忆保留重型版的多步时序语义；
- 通过自动机模板把重计算替换成常数级状态转移。

**实现路径与主要风险**：
- 需要先从 `CX8-D Heavy` trace 中挖掘 phase 边界并定义 predicate vocabulary；
- 可先从 3-4 个固定状态起步，再做 trace distillation；
- 风险在于状态设计不当会导致自动机既不够表达、也不够稳定，因此需要强约束与 neutral fallback。

---

### CX10-D: `RS-LAS` — Learned Action Sketch

**方案名称与类型**：
- `RS-LAS`；
- 类型：`one-shot maneuver sketch / sparse macro-event generator`。

**核心想法**：
1. 在搜索开始前，由一个 scene-level predictor 只输出极短的 maneuver sketch，例如 2-5 个事件：`(gate token, macro tag, confidence)`；
2. 这些事件不是精细轨迹，而是“在某处先 reverse-setup，再以某种 thread family 通过”的宏观提示；
3. 在线搜索仍完全由 accepted `CX3-D` 驱动，只在靠近 sketch gate 时启用对应 macro bias；若验证失败则直接 abstain。

**如何继承 `CX8-D` 的成功语义**：
- `CX8-D Heavy` 的优势本质上来自少数关键的 phase-switch events；
- `RS-LAS` 尝试把这些事件一次性压缩成一段很短的程序；
- 成功的话，它是最接近“保留语义但只付一次成本”的路线。

**理论抓手**：
- 额外成本与 sketch 长度 `K` 成正比，而非与扩展节点数成正比；
- 这是 `option sketch` / `program sketch` 的 planner 版本：先给长期结构，再由 baseline search 负责局部完备性；
- 若 sketch token 使用相对几何描述而非绝对 region label，可提升跨场景泛化。

**预期优势轴**：
1. 有希望覆盖 `narrow_passage` 这类需要明确先后顺序的 case；
2. 若 sketch 预测稳定，可在极低在线成本下保留较强的多步语义；
3. 适合与 scene-level verifier 结合，形成“提案 + 校核 + fallback”的三段式体系。

**与已有工作的差异**：
- 最相关工作：
  - *Combined Task and Motion Planning via Sketch Decompositions* — <https://openreview.net/forum?id=ojc4aWQfP2>
  - *PIVOT-R* — <https://openreview.net/forum?id=YXik8d8ou0>
- 差异与创新点：
  1. 现有 sketch/waypoint 方法通常输出 task skeleton 或 waypoint list；`RS-LAS` 输出的是 **nonholonomic maneuver sketch**；
  2. 现有工作多直接让 sketch 主导规划；`RS-LAS` 则把 sketch 限制为对 accepted baseline 的局部 macro bias；
  3. `RS-LAS` 强制带 verifier 与 abstain 逻辑，避免 `CX9-A` 式的 test-time semantic drift。

**如何打破 `CX8` 的 Pareto 冲突**：
- 只在 scene 开始时付一次推理成本；
- 把高语义决策浓缩成极少数 macro events，而不是重复对海量 successors 做判断。

**实现路径与主要风险**：
- 需要新建 `teacher trace -> bottleneck event sequence` 的数据管道；
- sketch token 设计必须避免过拟合到绝对地图纹理；
- 这是四条路线里创新最高但训练风险也最高的一条，应放在后序验证。

## 6. Recommended Execution Order

推荐执行顺序：`CX10-A -> CX10-B -> CX10-C -> CX10-D`

### 6.1 为什么先做 `CX10-A / RS-CEC`

- 它最直接利用现有最强正信号来源：`CX8-D Heavy`；
- 几乎不需要改 planner 骨架，只需要离线 compiler + 在线 O(1) lookup；
- 若连 `teacher-distilled rulebook` 都不能保住任何 test-side signal，就说明“可编译的局部语义”本身可能不足以承载 `CX8-D` 的有效机制。

### 6.2 为什么第二做 `CX10-B / RS-HBC`

- 它最有可能修复 `CX9-A` 的泛化问题，因为核心验证依赖 scene-specific analytic probe，而不是纯 learned atlas；
- 若 `RS-CEC` 过拟合 teacher support，`RS-HBC` 是最自然的 analytic 对照组。

### 6.3 为什么第三做 `CX10-C / RS-NFA`

- 它解决的是 `CX9-A` 和简单 rulebook 都难以保留的 **phase persistence**；
- 但需要 temporal trace mining 和状态设计，因此实现复杂度高于 `A/B`。

### 6.4 为什么最后做 `CX10-D / RS-LAS`

- 它的上限可能最高，但 data pipeline、tokenization、verifier 设计都最重；
- 更适合作为 `A/B/C` 失败后的高创新后手，而不是当前第一优先级。

## 7. Minimum Acceptance Bar and Failure Criteria

### 7.1 Stage-1 Dev Gate

所有 `CX10-*` 候选在 `data/split/calib_hard_v1` 的 dev-only pilot 上，至少需要同时满足：

1. `exp_delta > 0`；
2. `success_delta_pp >= 0`；
3. `mean_time_overhead_ratio < 0.30`；
4. `parasol_misc` 不出现明显负向回归，或有清晰 `neutral-abstain` 解释；
5. 不出现 path audit 恶化；
6. 不依赖任何 per-successor 深模型推理。

### 7.2 Stage-2 Locked Final Gate

若 dev 通过，进入 `rs_root_hard_v2/test` 的 locked final eval 时，必须：

1. 锁定 dev 选出的结构和参数，不再调参；
2. 相对 accepted `CX3-D` 维持 `exp_delta > 0`；
3. `mean_time_overhead_ratio < 0.30`；
4. `mp/csm` ordinary support 不发生原则性退化；
5. family-wise gain 不能只来自单一 case patch。

### 7.3 直接失败判据

以下任一满足，则直接判定该 `CX10-*` 路线失败：

1. 重新引入 per-successor 深模型/重仲裁；
2. 新结构本质上只是另一种 dense field / coarse atlas，未形成可执行程序结构；
3. 无法提供 `neutral-by-default` 与 support-aware abstain；
4. gain 只存在于个别 `maze` case，而整体 trend 不稳；
5. 为实现候选而需要重写 planner 主干，脱离当前 `rs_cx` / planner hook 架构。

## 8. Final Recommendation

基于当前证据，`CX10` 的主命题应冻结为：

> **Compile semantics, not scores.**

更具体地：

- `CX8-D Heavy` 已经说明“瓶颈语义”确实存在；
- `CX9-A` 已经说明“只把语义做成粗图谱”不足以稳健泛化；
- 因而 `CX10` 最值得做的，不是继续学一个更大的预测器，而是把 teacher 语义转成：
  - **可检索的 rulebook**；
  - **可验证的 bottleneck script**；
  - **可执行的有限状态控制器**；
  - **可稀疏触发的 macro sketch**。

推荐冻结的主执行顺序是：

1. `CX10-A / RS-CEC`
2. `CX10-B / RS-HBC`
3. `CX10-C / RS-NFA`
4. `CX10-D / RS-LAS`

其中：

- `RS-CEC` 是最现实的 first shot；
- `RS-HBC` 是最可能修复泛化问题的 analytic companion；
- `RS-NFA` 是最有机会保住 `CX8-D` 时序语义的结构化升级；
- `RS-LAS` 是高风险高上限的最后储备路线。

## 9. Reference Links

1. *Programmatic Reinforcement Learning without Oracles* — ICLR 2022 — <https://openreview.net/forum?id=G8EkpJ7mgRT>
2. *Hierarchical Programmatic Reinforcement Learning* — ICML 2023 — <https://proceedings.mlr.press/v202/liu23at.html>
3. *POETREE: Policy Extraction from Deep Reinforcement Learning for Interpretable Decision-Making with Adaptive Expertise Distillation* — ICLR 2022 — <https://openreview.net/forum?id=0u6pqUvCYlN>
4. *VisualPredicator: Learning Abstract World Models with Neuro-Symbolic Predicates for Robot Planning* — ICLR 2025 — <https://openreview.net/forum?id=mqIQE8BftT>
5. *Provably Correct Compositional Policies via Automata Embeddings* — primary source — <https://arxiv.org/abs/2410.03814>
6. *Planning with a Learned Policy Basis to Optimally Solve Complex Tasks* — primary source — <https://openreview.net/forum?id=Ht90v3Wqvb>
7. *Query-Efficient Planning in Deterministic MDPs under Linear Realizability and Optimal Partial Feedback* — COLT 2021 — <https://proceedings.mlr.press/v134/chen21a.html>
8. *Learned Critical Probabilistic Roadmaps for Robotic Motion Planning* — primary source — <https://arxiv.org/abs/1910.14634>
9. *Long Range Navigator: Yet Another Way to Inject Language Models in Robotics* — CoRL 2025 — <https://openreview.net/forum?id=JwrnoB1tR0>
10. *PIVOT-R: Primitive-Driven Waypoint-Oriented Task and Motion Planning for Runtime-Aligned Long-Horizon Robotic Manipulation* — primary source — <https://openreview.net/forum?id=YXik8d8ou0>
11. *Learning over Subgoals for Efficient Navigation of Structured, Unknown Environments* — CoRL 2018 — <https://proceedings.mlr.press/v87/huang18a.html>
12. *Learning Efficient Abstract Planning Models that Choose What to Predict* — CoRL 2022 — <https://openreview.net/forum?id=ba27-RzQssu>
13. *Overcoming the Pitfalls of Prediction Error in Model-Based Planning* — primary source — <https://arxiv.org/abs/2403.17991>
14. *Subgoal Diffuser: Offline Goal-Conditioned Trajectory Diffusion for Subgoal Generation in Robot Manipulation* — ICRA 2024 — <https://arxiv.org/abs/2402.05157>
15. *Hybrid Search for Efficient Planning with Completeness Guarantees* — primary source — <https://arxiv.org/abs/2310.12819>
16. *Combined Task and Motion Planning via Sketch Decompositions* — primary source — <https://openreview.net/forum?id=ojc4aWQfP2>
