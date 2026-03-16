# P0-CX24 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-14`

## 1. Executive Summary

`CX23-C / RS-HAA` 已经把当前 repair 线推进到了一个新的边界：

1. public `exp4 = +392.889`
2. `flange = +1428.4`
3. `narrow_passage = +98.25`
4. 但 `maze = -113.0`
5. `parasol_misc = -58.333`

因此 `CX24` 的问题不应再写成“再调 automaton 多长 / 多严”，而应写成：

> **如何把 `RS-HAA` 从“短时序一致性驱动的选择性 leverage”升级成带陷阱见证、尾部支持控制、反事实 commit 证书、组稳健目标与完整诊断平面的系统。**

本轮针对 5 个明确问题，各冻结 1 条方案：

1. `CX24-A / RS-MTW` — Maze Trap Witness Automaton
2. `CX24-B / RS-TAS` — Tail-Aware Abstention Shield
3. `CX24-C / RS-GRA` — Group-Robust Automaton
4. `CX24-D / RS-CCC` — Counterfactual Commit Certificate
5. `CX24-E / RS-ATO` — Adoption Trace Observatory

## 2. What `CX23-C` Actually Established

`CX23-C` 的结果说明：

1. 时序 automaton 本身是对的对象；
2. 它确实修好了 `narrow_passage`；
3. 但它仍会在某些 family 上“越看越自信地走错”；
4. 并且当前诊断证据太薄，导致修复只能靠 aggregate metrics 猜。

因此 `CX24` 必须围绕以下 5 个已确认问题逐一补结构。

## 3. Literature Sweep by Issue

### 3.1 `maze` 负项：陷阱 / dead-end / topology witness 不足

**Primary sources**

1. Avoiding and Escaping Depressions in Real-Time Heuristic Search  
   Link: https://auld.aaai.org/Library/JAIR/Vol43/jair43-014.php
2. Escaping Heuristic Depressions in Real-Time Heuristic Search  
   Link: https://www.cs.toronto.edu/~jabaier/publications/her-bai-aamas11.pdf
3. Avoiding Dead Ends in Real-Time Heuristic Search  
   Link: https://www.cs.unh.edu/~ruml/papers/safety-aaai-18-corrected.pdf
4. Hierarchical Motion Planning in Topological Representations  
   Link: https://argmin.lis.tu-berlin.de/papers/12-zarubin-RSS.pdf

**对当前问题的启发**

1. maze 类错误更像 heuristic depression / dead-end / trapped basin，而不是单纯短时序 noise；
2. 仅用时序一致性会把“重复可见、但实际上无出口”的模式当成强信号；
3. 修复对象应是：
   - depression witness
   - dead-end witness
   - topology / escape witness

### 3.2 `parasol_misc` 负项：长尾 misc 仍误 commit

**Primary sources**

1. Introspective Planning: Aligning Robots’ Uncertainty with Inherent Task Ambiguity  
   Link: https://proceedings.neurips.cc/paper_files/paper/2024/file/8451a20c5a7e0ee5671dda28f7daf7f3-Paper-Conference.pdf
2. Conformal Prediction Meets Long-tail Classification  
   Link: https://arxiv.org/abs/2508.11345

**对当前问题的启发**

1. 长尾 misc 更像 support / ambiguity 问题，而不是普通 family discrimination；
2. head-tail coverage gap 会让稀有状态的高置信 commit 不可靠；
3. 修复对象应是：
   - tail-aware support gate
   - minority-aware abstention
   - uncertainty alignment before commit

### 3.3 across-family 稳定增益不足：需要显式 worst-group 目标

**Primary sources**

1. Distributionally Robust Neural Networks for Group Shifts: On the Importance of Regularization for Worst-Case Generalization  
   Link: https://openreview.net/pdf?id=ryxGuJrFvS
2. On the Foundation of Distributionally Robust Reinforcement Learning  
   Link: https://arxiv.org/abs/2404.10645

**对当前问题的启发**

1. 平均增益高不代表 worst-group 可接受；
2. 若不显式优化 worst-group / hidden-group regret，系统会自然偏向最容易出大增益的 family；
3. 修复对象应是：
   - group-adjusted automaton objective
   - worst-group selection criterion
   - latent group robustness

### 3.4 时序证据被欺骗：commit 前需要反事实验证

**Primary sources**

1. Reward Machines: Exploiting Reward Function Structure in Reinforcement Learning  
   Link: https://arxiv.org/abs/2010.03950
