# P0-CX22 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-14`

## 1. Executive Summary

`CX21-B / RS-LAG` 已经把当前局面进一步收紧了：

1. 它是目前最强的 public ceiling 分支；
2. 但它的 gain 过度集中在 `flange`；
3. 同时它对 `maze / narrow_passage / parasol_misc` 产生了明确负项；
4. runtime 仍高达 `3.347043x`。

因此 `CX22` 不应再继续扩展新的 `RS-core` 对象，而应拆成两条更务实的 follow-up：

1. **Compression / Stabilization Track**：把 `CX21-B` 压成更便宜、更窄激活、更高支持度的 grammar；
2. **Direct Hard-Test Track**：把 frozen `CX21-B` 从“继续 public 调整”转成“高置信 hard-test 升级或影子 adoption”问题。

本轮冻结四个方案：

1. `CX22-A / RS-LAG-SDT`
2. `CX22-B / RS-LAG-DCG`
3. `CX22-C / RS-LAG-HPG`
4. `CX22-D / RS-LAG-SHA`

其中前两案属于 **定向压缩 / 稳态修复**，后两案属于 **直接单独升级到 hard-test**。

## 2. What `CX21-B` Actually Established

`CX21-B` 的结果不能简单总结成“有 gain / 没 gain”，而应拆成三条：

1. **legality-aware grammar 确实是主贡献对象**
   - public `exp4 exp_delta = +351.722`
   - `No-Legality` ablation 退到 `+70.833`
2. **当前 grammar 仍然太偏**
   - `flange = +1482.6`
   - 但 `maze = -117.0`
   - `narrow_passage = -99.75`
   - `parasol_misc = -94.333`
3. **当前 grammar 仍然太贵**
   - public `mean_time_overhead_ratio = 3.347043`

因此下一轮最核心的问题不是“grammar 有没有信号”，而是：

> **能否把这份强但偏的 legality signal 压缩为高支持、低开销、低误触发的结构；或者，如果不再压缩，能否用 honest hard-test protocol 直接判断它是否值得升级。**

## 3. Literature Sweep

### 3.1 Compression, Rule Extraction, and Structured Policy Simplification

1. **MSVIPER: Extending DAgger to Decision Tree Policies via Imitation Learning**  
   Link: <https://proceedings.neurips.cc/paper/2018/hash/e6d8545daa42d5ced125a4bf747b3688-Abstract.html>
2. **Verifiable and Interpretable Policies through Finite State Controllers**  
   Link: <https://openreview.net/forum?id=znNZ3G5ehD>
3. **Motion Planning using Safe-by-Design Motion Primitives for Autonomous Driving**  
   Link: <https://arxiv.org/abs/2401.10743>
4. **A Modular Framework for Motion Planning Using Safe-by-Construction Maneuver Automata**  
   Link: <https://doi.org/10.1109/TRO.2021.3134946>

**这些工作共同说明**

1. 强策略对象可以被蒸馏为小树、有限状态控制器或稀疏 primitive grammar；
2. 压缩的价值不只在速度，还在于：
   - 删掉长尾 rule；
   - 暴露可诊断 leaf / state；
   - 让后续人为修正更可行；
3. 对 motion planning，primitive legality / automaton interface 往往比 dense score 更稳定。

**对 `CX21-B` 的直接启发**

- `CX21-B` 已经像一个“偏大、偏宽、偏常驻”的 grammar；
- 最自然的 follow-up 不是再加 feature，而是：
  - 把 grammar 蒸馏成小树 / FSC；
  - 或把 grammar 收缩到少量高价值 decision points。

### 3.2 Sparse Intervention and Decision-Point Control

1. **DPRL: Decision Point Reinforcement Learning**  
   Link: <https://arxiv.org/abs/2110.04555>
2. **Conformal Decision Rules for Efficient Optimization Under Uncertainty**  
   Link: <https://proceedings.mlr.press/v235/lu24f.html>
3. **Conformal Risk Training**  
   Link: <https://openreview.net/forum?id=33XGfHLtZg>

**这些工作共同说明**

1. 不是所有状态都值得做复杂决策；
2. 真正高价值的是：
   - 少量 decision points；
   - 对这些点做更强、更硬的规则；
   - 其余点回退默认策略；
3. 如果硬规则没有风险证书，就应该退回 softer action 或 abstain。

