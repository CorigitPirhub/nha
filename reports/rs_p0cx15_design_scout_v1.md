# P0-CX15 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-12`

## 1. Executive Summary

`CX1-CX14` 的主结论已经足够清楚：

1. `RS + refined CX3-D / RS-HPG` 仍是当前唯一稳定、可部署的 accepted 主线；
2. 强语义 ceiling 真实存在，但 `CX8-D Heavy` 证明其 successor-level 执行代价不可部署；
3. `CX10-CX12` 说明 sketch / defer / repair 家族会稳定掉进 `误触发 vs 过度抑制` 的二元陷阱；
4. `CX13` 说明只改 static allocation / schedule / contract，不会自动产生 leverage；
5. `CX14` 首次表明 **episode-local memory** 是对的对象，但 runtime sprint 进一步说明：如果只压缩维护成本、不引入新的“可恢复性证据”，正向信号会被一起压平。

因此 `CX15` 的问题必须重写为：

> **如何让 accepted `RS + refined CX3-D` 在搜索中只在真正需要时消费少量额外计算，并且这点额外计算必须围绕“局部可恢复性、事件触发微审查、可复用失败记忆”展开，而不是再去做更强的静态语义判别。**

`CX15` 的推荐方向不是“再预测一次正确 token”，而是：

- 把 **recoverability / exitability** 变成主对象；
- 把 **event trigger** 变成高开销计算的唯一入口；
- 把 **failure / escape memory** 变成跨 episode 的可复用资产。

## 2. What `CX1-CX14` Actually Established

### 2.1 已被证伪或基本跑穿的对象

- `dense field / residual`：只能做保守修形，难以形成稳定强增益；
- `successor-level heavy semantics`：有效，但 runtime 无法部署；
- `coarse semantic atlas / strategic partition`：dev 可行，locked test 不稳；
- `sketch / defer / repair`：能消害，不能保益；
- `static allocation / contract`：能重排预算，不能产生 leverage；
- `episode-local memory`：方向对，但如果 memory 只表示“重复失败”，而不表示“是否仍可恢复”，则压缩后容易退化成 tie。

### 2.2 当前真正缺失的东西

现有路线真正缺的不是更大的模型，而是三类结构化对象：

1. **局部可恢复性对象**：这里是可逆的 bottleneck，还是不可恢复的 trap？
2. **事件触发机制**：什么时候值得花一次小额额外计算？
3. **失败-逃逸记忆**：过去失败的局部模式，是否能在后续 episode 中直接复用？

`CX15` 应围绕这三者，而不是继续围绕 family / token / sketch。

## 3. Literature Sweep

下面只保留对 `CX15` 最相关、且能直接支持“recoverability + trigger + memory”三件事的论文。

### 3.1 Recoverability / Fail-Safe / Reachability

1. **Towards Provably Not-at-Fault Control of Autonomous Robots in Arbitrary Dynamic Environments** — RSS 2019  
   Link: <https://roboticsconference.org/2019/program/papers/011/index.html>
2. **ARMTD: Anytime Robot Motion Planning with Transit-Driving Modes and Reachability-Based Safety** — RSS 2020  
   Link: <https://roboticsconference.org/2020/program/papers/46.html>
3. **Neural Value Functions for Safe Reachability-Based Control of Autonomous Systems** — RSS 2023  
   Link: <https://roboticsconference.org/2023/program/papers/036/>

**启发**

- 规划里“是否可继续前进”不够，关键是“是否仍有 fail-safe / recoverable continuation”；
- recoverability 可以作为局部 margin，而不一定非要做完整 long-horizon planning；
- reachability 视角最适合把 `reverse-setup / escape margin / still-recoverable` 这类信号对象化。

**对当前项目的含义**

- `CX8-D Heavy` 的有效语义，本质上更接近 recoverability reasoning，而不是普通 token classification；
- `CX15` 应优先把 “这里是否还保留可恢复退出” 变成 planner 可查的低成本对象。

### 3.2 Event Trigger / Selective Review / Lazy Expansion

1. **Generalized Lazy Search for Robot Motion Planning: Interleaving Search and Edge Evaluation via Event-Based Toggles** — ICAPS 2019  
   Link: <https://icaps19.icaps-conference.org/accepted-papers.html>
2. **When to Replan?** — ICRA 2024  
   Link: <https://www.omron.com/sinicx/research/reserach_result/all/ICRA2024_WhenToReplan.html>
3. **Adaptive Online Replanning with Diffusion Models** — NeurIPS 2023  
   Link: <https://proceedings.neurips.cc/paper_files/paper/2023/hash/f0af4dae6dd13c3847cc2a0f41541f2f-Abstract-Conference.html>
