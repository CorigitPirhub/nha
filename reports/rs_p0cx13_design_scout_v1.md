# P0-CX13 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-11`

## 1. Executive Summary

`CX8-D Heavy -> CX10/11/12 repair` 这条路线族已经给出非常稳定的结论：

- **强语义 ceiling 存在**：`CX8-D Heavy` 在 hard test 上仍有 `exp_delta = +58.575`，说明“正确干预”不是幻觉；
- **但 ceiling 不可部署**：同一结果伴随 `mean_time_overhead_ratio ≈ 1.2856`，超出任何可接受上线成本；
- **低成本修复族被跑穿**：`CX10` 主要是误触发，`CX11` 主要是 over-defer，`CX12` 则进一步证明“trap-aware 也只能消害、不能保益”；
- 因而当前 Pareto 死锁不是某个实现 bug，而是这一路线族的**结构性极限**。

这意味着 `CX13` 不应再继续回答：

> “如何更聪明地决定要不要给 sketch / token / semantic repair？”

而应转向新的核心问题：

> **如何把搜索计算本身作为一等对象进行分配、约束和调度，从而在不做昂贵语义推理的前提下，把预算集中到真正值得探索的区域？**

因此，`CX13` 的方向必须：

1. **完全跳出 sketch/defer/repair family**；
2. **保持 RS-grounded**：建立在 accepted `RS + refined CX3-D / RS-HPG` 上；
3. **在线可部署**：在线只能是 `O(1)` 或 `O(K)`，且 `K` 不与 successor 数量线性耦合；
4. **创新对象改成“计算分配 / 结构约束 / episode-level schedule”**，而不是再发明新的 token 判别器。

## 2. Structural Diagnosis: Why the Old Family Is Exhausted

### 2.1 当前失败不是“不会识别语义”，而是“语义对象选错了”

`CX10-D` 与 `CX11/CX12` 的共同问题已经很清楚：

- 它们试图在 **token / gate / local geometry** 层判断“此处该不该激活特殊策略”；
- 但 `flange` 与 `narrow_passage` 在当前可用特征空间中高度重叠；
- 结果就是：
  - 若 gate 宽松：`flange` 会灾难性误触发；
  - 若 gate 严格：`narrow_passage` 的 sparse positive signal 也一起被抹掉。

换句话说，当前 family 的主要对象——`semantic token validity`——已经被证明是一个：

- **高价值**，但
- **高脆弱**，
- 且 **高辨识难度**

的对象。

### 2.2 `CX13` 需要把对象从“语义判别”换成“计算分配”

若继续在 token 层做对错判别，新的候选大概率还会重复：

- `误触发太多`；
- `over-defer`；
- `消害不保益`。

因此，`CX13` 更合理的切入点是：

1. **预算分配**：决定哪些 basin / corridor / phase 值得消耗计算；
2. **结构约束**：限制搜索把预算花在 trap-like region；
3. **episode-level schedule**：不是选 token，而是选“这一类实例的搜索节奏和资源配置”。

这是和 `CX8-D semantic intervention -> repair family` 的**根本对象切换**。

## 3. Literature Sweep

下面只保留与 `CX13` 新问题最相关的 primary-source 文献，并按主题整理。

### 3.1 Learned Search Guidance / Heuristic Learning

1. **Learning Heuristic Search via Imitation** — CoRL 2018 / PMLR  
   Link: <https://proceedings.mlr.press/v87/chitnis18a.html>

2. **Learning Efficient Abstract Planning Models that Choose What to Predict** — CoRL 2022 / OpenReview  
   Link: <https://openreview.net/forum?id=ba27-RzQssu>

3. **Policy-Guided Heuristic Search with Guarantees** — arXiv  
   Link: <https://arxiv.org/abs/2103.11505>

4. **CAMPs: Cost-Aware Meta Planning with Search** — ICML 2024 / OpenReview  
   Link: <https://openreview.net/forum?id=Uuk7eHcngv>

**提炼**：
- 这些工作证明：学习模块可以为 search 提供有效 guidance；
- 但主流对象依然是：
  - `heuristic value`
  - `search policy`
  - `abstract planner prior`