**对 `CX21-B` 的直接启发**

- 当前 `CX21-B` 最大的结构问题就是 grammar 介入域太宽；
- 因而更合理的 follow-up 不是“更强 grammar”，而是：
  - **更少介入点**
  - **更窄 hard-forbid 条件**
  - **更明确的 risk-certified abstain**

### 3.3 Honest Promotion, Safe Policy Improvement, and Hard-Test Escalation

1. **Decision-Point Guided Safe Policy Improvement for Efficient Robot Navigation**  
   Link: <https://openreview.net/forum?id=awaeVoRFOOk>
2. **CSPI-MT: Cal-Safe Policy Improvement with Multiple Testing**  
   Link: <https://proceedings.neurips.cc/paper_files/paper/2023/hash/b4f338c0b2f2f8f14b1ea8c13c7e4df5-Abstract-Conference.html>
3. **Confident Off-Policy Evaluation and Selection through Self-Normalized Importance Weighting**  
   Link: <https://proceedings.mlr.press/v238/thomas24a.html>
4. **Sequential Conformal Risk Control with Anytime-Valid Coverage**  
   Link: <https://openreview.net/forum?id=GqfM8LSTaj>

**这些工作共同说明**

1. 若目标是 honest promotion，就不该反复拿 public benchmark 微调；
2. 更合理的路径是：
   - 冻结候选；
   - 用 confidence bound / lower bound / multiple testing 做 promotion gate；
   - 进入 test 后不再调参；
3. 还有一种更保守的方式：
   - 不直接整支替换；
   - 只让高置信 intervention class 获得 adoption 权。

**对 `CX21-B` 的直接启发**

- `CX21-B` 不一定要先修好再进 hard-test；
- 也可以先把问题改写成：
  - “整支 frozen grammar 值不值得晋级？”
  - 或 “哪些 frozen grammar class 值得被 hard-test adopt？”

## 4. Two CX22 Tracks

## 4.1 Track I — 定向压缩 / 稳态修复

### CX22-A: `RS-LAG-SDT` — Support-Distilled Tree Grammar

**核心想法**

1. 把 `CX21-B` 的 legality grammar 蒸馏成极小 decision tree / FSC；
2. 只保留高支持特征：
   - `viability`
   - `reverse-required`
   - `trap / escape affinity`
   - `oracle_gain`
   - support count / margin
3. 叶子只输出：
   - `allowed`
   - `discouraged`
   - `forbidden`
   - `must-precede`
4. 低支持叶统一回退 accepted baseline。

**它如何直接对准 `CX21-B` 的问题**

1. 压缩在线开销；
2. 剪掉长尾不稳 rules；
3. 把 `flange` gain 保存在少量高支持叶中，而不是让整张 grammar 常驻。

**为什么文献支持这条线**

- `MSVIPER` 支持把强策略 distill 到小树；
- FSC / verifiable policy extraction 支持把控制逻辑压成小型状态机；
- maneuver automata / safe-by-design primitives 支持把 legality 变成明确动作语言。

**预期优点**

1. 最直接压 runtime；
2. 最适合做 error leaf surgery；
3. 容易解释 “哪些 leaf 保留了 `flange` gain，哪些 leaf 应被砍掉”。

**主要风险**

1. 若 `CX21-B` 的信号本身并不稀疏，蒸馏会严重掉点；
2. 过度剪枝可能把 `flange` gain 一起剪掉。

### CX22-B: `RS-LAG-DCG` — Decision-Point Conformal Grammar

**核心想法**

1. 保留 grammar 本体，但压缩它的介入域；
2. 只在高价值 decision points 让 grammar 激活；
3. hard forbid / must-precede 只有在 conformal / risk gate 通过时才允许；
4. 否则退回 `discouraged` 或 abstain。

**它如何直接对准 `CX21-B` 的问题**

1. 不是压 grammar 逻辑，而是压激活频率；
2. 直接减少 `maze / narrow_passage / parasol_misc` 上的误触发；
3. 避免 `CX11` 那种全局 defer，因为对象是 **rule strength** 而不是整支策略。

**为什么文献支持这条线**

- `DPRL` 说明 decision-point 稀疏介入有理论和实践价值；
- conformal decision rules / conformal risk training 说明“敢不敢用硬规则”可以被写成风险控制问题。

**预期优点**