4. **Learning Efficient Abstract Planning Models that Choose What to Predict** — CoRL 2023 / OpenReview  
   Link: <https://openreview.net/forum?id=ba27-RzQssu>

**启发**

- 高开销 computation 不应常驻，而应由事件触发；
- 关键不是“会不会重规划”，而是“什么时候值得做额外审查”；
- selective prediction 的核心结论是：**预测对象必须被严格裁剪**。

**对当前项目的含义**

- `CX15` 不应再让微审查 per-node 常驻；
- 额外 review 只能在 `stall / duplicate burst / accepted ratio collapse / recoverability margin 下降` 等事件出现时触发；
- 这与 `CX14-B` 的 runtime sprint 一致：必须先把 trigger 变成第一公民。

### 3.3 Failure Memory / Experience Reuse / Narrow-Corridor Memory

1. **Experience Graphs: Leveraging Experience for Planning with Sparse Roadmap Spanners** — RSS 2012 / IJRR lineage  
   Link: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
2. **Thunder Framework: Experience-Based Motion Planning in Changing, Partially-Known Environments** — ICRA 2015  
   Link: <https://arxiv.org/abs/1508.01296>
3. **Generalized Experience-Based Multi-Agent Path Finding with Narrow Corridors** — RSS 2024  
   Link: <https://roboticsconference.org/program/papers/065/>

**启发**

- experience reuse 在 narrow / repetitive geometry 下是成立的；
- 但传统 experience graph 主要存储的是“成功路径”；
- 对当前项目，更稀缺也更有价值的其实是：
  - 哪些局部入口会反复失败；
  - 哪些短 escape prefix 能把搜索拉回 recoverable basin。

**对当前项目的含义**

- `CX15` 不应再存整条成功路径；
- 应优先存储 **失败入口 + 逃逸短前缀** 的局部记忆。

### 3.4 Dead-End / Depression Avoidance

1. **Avoiding Dead Ends in Real-Time Heuristic Search** — AAAI 2018  
   Link: <https://ojs.aaai.org/index.php/AAAI/article/view/11508>
2. **Real-Time Heuristic Search: Depression Avoidance and Learning** — JAIR 2012  
   Link: <https://www.jair.org/index.php/jair/article/view/10817>

**启发**

- 真正拖垮搜索的，不一定是全局 heuristic 差，而是落入局部 depression / dead end；
- 有效机制不是“更大模型”，而是：
  - 发现 depression；
  - 记住 depression；
  - 把优先级推回 border。

**对当前项目的含义**

- `CX14-B` 的 local penalty 已接近这个对象，但还缺：
  - recoverability-aware trigger；
  - depression border 的方向性修复；
  - 跨 episode 可复用记忆。

## 4. Structural Diagnosis for `CX15`

综合文献与 `CX1-CX14` 结果，`CX15` 要绕开的不是单一 bug，而是三类结构陷阱：

### 4.1 不能再把 “semantic identity” 当主对象

`CX10-CX12` 已经证明：

- 仅凭局部几何 + sketch confidence，很难稳定区分 `flange trap` 与 `recoverable narrow passage`；
- 再做更复杂 classifier，大概率只会把系统推回 `误触发 / over-defer`。

### 4.2 不能只做 “重复失败计数”

`CX14` 说明重复失败 memory 有信号，但 runtime sprint 也证明：

- 若 memory 只表达 “这里经常失败”，
- 而不表达 “这里是否还有 recoverable exit”，
- 压缩后就容易退化为整体 tie。

### 4.3 不能把高开销逻辑常驻在线循环

`CX8-D Heavy` 和 `CX14` 都证明：

- 一旦高表达力逻辑 per-expansion 常驻，
- runtime 很快就超过部署边界。

所以 `CX15` 需要的是：

> **recoverability-aware, event-triggered, memory-backed sparse review**

而不是 another guidance map。

## 5. Proposed `CX15` Candidate Families

### CX15-A: `RS-RMC` — Recoverability Margin Cache

**核心想法**

1. 离线或一次性地为局部状态抽象建立一个 **recoverability margin cache**：
   - 当前 heading / clearance / corridor geometry 下，
   - 是否仍存在低成本 reverse-setup / escape continuation；
2. 在线阶段不预测 token，只查询当前局部 signature 的 recoverability margin；
3. 当 margin 高时完全不干预；margin 低但未到 hopeless 时，才施加极小 bundle-family bias 或标记为 review candidate。

**干预对象**

