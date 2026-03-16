# P0-CX21 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-14`

## 1. Executive Summary

`CX20` 已经把一个关键事实说清楚了：

1. `RS-core` 结构化升级不是错方向；
2. 它甚至是 `CX17-C` 之后唯一再次打出明显 public positive ceiling 的路线；
3. 但当前实现方式仍然过激，导致 hard-test 上出现一致的 `success_delta_pp` 下滑。

因此，`CX21` 的问题不应再写成 “要不要继续做 RS-core”，而应写成：

> **如何把 `CX20` 的高-ceiling RS-core 方向，从“更强但不稳”的对象，收敛成“一致 value foundation + 合法性 grammar + 稳定 compiled substrate”。**

本轮文献调研的结论是：

- 用户提出的那类 **HJ / HJB value-function field** 直觉是对的：`RS` 的上限确实不应只是单一 cost 图；
- 但文献同样清楚表明：高维精确 PDE 求解不可部署，真正可行的是 **learned value/reachability surrogate + consistency constraints**；
- 对 `macro` 来说，真正值得学的是 **legality / precondition / must-precede relation**，而不是扁平 bias 分数；
- 对 `substrate` 来说，真正有希望泛化的是 **高支持度、稀疏、可验证的 reusable graph**，而不是更大的 prior graph。

因此本轮冻结三条 `CX21` 候选：

1. `CX21-A / RS-CVF`：`RS Consistent Value Foundation`
2. `CX21-B / RS-LAG`：`RS Legality-Aware Grammar`
3. `CX21-C / RS-SCG`：`RS Stable Compiled Graph`

推荐顺序保持：

`CX21-A -> CX21-B -> CX21-C`

因为 `CX21-B/C` 都必须建立在更稳的一致基础场之上。

## 2. What `CX20` Actually Established

`CX20-A/B/C` 的结果不是“RS-core 失败”，而是更细的三条结论：

1. **对象选对了**：
   - `CX20-A` public `exp4 exp_delta = +52.000`
   - `CX20-B` public `exp4 exp_delta = +45.111`
   - `CX20-C` public `exp4 exp_delta = +45.111`
2. **当前实现方式不稳**：
   - 三条路线 hard-test 都出现 `success_delta_pp = -1.370`
   - 关键 hard families 出现系统性负项
3. **失败模式高度同构**：
   - 不是单一实现 bug；
   - 而是当前 `RS-core` 升级在三个层面都太激进：
     - 多头对象彼此不一致；
     - macro grammar 过早变成硬约束；
     - compiled graph 缺少边级可执行性保护。

因此 `CX21` 的核心不是“再加新模块”，而是把 `CX20` 的三类对象做稳。

## 3. Literature Sweep

### 3.1 Value Functions, Reachability, and Structured Fields

1. **DeepReach: A Deep Learning Approach to High-Dimensional Reachability**  
   Link: <https://arxiv.org/abs/2006.15611>
2. **ExactBC: Fast Convergence of Deep Neural Networks in Predicting Hamilton-Jacobi Reachability**  
   Link: <https://arxiv.org/abs/2501.07656>
3. **Progressive Neural Networks for Operator Learning in Motion Planning**  
   Link: <https://arxiv.org/abs/2409.07863>
4. **Reachability-Based Trajectory Design Using Neural Implicit Safety Constraints**  
   Link: <https://arxiv.org/abs/2410.19564>

**这些工作共同确认的点**

1. 类似 `HJ / HJB` 的值函数对象，确实是规划中的强结构对象；
2. 但高维精确网格求解会迅速爆炸，必须用近似、operator learning 或 implicit representation 做摊销；
3. 一旦引入 safety / reachability / viability，对象之间的一致性与边界条件会直接决定稳定性；
4. “cost-to-go / safety / recoverability” 若彼此矛盾，就会得到看起来强、但闭环不稳的行为。

**映射到当前项目**

`CX20-A` 的方向被文献确认了，但它缺少两样关键东西：

1. **结构一致性**：各头不是独立分数，而应服从受控关系；
2. **边界 / 可恢复性约束**：goal、obstacle、reverse-required、trap-affinity 之间需要显式逻辑。

这直接推导出 `CX21-A / RS-CVF`。

### 3.2 Motion Primitives, Macro Languages, and Skill Legality

1. **Motion Planning using Safe-by-Design Motion Primitives for Autonomous Driving**  
   Link: <https://arxiv.org/abs/2401.10743>
2. **Bridging the Gap between Learning and Planning in Complex Action Spaces**  
   Link: <https://arxiv.org/abs/2205.15145>
3. **Logic-Skill Programming: An Infrastructure for Neuro-Symbolic Planning with Logic and Skills**  
   Link: <https://arxiv.org/abs/2402.14955>

**这些工作共同确认的点**

1. action-space leverage 往往来自 **结构化 primitive / skill language**，而不是逐动作打分；
2. primitive 若缺少 precondition / legality / effect typing，在线使用时会非常脆弱；
3. 真正可组合的 action language，通常都需要：
   - legality
   - typed transition
   - must-precede / must-follow relation
