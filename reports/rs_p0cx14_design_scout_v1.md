# P0-CX14 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-12`

## 1. Executive Summary

到 `CX13` 为止，`P0-CX` 已经系统地穷尽了几类直觉上最可能成功的路线：

- `CX1-CX7`：field / residual / topology-preserving refinement；
- `CX8`：successor-level semantic intervention；
- `CX10-CX12`：semantic repair / defer / trap-aware sketch gating；
- `CX13`：computation allocation / schedule / contract design。

它们共同给出的结论非常清楚：

1. **正向 ceiling 真实存在**：`CX8-D Heavy` 证明某种强语义干预确实能改善 hard cases；
2. **但 token/repair family 会掉进“误触发 vs 过度抑制”的双重陷阱**；
3. **而纯 allocation family 又会掉进“重新分配了算力，但没有带来 leverage”的陷阱**。

因此 `CX14` 不应继续围绕：

- semantic token validity；
- sketch repair；
- defer / abstain；
- basin budget / schedule contract；

做局部修补。

`CX14` 的主问题应该被重写为：

> **如何让 accepted `RS + refined CX3-D` 在搜索过程中获得“可塑性”，但这种可塑性必须来自极轻量、可复用、episode-local 的结构记忆，而不是新的重模型或局部语义分类器。**

更直白地说，`CX14` 应从 “predict the right intervention” 转向：

> **learn cheap reusable search memory.**

## 2. What the Previous Families Still Miss

### 2.1 `CX8-CX12` 的共同局限：它们都把“正确动作/正确 token”当成主对象

不管是：

- `CX8-D` 的 heavy bundle arbitration；
- `CX10-D` 的 sketch；
- `CX11` 的 defer / verifier；
- `CX12` 的 trap-aware filters / signed adjustment；

它们都隐含地在问：

> “在这里，什么 token / semantic actuation 是对的？”

问题在于，这个对象太脆弱：

- `flange` 与 `narrow_passage` 的局部几何高度重叠；
- 一旦判断错，就会付出灾难性代价；
- 一旦 gate 变保守，又会把 sparse positive signal 一并抹平。

### 2.2 `CX13` 的局限：它把“预算对象”换了，但没有让搜索真正变得更聪明

`CX13-A/B/C` 已经说明：

- 单纯切换 budget / schedule / contract 对象；
- 如果没有新的、能在 episode 内累积的证据；
- 最终只会把 accepted baseline 重新参数化一遍。

也就是说，`CX13` 缺的是：

> **search-time evidence accumulation mechanism**

而不是另一个离线配置对象。

## 3. Literature Sweep

下面只保留对 `CX14` 最相关的 primary-source 文献，并强调它们的结构启发与局限。

### 3.1 Learned Search Guidance and Heuristic Plasticity

1. **Learning Heuristic Search via Imitation** — CoRL 2018 / PMLR  
   Link: <https://proceedings.mlr.press/v87/chitnis18a.html>

2. **Policy-Guided Heuristic Search with Guarantees** — arXiv  
   Link: <https://arxiv.org/abs/2103.11505>

3. **Learning Efficient Abstract Planning Models that Choose What to Predict** — CoRL 2022 / OpenReview  
   Link: <https://openreview.net/forum?id=ba27-RzQssu>

**启发**：
- 搜索 guidance 不一定要依赖更大模型；
- 抽象层和选择性预测非常关键；
- “不是所有信息都值得预测”这件事已经是共识。

**局限**：
- 这些工作大多依赖静态 prior / learned heuristic；
- 很少让搜索在 **同一 episode 内** 利用刚刚观察到的 failure pattern 去快速改写后续优先级。

### 3.2 Meta Planning, Configuration, and Compute Allocation

1. **CAMPs: Cost-Aware Meta Planning with Search** — ICML 2024 / OpenReview  
   Link: <https://openreview.net/forum?id=Uuk7eHcngv>

2. **Query-Efficient Planning in Deterministic MDPs under Linear Realizability and Optimal Partial Feedback** — COLT 2021 / PMLR  
   Link: <https://proceedings.mlr.press/v134/chen21a.html>

3. **Planning with a Learned Policy Basis to Optimally Solve Complex Tasks** — OpenReview  
   Link: <https://openreview.net/forum?id=Ht90v3Wqvb>

**启发**：
- 计算预算、查询成本、实例配置确实可以成为 planning 的主对象；
- meta planning 的对象可以是“算哪里 / 算多久”，而不是“输出哪个动作”。