- 它们很少把 **computation budget allocation itself** 作为主对象。

**对当前项目的局限**：
- 我们的问题不再是“分数不准”，而是“预算被花错地方”；
- 因而继续堆叠 heuristic/policy predictor，大概率仍会落回 `CX8-CX12` 的老问题。

### 3.2 Meta-Learning / Algorithm Configuration / Instance Adaptation

1. **CAMPs: Cost-Aware Meta Planning with Search** — ICML 2024 / OpenReview  
   Link: <https://openreview.net/forum?id=Uuk7eHcngv>

2. **Planning with a Learned Policy Basis to Optimally Solve Complex Tasks** — OpenReview  
   Link: <https://openreview.net/forum?id=Ht90v3Wqvb>

3. **Query-Efficient Planning in Deterministic MDPs under Linear Realizability and Optimal Partial Feedback** — COLT 2021 / PMLR  
   Link: <https://proceedings.mlr.press/v134/chen21a.html>

**提炼**：
- per-instance planning behavior 可以通过：
  - schedule 选择
  - cost-aware meta planning
  - query-efficient resource use
  来显著改变；
- 这类工作与 `CX13` 最接近，因为它们开始把“算力/查询/计划资源”本身作为对象。

**对当前项目的局限**：
- 现有方法往往：
  - 选择完整 planner / high-level policy；
  - 或依赖更重的 planning-time meta inference；
- 对我们来说，需要的是 **仍然停留在 accepted RS + CX3-D 主线之内** 的 lightweight schedule / budget object，而不是外接新的 planner portfolio。

### 3.3 Topological / Structural Guidance

1. **Combined Task and Motion Planning via Sketch Decompositions** — OpenReview  
   Link: <https://openreview.net/forum?id=ojc4aWQfP2>

2. **RT-Trajectory: Robotic Task and Motion Planning via Hierarchical Sketches** — arXiv 2025  
   Link: <https://arxiv.org/abs/2503.22195>

3. **VisualPredicator: Learning Abstract World Models with Neuro-Symbolic Predicates for Robot Planning** — ICLR 2025 / OpenReview  
   Link: <https://openreview.net/forum?id=mqIQE8BftT>

**提炼**：
- 结构化 planning object（如 sketch、predicate、topological abstraction）确实是有效方向；
- 但 `CX10-CX12` 已经说明：一旦结构对象落回 token/gate 判别，就会重新遇到 distinguishability crisis。

**对当前项目的局限**：
- 这些工作帮助我们确认“高层对象值得做”；
- 但对 `CX13` 来说，**高层对象不应再是 sketch token，而应是 budget contract / basin allocation / schedule phase**。

### 3.4 Risk Control / Selective Abstention / Deferral

1. **SLTD: Learning to Defer for Sequential Decision-Making under Uncertainty** — arXiv 2024  
   Link: <https://arxiv.org/abs/2402.01830>

2. **Beyond Confidence: Trustworthy Learning-to-Defer via Conformal Prediction Sets** — arXiv 2023  
   Link: <https://arxiv.org/abs/2307.04993>

3. **Selective Omniprediction and Fair Abstention** — OpenReview  
   Link: <https://openreview.net/forum?id=BoYGLpNXZd>

**提炼**：
- 这些工作非常适合解释 `CX11` 的失败：defer can remove harm, but defer alone does not create gain；
- 它们强调：
  - calibrated abstention
  - support-aware deferral
  - uncertainty-aware fallback

**对当前项目的局限**：
- 对当前项目来说，`CX11` 已经把“defer 作为主对象”跑到尽头；
- 再继续这条路，只会更稳定地得到 baseline tie，而不是更强优势区间。

## 4. Structural Limit Analysis of Existing Work

结合上面文献和本项目证据，可以把现有工作的结构性局限总结成三条：

### 4.1 现有 learned heuristic / planning prior 工作仍把“估值”当核心对象

这类方法通常问：

- 哪个 state 更 promising？
- 哪个 subgoal 更好？
- 哪个 policy prior 更接近成功？