4. 纯粹的 flat bias 容易在 out-of-distribution geometry 上误导搜索。

**映射到当前项目**

`CX20-B` 证明 “让 RS 直接接 macro” 是对的，但做法仍太平：

- 它更像 flat allow/ban；
- 缺少 legality margin；
- 缺少 `reverse-setup -> forward-family` 这种显式前置关系；
- 缺少高不确定性时的 abstain/fallback。

这直接推导出 `CX21-B / RS-LAG`。

### 3.3 Reusable Substrates, Compiled Graphs, and Stable Query Structures

1. **Experience Graphs: Leveraging Experience for Planning with Sparse Roadmap Spanners**  
   Link: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
2. **Thunder Framework: Experience-Based Motion Planning in Changing, Partially-Known Environments**  
   Link: <https://arxiv.org/abs/1508.01296>
3. **GCS*: Forward Heuristic Search on the Shortest Path Problem in Graphs of Convex Sets**  
   Link: <https://arxiv.org/abs/2401.05194>
4. **Multi-Query Shortest Paths in Graphs of Convex Sets**  
   Link: <https://arxiv.org/abs/2501.02031>

**这些工作共同确认的点**

1. reusable structure 的价值是真实的，尤其在重复出现的局部几何中；
2. 但稳定泛化并不来自“把更多轨迹/graph 塞进去”，而来自：
   - 稀疏抽象
   - lower bound / support
   - 局部可执行修复
3. 离线 compiled structure 最好是 queryable substrate，而不是不可控的大 prior；
4. 在线真正执行前，通常仍需要 bounded local solve / repair 来兜底。

**映射到当前项目**

`CX20-C` 的问题不是 “compiled substrate 不值得做”，而是：

- graph 太激进；
- 节点/边定义过宽；
- 采用边之前缺少 local executable verification。

这直接推导出 `CX21-C / RS-SCG`。

## 4. What the Literature Changes About the Earlier RS-Core Draft

文献没有推翻上一轮的 `RS-core` 草案，但明确要求做三处收缩：

### 4.1 不是 “multi-head” 就够了，而必须是 `consistent multi-head`

`CX20-A` 的 hard-test failure 很像 reachability 文献里典型的问题：

- cost 说“值得前进”；
- 但 recoverability / reverse requirement 并没有同步成立；
- 结果就是把 planner 引到局部不可恢复区。

所以 `CX21-A` 不能再是 “四个头一起训”，而必须是：

1. 头与头之间有受控关系；
2. boundary conditions 明确；
3. uncertainty / abstention 有明确出口。

### 4.2 不是 “macro grammar” 就够了，而必须是 `legality-aware grammar`

`CX20-B` 说明 grammar 对象本身是有 leverage 的；
但文献表明，如果 grammar 没有 legality / precondition typing，它最终仍然只是更硬的 bias。

所以 `CX21-B` 必须从 flat family score 收缩为：

1. `allowed`
2. `discouraged`
3. `forbidden`
4. `must-precede`

且 hard forbid 只能在 support 足够高时使用。

### 4.3 不是 “compiled graph” 就够了，而必须是 `stable compiled graph`

`CX20-C` 的主要问题是把 prior graph 变大了，但没有让 graph 变稳。

文献给出的更合理做法是：

1. 节点稀疏；
2. 边带 support 与 lower bound；
3. 在线只查询局部子图；
4. 采用边之前做 bounded local refinement。

因此 `CX21-C` 的关键词不是 “更复杂”，而是：

> **high-support + sparse + locally executable**

## 5. Frozen `CX21` Candidates

### CX21-A: `RS-CVF` — RS Consistent Value Foundation

**核心想法**

1. `RS` 输出多头基础场：
   - `cost-to-go`
   - `viability / recoverability`
   - `reverse-required`
   - `trap / escape affinity`
2. 但这些头不是平行输出，而是通过一致性约束绑在一起。

**与 `CX20-A` 的根本差异**

`CX20-A` 只是把对象变多；  
`CX21-A` 要把对象之间的逻辑关系也变成训练目标的一部分。

**建议加入的约束**

1. goal / obstacle boundary consistency；
2. `reverse-required` 只有在前向推进困难、但局部仍可恢复时才允许升高；
3. `trap-affinity` 与 `viability` 保持受控反相关；
4. 对低支持区域输出 uncertainty / abstention，而不是硬结论。

**在线成本**

- 单次 `RS` 前向；
- 仍可视为 `O(1)` field query。

**为什么它最值得先做**

因为 `CX21-B/C` 都依赖一个更可信的 `RS` 基础表示；  
如果底座仍然自相矛盾，后面的 grammar / graph 只会放大错误。

**关键风险**

1. 约束过强会把信号压回 scalar tie；
2. 监督构造若不稳，会学到形式一致、实际无用的表示。