**局限**：
- 这些方法往往把控制对象放在 **planner selection / policy basis / high-level planning** 层；
- 对当前项目来说，还是太“静态”了，缺少 episode-local 搜索记忆。

### 3.3 Structural Abstraction and Long-Horizon Planning

1. **Combined Task and Motion Planning via Sketch Decompositions** — OpenReview  
   Link: <https://openreview.net/forum?id=ojc4aWQfP2>

2. **RT-Trajectory: Robotic Task and Motion Planning via Hierarchical Sketches** — arXiv 2025  
   Link: <https://arxiv.org/abs/2503.22195>

3. **VisualPredicator: Learning Abstract World Models with Neuro-Symbolic Predicates for Robot Planning** — ICLR 2025 / OpenReview  
   Link: <https://openreview.net/forum?id=mqIQE8BftT>

**启发**：
- 高层结构对象是必要的；
- predicate / abstraction / sketch 可以显著缩短 horizon。

**局限**：
- `CX10-CX12` 已经说明：如果高层对象最终又回到 fragile token gating，就会再次掉进 distinguishability crisis。

### 3.4 Deferral, Abstention, and Safety

1. **SLTD: Learning to Defer for Sequential Decision-Making under Uncertainty** — arXiv 2024  
   Link: <https://arxiv.org/abs/2402.01830>

2. **Beyond Confidence: Trustworthy Learning-to-Defer via Conformal Prediction Sets** — arXiv 2023  
   Link: <https://arxiv.org/abs/2307.04993>

3. **Selective Omniprediction and Fair Abstention** — OpenReview  
   Link: <https://openreview.net/forum?id=BoYGLpNXZd>

**启发**：
- defer 可以降低 catastrophic mistakes；
- calibrated abstention / support-aware fallback 是对的。

**局限**：
- `CX11` 已经把“defer 作为主对象”跑穿；
- 继续增强 defer 只会更稳定地得到 baseline tie。

## 4. Structural Limit Analysis

结合现有证据和文献，`CX14` 需要绕开的三类结构陷阱是：

### 4.1 不能再依赖 fragile local semantic discrimination

因为这已经被 `CX10-CX12` 证明会反复失败。

### 4.2 不能只做静态 offline configuration

因为 `CX13` 说明：

- static schedule / contract / budget object
- 若不能在 episode 内吸收搜索反馈
- 就只是在重放 accepted baseline。

### 4.3 不能再让“是否安全”成为唯一主问题

因为这会再次滑向：

- 消害成功；
- 保益失败；
- 最终 tie baseline。

所以 `CX14` 的对象必须同时满足：

1. **episode-local**
2. **cheap**
3. **state abstraction aware**
4. **can accumulate evidence online**

## 5. Proposed CX14 Candidate Families

### CX14-A: `RS-NSG` — Novelty Signature Guidance

**核心想法**：
1. 为搜索节点定义一个极廉价的 **nonholonomic local signature**，例如：
   - clearance bin
   - goal-distance bin
   - heading-to-goal bin
   - trap-score bin
   - corridor-score bin
   - yaw bin
2. 搜索中维护一个 episode-local signature memory：
   - 已经多次出现、且没有带来可见 progress 的 signature，将逐渐受到 penalty；
   - 新颖且在结构上更像 corridor 的 signature 得到轻微 bonus。
3. 不去预测“哪个 token 对”，而是让搜索自动减少对“重复失败局部模式”的浪费。

**干预对象**：
- 不是 token；
- 不是 basin；
- 而是 **state-abstraction signature novelty**。

**何时干预**：
- 在线每次 expand 时常数级查询 / 更新 signature table。

**理论抓手**：
- width-based / novelty-aware search 的思想；
- online memory compression；
- cheap abstraction over nonholonomic state space。

**可部署性**：
- 在线仅需：
  - `O(1)` hash lookup；
  - `O(1)` counter update；
- 不依赖 per-successor 模型前向。

**创新性**：
- 不做 semantic repair；
- 不做 schedule catalog；
- 而是把 **episode-local repeated-failure pattern** 作为一等对象。

**为什么可能打破 Pareto 死锁**：
- catastrophic waste 往往来自反复落入相似局部模式；
- signature novelty guidance 直接压制这种重复，而不用 fragile 地判断“这里是什么 family / token”。

**风险**：
- signature 设计过粗会把好状态和坏状态混在一起；
- 设计过细则记忆复用不足。

---

### CX14-B: `RS-LHU` — Local Heuristic Update

**核心想法**：
1. 保持 accepted `RS + CX3-D` 作为初始 field；
2. 在同一搜索 episode 内，若某类 local signature 持续出现：
   - accepted successor 率低；
   - anchor progress 低；
   - queue 中重复出现；
   就对该 signature 附加一个小的 **online penalty update**；