但我们现在的核心痛点是：

> **搜索预算被错误地分配到 trap-like region，而不是单个 state 的 heuristic 分数不准。**

因此，继续强化估值对象，并不能自然解决当前死锁。

### 4.2 现有 topology/sketch 工作解决了“表达能力”，没有解决“可部署 budget control”

它们能表达：

- long-horizon structure；
- topological choice；
- subgoal scaffold；

但没有直接回答：

- 在 fixed compute budget 下，如何避免某类 trap 吃掉全部 expansions？
- 如何用 `O(1)` / `O(K)` 成本去约束搜索资源流向？

### 4.3 现有 defer/risk-control 工作解决了“少犯错”，没有解决“如何多赚收益”

`CX11` 已经把这点验证得很充分：

- risk-aware / defer-aware 系统很擅长把 catastrophic negative case 压到 `0`；
- 但如果正向 signal 本身稀疏且脆弱，它们也会顺手把 gain 一起抹平。

所以 `CX13` 不能再把 “少犯错” 当主命题，而必须寻找：

> **既不误花预算，又能把预算集中到真正值得探索的地方。**

## 5. Proposed CX13 Candidate Families

### CX13-A: `RS-BBC` — Basin Budget Controller

**核心想法**：
1. 先基于 accepted `RS + CX3-D` field、occupancy 和 skeleton/clearance saddle，把 free space 分成少量 basin：
   - corridor basin
   - trap pocket basin
   - open transition basin
2. 为每个 basin 分配一份 episode-level exploration budget；
3. 搜索过程中，node 只需查自己所在 basin 的 remaining budget：
   - 若 basin 被判为 trap-like，且预算已耗尽，则提高 priority penalty 或限制 reverse-heavy expansion；
   - 若 basin 属于 high-value corridor，则保留更多搜索预算。

**干预对象**：
- 不是 successor；
- 不是 sketch token；
- 而是 **basin-level exploration budget**。

**何时干预**：
- 主要在搜索前完成 basin 划分和 budget 初始化；
- 在线只做 `node -> basin id` 查表与常数级 budget ledger 更新。

**理论抓手**：
- resource-rational / metareasoning 视角；
- topological basin decomposition；
- computation allocation rather than value prediction。

**可部署性**：
- 预处理：一次性 basin extraction；
- 在线：`O(1)` basin lookup + counter update；
- 不依赖 per-successor 模型前向。

**创新性**：
- 现有方法很少把 **trap basin 预算** 作为主对象；
- 它不是 planner portfolio，也不是 topological waypoint，而是 **search budget contract over structural regions**。

**为什么有希望打破 Pareto 死锁**：
- 当前死锁来自“少数 catastrophic region 吞掉大量预算”；
- 若能直接在 basin 级做预算约束，就可能：
  - 去掉 `flange` catastrophic expansion waste；
  - 同时不需要去判断 fragile token validity。

**风险**：
- basin 划分若过粗，会再次退化成 tie；
- basin 划分若过细，预处理和调试会变复杂。

---

### CX13-B: `RS-IAS` — Instance-Adaptive Search Schedule

**核心想法**：
1. 不再学习具体语义 token；
2. 而是为每个 instance 选择一套 **搜索日程表**，例如：
   - heuristic inflation schedule
   - reverse quota schedule
   - restart threshold
   - anchor-vs-guided priority mixing schedule
3. schedule 从一个小型离散 catalog 中选出，或者在 2-3 个 phase 之间切换。

**干预对象**：
- **episode-level search schedule**，不是局部 token。

**何时干预**：
- 主要在搜索开始前一次性选择；
- 或在极少数固定 phase 点切换。

**理论抓手**：
- per-instance algorithm configuration；
- meta-planning / cost-aware schedule selection；
- budgeted anytime search。

**可部署性**：
- 在线只需：
  - `O(1)` catalog lookup；
  - `O(1)` phase switch；
- 不与 successor 数量线性耦合。

**创新性**：
- 不做 planner router，不更换主方法；
- 而是在 accepted `RS + CX3-D` 内部只学习 **搜索节奏和资源分配**。