2. Counterfactual Explanations as Plans  
   Link: https://arxiv.org/abs/2502.09205
3. Counterfactual Scenarios for Automated Planning  
   Link: https://arxiv.org/abs/2508.21521

**对当前问题的启发**

1. automaton / reward machine 的价值在于把 temporally extended structure显式化；
2. 但真正避免错误强化，还需要比较：
   - commit
   - abstain
   - sibling action/class
3. 因而 commit 前应引入 bounded counterfactual certificate。

### 3.5 缺少可诊断证据：需要专门的 observability / forensics plane

**Related sources**

1. Introspective Planning  
   Link: https://proceedings.neurips.cc/paper_files/paper/2024/file/8451a20c5a7e0ee5671dda28f7daf7f3-Paper-Conference.pdf
2. Evaluating the Effectiveness of Size-Limited Execution Trace with Near-Omniscient Debugging  
   Link: https://www.sciencedirect.com/science/article/abs/pii/S0167642324000406

**对当前问题的启发**

1. 仅看 aggregate family mean 不足以定位误 commit 根因；
2. 需要结构化 trace / transition / state occupancy 证据；
3. 修复对象应是一个和 automaton 配套的 observability plane。

## 4. Frozen `CX24` Plans

### CX24-A: `RS-MTW` — Maze Trap Witness Automaton

**解决问题**

- `maze` 仍显著负项
- 时序证据可能在 maze 中自我强化

**核心想法**

在 `RS-HAA` 基础上增加 trap/topology witness：

1. heuristic depression score
2. dead-end / no-exit witness
3. topology / escape witness

只有当时序 automaton 与 trap witness 一致时才允许 commit。

**为什么可能改善**

它直接对准 `maze = -113.0` 的根因：当前 automaton 只有“连续支持”，没有“真实出口”证据。

### CX24-B: `RS-TAS` — Tail-Aware Abstention Shield

**解决问题**

- `parasol_misc` 仍为负

**核心想法**

给 automaton 增加 tail-aware support / conformal shield：

1. rare-state density
2. support radius
3. head-tail-aware confidence correction

对 tail states 优先：

1. abstain
2. soften commit
3. fallback baseline

**为什么可能改善**

`parasol_misc` 明显是长尾支持不足问题，而不是主 family 规则问题。

### CX24-C: `RS-GRA` — Group-Robust Automaton

**解决问题**

- 整体仍非 across-family 稳定增益

**核心想法**

把 automaton 的选择与训练目标从 average gain 改成：

1. worst-group regret
2. group-adjusted score
3. latent-group robust objective

**为什么可能改善**

当前系统太容易“靠 flange 独赢”。这条线直接把 across-family stability 升成优化对象。

### CX24-D: `RS-CCC` — Counterfactual Commit Certificate

**解决问题**

- 时序证据可能被欺骗

**核心想法**

在 commit 前执行一次 bounded counterfactual check：

1. commit current class
2. abstain / baseline
3. sibling class

只有当前 class 明显占优时才发放 commit certificate。

**为什么可能改善**

它直接阻止“越看越自信地走错”。

### CX24-E: `RS-ATO` — Adoption Trace Observatory

**解决问题**

- 缺少可诊断证据

**核心想法**

为 automaton 增加 mandatory observability plane：

1. state occupancy
2. transition matrix
3. commit / suppress / recover counts
4. false-commit trace slices
5. family-conditioned error ledger

**为什么可能改善**

它本身不直接加分，但没有它，后续修复仍会继续盲修。

## 5. Recommended Order

### Rank 0: `CX24-E / RS-ATO`

必须最先做。否则后续仍缺诊断抓手。

### Rank 1: `CX24-A / RS-MTW`

因为 `maze` 是当前最清晰的结构性失败点。

### Rank 2: `CX24-D / RS-CCC`

因为它直接针对 “被短时序证据欺骗”。

### Rank 3: `CX24-B / RS-TAS`

专门处理 `parasol_misc` 的尾部误迁移。

### Rank 4: `CX24-C / RS-GRA`

在前面几个局部修复有一定站稳后，再做 across-family 稳健目标更合适。

## 6. Final Judgment

围绕 `CX23-C` 的下一轮，不应再是调 automaton 的记忆长度或阈值，而应系统补足 5 个缺口：

1. trap/topology witness
2. tail-aware abstention
3. group-robust objective
4. counterfactual commit certificate
5. observability plane

这 5 条线都能被单独陈述为方法对象，也都直接对应当前已经暴露的 5 个问题。