3. 这个 update 不是学习新模型，而是 episode-local 的 sparse heuristic rewrite。

**干预对象**：
- **online residual memory**
- 不是 offline residual field。

**何时干预**：
- 只在搜索中，根据当前 episode 的失败 evidence 做稀疏增量更新。

**理论抓手**：
- online learning / no-regret flavor 的 heuristic adaptation；
- sparse local value correction；
- memory-based self-calibration。

**可部署性**：
- 在线只需：
  - signature lookup；
  - 稀疏 penalty table update；
- 复杂度仍接近 `O(1)`。

**创新性**：
- 与 `CX1-CX7` 不同，这不是离线学一个 residual field；
- 与 `CX10-CX12` 不同，这也不是 semantic token gate；
- 它是 **search-time self-correcting heuristic memory**。

**为什么可能打破 Pareto 死锁**：
- 如果当前痛点是“accepted field 对某些 trap signature 的代价太乐观”，则在线 sparse rewrite 比 offline token repair 更有机会保住 gain，同时不触发大规模误伤。

**风险**：
- update 过快会导致搜索抖动；
- update 过慢则不产生效果。

---

### CX14-C: `RS-MHQ` — Multi-Head Queueing

**核心想法**：
1. 不再只有单一 priority ordering；
2. 为节点同时维护 2-3 种极轻量 head：
   - progress head
   - novelty head
   - escape / trap head
3. 搜索器不学习动作，而是在 node pop 时按一个小型 deterministic scheduler 在这些 head 之间切换：
   - early phase 更偏 progress；
   - stall phase 更偏 novelty / escape；
   - recovery phase 再回到 progress。

**干预对象**：
- **queue discipline**
- 不是 heuristic token。

**何时干预**：
- 每次 pop node 时做 `O(1)` phase switch / queue select。

**理论抓手**：
- multi-queue best-first search；
- phase-based compute triage；
- meta-reasoning over queue discipline。

**可部署性**：
- 在线 `O(1)` phase dispatch；
- 所有 head 都由 cheap analytic features构成。

**创新性**：
- 相比 `CX13-B` 的 static schedule，它是 **search-time queue discipline adaptation**；
- 相比 `CX14-A/B`，它不直接改 heuristic，而是改 “谁先被展开”。

**为什么可能打破 Pareto 死锁**：
- 如果问题的本质是 accepted planner 的 queue discipline 在 hard scenes 上过早塌缩到错误 basin，那么 multi-head queueing 可能比 token repair 更自然。

**风险**：
- 若 head 之间差异不够大，就仍会退化成 accepted baseline；
- 需要防止 queue oscillation。

## 6. Recommended Order

推荐顺序：`CX14-A -> CX14-B -> CX14-C`

### 为什么先做 `CX14-A / RS-NSG`

- 它最便宜；
- 最贴近当前 failure pattern：重复陷入相似局部 trap signature；
- 最有希望在不引入 brittle token semantics 的前提下产生净 gain。

### 为什么第二做 `CX14-B / RS-LHU`

- 如果 novelty alone 不够，下一步最值得做的是在线 sparse heuristic self-correction；
- 它比 `CX1-CX7` 更动态，比 `CX10-CX12` 更少依赖 fragile semantics。

### 为什么第三做 `CX14-C / RS-MHQ`

- queue discipline adaptation 很有创新性；
- 但调度逻辑与验证成本更高，放在 `A/B` 之后更稳。

## 7. Minimum Acceptance Bar

任一 `CX14` 候选若要进入下一阶段严格验证，至少需要：

1. public `exp4` 上：
   - `exp_delta > 0`
   - `mean_time_overhead_ratio < 0.30`
   - `flange exp_delta >= 0`
2. `mp/csm` ordinary-support 不劣化；
3. 在线逻辑必须保持 `O(1)` 或 `O(K)`；
4. 不能再次退回 sketch/defer/repair 或静态 budget family。

## 8. Final Recommendation

`CX14` 的主命题应冻结为：

> **Use episode-local search memory, not semantic repair.**

也就是说：

- 不再问“这个 token 对不对”；
- 也不再只问“预算该怎么静态分配”；
- 而是让搜索在本 episode 中，廉价地记住：
  - 哪些局部模式已经反复失败；
  - 哪些局部模式仍值得探索；
  - 哪种 queue discipline / sparse penalty 更新最能把预算从无效 basin 挪走。

当前首选执行入口：`CX14-A / RS-NSG`。