1. 更有机会保住 `flange` gain；
2. 相比蒸馏，更少改变 grammar 主体；
3. runtime 下降来自“少触发”，而不是“少表达”。

**主要风险**

1. gate 过严会把 grammar 压成 tie；
2. gate 过松会继续带着负 family 一起介入。

## 4.2 Track II — 直接单独升级到 hard-test

### CX22-C: `RS-LAG-HPG` — High-Confidence Promotion Gate

**核心想法**

1. 完全冻结当前 `CX21-B`；
2. 构造一次性的 hard-test promotion gate：
   - dev/public family-wise lower confidence bound
   - negative-family penalty
   - runtime penalty
3. 只有 gate 通过，整支 `CX21-B` 才允许进 hard-test；
4. 进入后严格禁止回调调参。

**它如何直接对准当前问题**

1. 把“继续 public 追数”停止掉；
2. 强制给 `CX21-B` 一个 honest go/no-go；
3. 若失败，也能更快冻结这条线，而不是继续局部修饰。

**为什么文献支持这条线**

- `CSPI-MT`、confident OPE、sequential CRC 都强调：
  - 候选应先冻结；
  - 再用 confidence-style gate 进入 test；
  - 而不是 test 后再调。

**预期优点**

1. 最 honest；
2. protocol 最清晰；
3. 非常适合 paper-facing evidence chain。

**主要风险**

1. 它本身不修方法；
2. 可能只是更快证明 `CX21-B` 不具备 hard-test 稳定性。

### CX22-D: `RS-LAG-SHA` — Shadow Hard-Test Adoption

**核心想法**

1. 同样冻结 `CX21-B`；
2. 但在 hard-test 上不直接整支替换 accepted baseline；
3. 采用 shadow adoption：
   - baseline 仍是主 driver；
   - `CX21-B` 只在高置信 intervention class 上获准介入；
   - 介入 class 可由 dev 校准：
     - decision-point class
     - grammar leaf
     - macro family
     - LCB positive tag

**它如何直接对准当前问题**

1. 回答“`CX21-B` 的哪些 class 还能在 hard-test 上活着”；
2. 避免整支 branch 一次性把负 family 全带进去；
3. 比整支 promotion 更保守，但仍是 hard-test 直接升级。

**为什么文献支持这条线**

- safe policy improvement / confident OPE 支持只 adopt 有 lower bound 的 intervention；
- 这也是把 `CX21-B` 变成 **instance/class-specific safe adoption** 问题，而不是再训练新模型。

**预期优点**

1. 有机会保住 `flange` 核心收益；
2. 能更干净地区分“有价值的 grammar class”与“有害的 grammar class”；
3. 若成功，可为后续 `CX22-A/B` 提供更明确压缩对象。

**主要风险**

1. adoption class 太粗会继续把负项带上 hard-test；
2. adoption class 太细会退化成几乎不使用 `CX21-B`。

## 5. Recommended Order

### 主路线

1. `CX22-A / RS-LAG-SDT`
2. `CX22-B / RS-LAG-DCG`

原因：

- 先回答 `CX21-B` 是否可被压成一个更便宜、更窄、更稳的 grammar；
- 若连这一步都做不到，就没有理由继续把它当部署候选。

### 若目标是尽快判断 ceiling

1. `CX22-D / RS-LAG-SHA`
2. `CX22-C / RS-LAG-HPG`

原因：

- 先做 shadow adoption，看看高置信 class 是否能在 hard-test 上单独站住；
- 若连影子 adoption 都站不住，就没必要给整支 frozen grammar promotion gate。

## 6. Final Judgment

`CX22` 的最重要结论是：

1. `CX21-B` 还没有死，但它已经不适合继续“大而全”地扩展；
2. 下一轮最合理的组织方式就是：
   - **要么压缩它**
   - **要么冻结它并用更 honest 的方式升级到 hard-test**
3. 因而 `CX22` 应冻结为四个方案：
   - `CX22-A / RS-LAG-SDT`
   - `CX22-B / RS-LAG-DCG`
   - `CX22-C / RS-LAG-HPG`
   - `CX22-D / RS-LAG-SHA`

这四条线都建立在同一个清晰判断上：

> **`CX21-B` 的核心问题已经不是“有没有 signal”，而是“能否把 signal 压缩为可部署结构，或用 honest hard-test protocol 证明它不值得再保留”。**