- 不是 sketch；
- 不是 family classifier；
- 而是 **局部可恢复性 margin**。

**如何继承 `CX8-D` 的有效语义**

- `CX8-D Heavy` 真正有价值的是：在 bottleneck 中识别“何时需要 reverse-setup 才可恢复”；
- `RS-RMC` 不直接复刻 bundle arbitration，而是先把 “still-recoverable vs entering trap” 这件事对象化。

**理论抓手**

- reachable / viable set；
- fail-safe continuation margin；
- 在线 `O(1)` table lookup。

**与已有工作的差异**

- 不像 RSS 2019 / RSS 2020 那样做完整 fail-safe planning；
- 不像 `CX10-CX12` 那样做 semantic token validity；
- 创新点在于：把 reachability 思想压缩成 **planner-local recoverability cache**，作为 cheap control signal。

**风险**

- margin 估计过粗会把 good narrow 与 real trap 混淆；
- 需要定义可在当前仓库中稳定提取的局部 recoverability proxy。

### CX15-B: `RS-EMR` — Event-Triggered Micro-Review

**核心想法**

1. accepted `RS + refined CX3-D` 作为默认执行；
2. 只有当以下事件之一出现时，才触发一次 **bounded micro-review**：
   - duplicate burst；
   - accepted successor ratio collapse；
   - anchor progress flatline；
   - recoverability margin 持续下降；
3. micro-review 只在小窗口内评估少量 bundle-family / reverse-setup alternative，不进入全局 per-successor heavy mode。

**干预对象**

- 不是全局 replanning；
- 而是 **搜索中的局部异常窗口**。

**如何继承 `CX8-D` 的有效语义**

- 保留 `reverse-setup / bundle arbitration` 的局部语义；
- 但只在明确事件触发后，对极少数窗口做 bounded review。

**理论抓手**

- event-triggered evaluation；
- lazy search / selective edge evaluation；
- 在线复杂度 `O(M · K)`，其中 `M` 是触发窗口数，`K` 是每次微审查的小候选集。

**与已有工作的差异**

- 不像 ICRA 2024 / NeurIPS 2023 的 replanning 工作那样重做整条计划；
- 不像 `CX14-B` 那样持续性地维护所有 signature penalty；
- 创新点在于：把额外 computation 压缩成 **search-dynamics gated micro-review**。

**风险**

- 触发器过弱则 review 太少，触发器过强则 runtime 再次上升；
- 需要与 `RS-RMC` 联动，否则事件只基于 process statistics 可能区分力不足。

### CX15-C: `RS-FME` — Failure Memory of Escape Motifs

**核心想法**

1. 不再存“成功整条轨迹”，而是存储：
   - 失败入口 signature；
   - 失败时最常见的 primitive bundle；
   - 最终把系统带回 recoverable basin 的 **短 escape motif**（2-4 primitive prefix）；
2. 这些 motif 跨 episode 复用；
3. 在线检索时：
   - 若当前局部模式与某失败入口高度相似，则降低原入口优先级；
   - 若已有 escape motif，则只对前几步做很小 bias。

**干预对象**

- 不是 static semantic sketch；
- 而是 **failure-to-escape local motifs**。

**如何继承 `CX8-D` 的有效语义**

- `CX8-D Heavy` 的成功常表现为少量关键 reverse-setup maneuver；
- `RS-FME` 把这种少量高价值 maneuver 从 full semantic logic 里“提纯”为可复用 escape motif。

**理论抓手**

- experience reuse；
- case-based planning；
- memory retrieval with bounded local prefix injection；
- 在线 `O(1)` hash / `O(log N)` approximate retrieval。

**与已有工作的差异**

- 不像 Experience Graphs / Thunder 存完整成功路径；
- 不像 `CX10-D` 存 scene-level sketch；
- 创新点在于：只存 **失败入口与短逃逸模式**，这是更适合当前 hard narrow regime 的经验单元。

**风险**

- 需要构建新数据管道，把失败 episode 与 escape prefix 对齐；
- 若 escape motif 泛化不足，可能重新滑回局部误触发。

### CX15-D: `RS-CBR` — Comfortable Border Repair

**核心想法**

1. 当搜索被检测为进入 local depression 时，不做全局 penalty，也不直接调用 sketch；
2. 而是在局部窗口内找出 **仍具 recoverability 的 border states**；
3. 然后仅对当前 depression 内部做一次小型 reverse-wave repair，把优先级“抬向 border”，迫使搜索先逃出局部塌缩盆地，再恢复 baseline。

**干预对象**