**为什么有希望打破 Pareto 死锁**：
- 当前 negative evidence 可能说明：问题不在“语义 token 错了”，而在“固定 schedule 对 hard instance 不匹配”；
- 若真正差别体现在 reverse/restart/budget节奏，schedule object 会比 token object 更稳定。

**风险**：
- 若 catalog 太小，可能表达力不足；
- 若 catalog 太大，又可能滑向软 router/portfolio。

---

### CX13-C: `RS-TCB` — Topological Contract Budgeting

**核心想法**：
1. 从 accepted field 与 skeleton 中提取少量 topological corridor tickets；
2. 每个 ticket 都有一个 **contract**：
   - reserve budget
   - admissible reverse quota
   - exit requirement
   - overrun penalty
3. 搜索过程中，每个 node 只需绑定到某个 ticket，并根据该 ticket 的 contract 调整 priority penalty / queue slack / budget spend。

**干预对象**：
- 不是 waypoint；
- 不是 sketch；
- 而是 **corridor-level search contract**。

**何时干预**：
- ticket construction 在搜索前；
- contract 执行在搜索中以常数级 ledger 方式发生。

**理论抓手**：
- topological abstraction + budget contract；
- global corridor commitment without local semantic tokenization。

**可部署性**：
- 在线仅为 ticket membership lookup + contract counter update；
- 复杂度近似 `O(1)`。

**创新性**：
- 相比传统 topology guidance，它不要求 planner 按某条 path/sketch走；
- 相比 router/portfolio，它不切换 planner；
- 它直接控制 **哪个 topological option worth spending budget on**。

**为什么有希望打破 Pareto 死锁**：
- 如果 catastrophic failure 的本质是“搜索把太多 expansions 花在错误 corridor/side pocket 上”，那 contract 比 token 更直接；
- 同时又不需要 `CX10-CX12` 那种 fragile local semantic discrimination。

**风险**：
- ticket extraction 若不稳，可能把正确 corridor 也过度压制；
- 需要 careful design 以避免再次变成纯 abstain。

## 6. Recommended Order

推荐顺序：`CX13-A -> CX13-B -> CX13-C`

### 为什么先做 `CX13-A / RS-BBC`

- 最直接对应当前 failure analysis：catastrophic budget waste 发生在 trap-like basin；
- 改动对象明确，在线也最便宜；
- 最有希望在不依赖 fragile token semantics 的前提下，直接减少 `flange` 式浪费。

### 为什么第二做 `CX13-B / RS-IAS`

- 如果 basin budget 还不够，下一步最值得测试的是“节奏错了还是对象错了”；
- per-instance schedule selection 是比 token 更 coarse、但也更稳定的对象。

### 为什么第三做 `CX13-C / RS-TCB`

- 它最有 paper-facing novelty；
- 但 contract/ticket 设计复杂度最高，适合作为在 `A/B` 之后的更大动作方案。

## 7. Minimum Acceptance Bar

任一 `CX13` 候选若要进入下一阶段严格验证，至少需要：

1. public `exp4` 上：
   - `exp_delta > 0`
   - `mean_time_overhead_ratio < 0.30`
   - `flange exp_delta >= 0`
2. `mp/csm` 上 ordinary-support 不退化；
3. 在线逻辑必须是 `O(1)` 或 `O(K)`，且 `K` 不与 successor 数量线性耦合；
4. 不重新落回 sketch/defer/repair family。

## 8. Final Recommendation

`CX13` 的主命题应冻结为：

> **Allocate search computation, don’t classify semantic tokens.**

更具体地：

- `CX8-D Heavy` 说明“正确方向”确实存在；
- `CX10-CX12` 说明在当前协议下，token/gate-level semantic repair 无法同时做到：
  - strong gain
  - low cost
  - low false positive
- 因而下一轮最值得押注的，不是更强 token，也不是更强 defer，而是：
  - **basin-level budget control**
  - **instance-level search schedule**
  - **topological contract budgeting**

当前首选执行入口：`CX13-A / RS-BBC`。