### CX21-B: `RS-LAG` — RS Legality-Aware Grammar

**核心想法**

让 `RS` 输出局部动作语法，而不是宏动作分数：

1. `allowed`
2. `discouraged`
3. `forbidden`
4. `must-precede(reverse-setup -> forward family)`

**与 `CX20-B` 的根本差异**

`CX20-B` 更接近 flat macro routing；  
`CX21-B` 则把 macro family 变成带合法性语义的局部动作语言。

**为什么文献支持这条线**

1. motion primitives 文献说明 primitive 的效力高度依赖 precondition / legality；
2. neuro-symbolic skill work 说明 typed skill interface 更容易泛化；
3. complex action-space planning 说明 action structure 比逐动作打分更重要。

**在线成本**

- 固定小规模 grammar decode；
- `O(K_macro)`，且 `K_macro` 与 successor 数量无关。

**为什么有希望修复 `CX20-B` 的 hard failure**

因为它不再要求每次都做 hard allow / ban；  
只有在 legality margin 高时才做硬限制，其余情形仍可回退 accepted baseline。

**关键风险**

1. grammar 太软会变成 tie；
2. grammar calibration 不足时，仍可能在 hard family 上误杀可行解。

### CX21-C: `RS-SCG` — RS Stable Compiled Graph

**核心想法**

由 `RS` 离线编译一个稀疏可查询的局部 substrate，节点只保留：

1. `viability basin`
2. `failure class`
3. `escape class`
4. `recovered basin`

边只保留：

1. `macro transition template`
2. `motif prior`
3. `support / lower bound`
4. `local executable refinement contract`

**与 `CX20-C` 的根本差异**

`CX20-C` 更像把 prior graph 做大；  
`CX21-C` 则要求 graph 必须先变稀疏、可信、可执行。

**为什么文献支持这条线**

1. Experience Graphs / Thunder 证明 reusable substrate 是成立的；
2. `GCS*` / multi-query GCS 说明离线编译 + 在线局部求解是更稳的接口；
3. 文献共同倾向于：graph 必须能提供 lower bound / executable local solve，而不只是 hint。

**在线成本**

- 查询局部子图；
- 对候选边做 bounded local refinement；
- 比 `CX21-A/B` 更重，但仍是查询型，而不是 per-successor dense semantics。

**为什么它仍值得保留**

它是唯一有机会把 `CX17-C` / `CX20-C` 的 public ceiling 真正推向 hard-test 的系统对象；  
但必须在 `CX21-A/B` 站住后再做。

**关键风险**

1. 节点/边抽象一旦错，reuse 会系统性放大错误；
2. 工程量最大，验证周期也最长。

## 6. Recommended Execution Order

### Rank 1: `CX21-A / RS-CVF`

原因：

1. 它直接修正 `CX20-A` 的主要失败机理；
2. 它对后续 grammar / graph 都是前置底座；
3. 它与用户提到的 `HJ / HJB value-function field` 直觉最直接对齐。

### Rank 2: `CX21-B / RS-LAG`

原因：

1. 它承接 `CX16-A/B` 与 `CX20-B` 已出现的 macro signal；
2. 但把对象从 flat score 收敛到 legality language；
3. 更有机会减少 hard-test 上的 success 损失。

### Rank 3: `CX21-C / RS-SCG`

原因：

1. 潜在 ceiling 最高；
2. 但依赖 `CX21-A/B` 提供更稳的 value / legality object；
3. 若提前做，极可能重演 `CX20-C` 的放大错误。

## 7. Immediate Design Constraints for the Next Implementation Round

1. 严禁回到 `sketch / defer / repair`；
2. 严禁把 `RS-core` 重新做成“更强 scalar cost + 更硬 bias”；
3. `CX21-A` 必须包含 `No-Consistency` 消融；
4. `CX21-B` 必须包含：
   - `No-Legality`
   - `Soft-Only`
   - `No-Must-Precede`
   三类消融；
5. `CX21-C` 必须包含：
   - `No-Support-Filter`
   - `No-Local-Refinement`
   - `No-Lower-Bound`
   三类消融；
6. `mp/csm` 仍只允许 ordinary-support audit；
7. hard-test 仍只在 public gate 明确通过后消费。

## 8. Final Judgment

本轮调研后的结论不是 “RS-core 还能不能做”，而是：

1. **能做，而且仍是当前最有希望打出根本性突破的路线之一**；
2. 但必须承认 `CX20` 已经证明：
   - 只把 `RS` 变强不够；
   - 关键在于把它变得 **一致、合法、稳定**；
3. 因而下一轮最合理的任务书，不是继续扩展 `CX20-A/B/C`，而是冻结为：
   - `CX21-A / RS-CVF`
   - `CX21-B / RS-LAG`
   - `CX21-C / RS-SCG`

这三条线都保留了 `CX20` 已经验证出来的高 ceiling 对象，但把实现方式收紧到了更符合文献与当前失败证据的形态。
