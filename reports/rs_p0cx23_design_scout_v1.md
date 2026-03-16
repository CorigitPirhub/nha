# P0-CX23 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-14`

## 1. Executive Summary

`CX22-D / RS-LAG-SHA` 已经把 `CX21-B` 修到当前最有价值的位置：

1. 保住了大部分 `flange` gain；
2. 把 overhead 从 `3.216x` 压到 `2.647x`；
3. 但 `maze / narrow_passage / parasol_misc` 仍明显为负；
4. 方法形态仍偏“工程门控”，还不够像一个可以单独陈述的创新点。

因此 `CX23` 的问题不应再写成“怎么继续调 `CX22-D`”，而应写成：

> **如何把 `CX22-D` 升级成一个可独立陈述的方法对象，使其既保留 `flange` gain，又能系统性减少负迁移 class。**

本轮冻结四条方案：

1. `CX23-A / RS-SAD` — Shadow Adoption Distillation
2. `CX23-B / RS-CAD` — Contrastive Adoption Debias
3. `CX23-C / RS-HAA` — Hierarchical Adoption Automaton
4. `CX23-D / RS-CCE` — Counterfactual Class Editor

它们都不是参数微调，而是围绕 `CX22-D` 做新的结构对象。

## 2. What `CX22-D` Actually Established

`CX22-D` 已经明确了三点：

1. **shadow adoption 是对的 repair object**
   - public `exp4 = +326.333`
   - `flange = +1424.0`
   - overhead `2.647250`
2. **负迁移 class 仍然存在**
   - `maze = -113.0`
   - `narrow_passage = -87.75`
   - `parasol_misc = -130.333`
3. **当前方法还不是一个足够强的“可陈述创新点”**
   - 它更像 class gate / shadow adoption 工程；
   - 而不是一个清晰的、可推广的算法对象。

因此后续真正该做的不是继续改 `min_hits / lcb_q / threshold`，而是发明一个新的、明确的修复对象。

## 3. Design Principles

`CX23` 的所有候选都必须满足：

1. **建立在 frozen `CX22-D` 之上**；
2. **不是参数微调**；
3. **方法对象可单独命名、单独消融、单独讲清楚**；
4. **必须直接对准 `CX22-D` 的核心短板：负迁移 class 没修掉。**

## 4. Frozen `CX23` Plans

### CX23-A: `RS-SAD` — Shadow Adoption Distillation

**核心想法**

把 `CX22-D` 当前的 adoption behavior 当 teacher，蒸馏出一个更小、更可解释的 adoption student。

**形式可以是**

1. small tree ensemble
2. finite-state controller
3. tiny MLP + distilled rule table

但必须满足：

- 能解释 adoption region；
- 能剪掉长尾坏 class；
- 能比 `CX22-D` 更便宜。

**为什么它值得优先做**

1. 最直接承接 `CX22-D`；
2. 最容易形成独立 innovation story；
3. 最有希望同时改善 runtime 与 generalization。

**主要风险**

1. teacher 本身若仍偏，student 可能复制偏差；
2. 过强压缩会损伤 `flange` gain。

### CX23-B: `RS-CAD` — Contrastive Adoption Debias

**核心想法**

显式建模：

1. positive-support classes
2. negative-transfer classes

并通过 contrastive / metric / signed-head 方式把它们拉开。

最终输出三态：

1. `promote`
2. `suppress`
3. `abstain`

**为什么它值得做**

1. `CX22-D` 的根本问题正是负迁移 class 残留；
2. 这条线直接把“坏 class”提升为一等对象。

**主要风险**

1. 若正负类重叠太强，contrastive separation 不稳；
2. suppressor 过强会重新把系统压回保守 tie。

### CX23-C: `RS-HAA` — Hierarchical Adoption Automaton

**核心想法**

把 adoption 从静态 class gate 变成时序 automaton：

1. `observe`
2. `candidate`
3. `commit`
4. `suppress`
5. `recover`

只有短时序证据持续成立，才允许真正 commit。

**为什么它值得做**

1. 当前很多误迁移很可能来自过早 commit；
2. 短时序一致性也许比更复杂的静态 class 更有效。

**主要风险**

1. 状态机过慢会错过 `flange` 的短窗口 gain；
2. 复杂度上升但收益不一定足够。

### CX23-D: `RS-CCE` — Counterfactual Class Editor

**核心想法**

基于 `CX22-D` 的 dev/public replay 构建 class-level counterfactual pairs：

1. adopt vs no-adopt
2. adopted class vs safer sibling class

再训练一个轻量 editor，只在高风险 class 上做：

1. replace class
2. soften adoption
3. abstain

**为什么它值得做**

1. 它直接回答“如果刚才不用这个 class 会怎样”；
2. 与普通 gate 不同，它是离线 counterfactual repair 对象。

**主要风险**

1. counterfactual 估计不稳会引入噪声；
2. 数据和实现复杂度最高。

## 5. Recommended Order

### Rank 1: `CX23-A / RS-SAD`

因为它最有机会同时满足：

1. 方法可陈述；
2. runtime 可下降；
3. 保持 `CX22-D` 的主收益。

### Rank 2: `CX23-B / RS-CAD`

因为它最直接对准负迁移问题本身。

### Rank 3: `CX23-C / RS-HAA`

适合在确认静态 class 表达不够时再做。

### Rank 4: `CX23-D / RS-CCE`

潜在最强，但工程风险最高。

## 6. Final Judgment

围绕 `CX22-D` 的下一步，不应再是参数微调，而应转向：

1. distillation
2. contrastive debias
3. temporal automaton
4. counterfactual class editing

这四条线都能被单独陈述为创新点，也都更符合 `CX22-D` 当前暴露出的真实问题。