- 不是局部 token；
- 不是跨 scene route；
- 而是 **depression 的 border 结构**。

**如何继承 `CX8-D` 的有效语义**

- `CX8-D Heavy` 本质上在 hard case 中强迫搜索不要继续错误 commitment；
- `RS-CBR` 用 border repair 的方式实现同样的“不继续往 trap 深处走”的语义，但不要求显式 semantic sketch。

**理论抓手**

- depression avoidance；
- dead-end border propagation；
- 在线 `O(B)`，仅在触发窗口内对小 basin 做局部反向传播。

**与已有工作的差异**

- 不像 `CX14-B` 只是累计 penalty；
- 不像 `CX13` 只是换 queue discipline；
- 创新点在于：把 **recoverable border** 作为局部修复目标，而不是把所有失败 signature 一视同仁地惩罚。

**风险**

- 需要可靠定义“当前局部 depression 的边界”；
- 若窗口提取不稳，可能仍出现过宽修复。

## 6. Recommended Execution Order

推荐顺序：`CX15-A -> CX15-B -> CX15-C -> CX15-D`

1. **先做 `CX15-A / RS-RMC`**
   - 最低风险；
   - 先验证 recoverability 这个对象本身是否有判别力。
2. **再做 `CX15-B / RS-EMR`**
   - 若 `RMC` 有信号，再把高开销 computation 收缩成 trigger-only micro-review。
3. **第三做 `CX15-C / RS-FME`**
   - 若 `A/B` 的单次 episode 证据不够，再引入跨 episode 的 failure memory。
4. **最后做 `CX15-D / RS-CBR`**
   - 方法学最强，但实现也最复杂；
   - 适合在前面三条已经澄清 recoverability / trigger / memory 的有效性后再推进。

## 7. Protocol and Acceptance Boundary

`CX15` 必须继续遵守：

1. accepted baseline 仍是 `RS + refined CX3-D / RS-HPG`；
2. 禁止回到 per-successor 深模型常驻推理；
3. public gate 仍以 `parasol_narrow/test exp4` 为首要：
   - `exp_delta > 0`
   - `mean_time_overhead_ratio < 0.30`
   - `flange exp_delta >= 0`
4. 只有 public gate 通过，才允许消费 `rs_root_hard_v2/test`；
5. `mp/csm` 继续只做 ordinary-support non-regression audit。

## 8. Main Recommendation

`CX15` 最值得押注的首选路线是：

> **`CX15-A / RS-RMC` + `CX15-B / RS-EMR` 组合**

原因很直接：

- `RMC` 负责提供当前路线最缺的对象：cheap recoverability evidence；
- `EMR` 负责提供当前路线最缺的执行形态：event-triggered sparse review；
- 二者组合最可能同时解决：
  - `CX10-CX12` 的 distinguishability crisis；
  - `CX14` 的 runtime-vs-signal collapse。

如果这两条路线仍不能在 public gate 上形成正向结果，则当前 `P0-CX` 很可能就不再缺“小修补”，而是真的缺新的 planner backbone 假设。

## 9. Source Links

- RSS 2019 not-at-fault control: <https://roboticsconference.org/2019/program/papers/011/index.html>
- RSS 2020 ARMTD: <https://roboticsconference.org/2020/program/papers/46.html>
- RSS 2023 neural value functions for safe reachability: <https://roboticsconference.org/2023/program/papers/036/>
- ICAPS 2019 generalized lazy search: <https://icaps19.icaps-conference.org/accepted-papers.html>
- ICRA 2024 When to Replan?: <https://www.omron.com/sinicx/research/reserach_result/all/ICRA2024_WhenToReplan.html>
- NeurIPS 2023 adaptive online replanning: <https://proceedings.neurips.cc/paper_files/paper/2023/hash/f0af4dae6dd13c3847cc2a0f41541f2f-Abstract-Conference.html>
- CoRL 2023 choose what to predict: <https://openreview.net/forum?id=ba27-RzQssu>
- RSS 2012 Experience Graphs: <https://www.ri.cmu.edu/publications/experience-graphs-leveraging-experience-for-planning-with-sparse-roadmap-spanners/>
- ICRA 2015 Thunder: <https://arxiv.org/abs/1508.01296>
- RSS 2024 experience-based MAPF with narrow corridors: <https://roboticsconference.org/program/papers/065/>
- AAAI 2018 avoiding dead ends in real-time heuristic search: <https://ojs.aaai.org/index.php/AAAI/article/view/11508>
- JAIR 2012 depression avoidance and learning: <https://www.jair.org/index.php/jair/article/view/10817>
