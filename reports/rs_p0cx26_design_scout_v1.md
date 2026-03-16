# P0-CX26 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-14`

## 1. Executive Summary

`CX24-E + CX24-D` 与 `CX25-B` 已经把问题缩得非常明确：

1. `CX24-D` 证明 certificate 能修 `maze`；
2. 但它也会严重误杀 `flange`；
3. `CX24-E`/`CX25-B` 证明我们终于有了足够细的 automaton diagnostics；
4. `CX25-A/C/D/E` 又说明：如果只是换一个 gate 或阈值，几乎都会退化成 “仍然修 maze，但救不回 flange，也压不住 misc”。

因此 `CX26` 的问题不该再写成“哪种 gate 更好”，而该写成：

> **如何以 `RS-DTO` 为底座，把证书系统重写成 risk-hotspot selective trigger + monotone graded intervention + correct tail definition compiler。**

本轮冻结三条方案：

1. `CX26-A / RS-HST`
2. `CX26-B / RS-MGI`
3. `CX26-C / RS-TDC`

## 2. Root-Cause Diagnosis

### 2.1 为什么 `flange` 会被误杀

从 `CX24-D` 与 `CX25-A/C/E` 的共同结果看：

1. `maze` 一旦被修好，`flange` 会大幅掉点；
2. 这说明证书并不是“分辨对错”，而是在很多 high-gain flange 段也被调用了；
3. 换句话说：
   - **根因首先是调用范围错了**
   - 其次才是证书动作太硬。

### 2.2 为什么 `CLR / SSC` 仍然没用

`CX25-A/C` 的结果几乎与 `CCC` 同级，说明：

1. 证书即便改成 selective / calibrated 的名字，
2. 只要底层仍然是“全局都可能触发，且动作强度缺乏稳定映射”，
3. 最终还是会回到 hard-veto-like behavior。

### 2.3 为什么 `parasol_misc` 一直修不好

`CX25-D` 失败说明：

1. `parasol_misc` 并不是单纯“低支持样本”；
2. 它更像：
   - high churn
   - oscillation
   - local proxy disagreement
   - sibling inconsistency
3. 也就是：

> **tail 必须先被定义成“结构性不一致状态”，而不是样本数稀少状态。**

## 3. Literature Sweep

### 3.1 Selective Trigger / Event-Scoped Review

1. **Selective Classification for Deep Neural Networks**  
   Link: https://proceedings.mlr.press/v97/geifman19a.html
2. **Selective Prediction with Conformal Guarantees**  
   Link: https://proceedings.mlr.press/v152/luo21a.html
3. **Decision Point Reinforcement Learning**  
   Link: https://arxiv.org/abs/2110.04555
4. **Introspective Planning**  
   Link: https://proceedings.neurips.cc/paper_files/paper/2024/file/8451a20c5a7e0ee5671dda28f7daf7f3-Paper-Conference.pdf

**启发**

1. 强约束不应 everywhere 常驻；
2. 真正有效的是：
   - 先找出高风险点；
   - 再在这些点做强干预；
3. 若不先收缩调用范围，再好的证书也会误伤 head positives。

### 3.2 Graded / Calibrated Intervention

1. **Conformal Decision Rules for Efficient Optimization Under Uncertainty**  
   Link: https://proceedings.mlr.press/v235/lu24f.html
2. **Selective Prediction with Conformal Guarantees**  
   Link: https://proceedings.mlr.press/v152/luo21a.html
3. **Counterfactual Explanations as Plans**  
   Link: https://arxiv.org/abs/2502.09205

**启发**

1. binary pass/fail 常常过于粗糙；
2. 更好的做法是：
   - 用 margin / risk score 表示信心；
   - 再把动作强度写成该分数的单调函数。

### 3.3 Tail Definition / Long-tail Risk

1. **Introspective Planning**  
   Link: https://proceedings.neurips.cc/paper_files/paper/2024/file/8451a20c5a7e0ee5671dda28f7daf7f3-Paper-Conference.pdf
2. **Conformal Prediction Meets Long-tail Classification**  
   Link: https://arxiv.org/abs/2508.11345
3. **Do Not Trust Overconfident Predictions in Long-Tailed Recognition**  
   Link: https://openaccess.thecvf.com/content/CVPR2024/papers/Tian_Do_Not_Trust_Overconfident_Predictions_in_Out-of-Distribution_Generalized_Long-Tailed_Recognition_CVPR_2024_paper.pdf

**启发**

1. tail risk 不该只由 support count 定义；
2. high uncertainty + disagreement + instability 更像真正的 tail hazard；
3. 这和 `parasol_misc` 的现象高度一致。

## 4. Frozen `CX26` Plans

## 4.1 Assessment of Additional Proposed Requirements

针对本轮补充评估，结论是：

1. **DTO 接口契约必须补充**；
2. **HST 的共同成立逻辑必须补充为定量 gate**；
3. **MGI 必须显式防“伪单调”**；
4. **TDC 必须显式防退化成 generic OOD detector**；
5. **这些补充都不需要单独再开新方案**。

原因是：

- 它们都不是新的算法对象；
- 它们是现有 `CX26-A/B/C` 要想可验收、可复现、可被诚实陈述所必须具备的 **实现契约**。

因此，本轮的合理处理方式是：

1. 把 `DTO interface contract` 作为 `CX26` 共享前置条件；
2. 把 `HST` 的定量触发逻辑直接并入 `CX26-A`；
3. 把 `MGI` 的单标量干预强度约束直接并入 `CX26-B`；
4. 把 `TDC` 的 tail-scope 与 tail-feature 约束直接并入 `CX26-C`。

### 4.1.1 `RS-DTO` 接口是否要补？

结论：**必须补，而且不应作为新方案，而应作为共享验收契约。**

如果不补，`HST` 会稳定退化成：

- 若干 feature 相加；
- 超阈则触发；
- 结果仍然是“换名字的阈值调参”。

因此后续 `DTO` 的最小 schema 至少应固定为：

1. `occupancy_hotspot_score`
2. `transition_hotspot_score`
3. `false_commit_ledger_hit`
4. `churn_score`
5. `commit_recover_loop_score`
6. `local_proxy_disagreement`
7. `sibling_inconsistency`
8. `tail_uncertainty`

同时要固定：

1. `W_short / W_mid / W_long` 三档时间窗；
2. 全部证据归一化到 `[0,1]`；
3. per-state / per-transition / per-episode 三层输出。

### 4.1.2 `HST` 的“共同成立”是否要补？

结论：**必须补，而且应直接并入 `CX26-A`。**

推荐形式不是开放式 score mixing，而是：

**分层 gate**

1. gate-1：`{occupancy hotspot, transition hotspot, false_commit_ledger}` 至少命中一项；
2. gate-2：动态风险分数  
   `S = w1·churn + w2·commit_recover_loop + w3·proxy_disagreement + w4·sibling_inconsistency`
   超阈，且 `{churn, loop, disagreement}` 至少 `2-of-3` 成立；
3. gate-3：episode review/intervene budget 未耗尽。

如果没有预算约束，`maze` 很可能会被高频干预“拉平”，但 `flange` 误杀仍会继续发生。

### 4.1.3 `MGI` 的“伪单调”是否要补？

结论：**必须补，而且应直接并入 `CX26-B`。**

如果继续让以下动作通道分别调节：

1. TTL
2. sibling priority
3. soft-commit
4. fallback

那即便每个通道单独看是单调的，叠加后整体策略也很容易不再单调。

因此更稳的做法是：

1. 先定义单一 **干预强度标量** `z∈[0,1]`；
2. 再把 `z` 单调映射到各动作通道。

这会显著减少自由度，也是让 “monotone graded intervention” 变成真命题的必要条件。

### 4.1.4 `TDC` 的 tail 是否要补？

结论：**必须补，而且应直接并入 `CX26-C`。**

如果 tail 被实现成：

- rare
- low support
- generic OOD

那么它极可能重新扩散到 head families，最终又把整个系统压回保守 tie。

因此 `TDC` 必须把 tail 定义成：

1. churn / oscillation
2. `commit→recover` loop
3. local proxy disagreement
4. sibling inconsistency
5. tail uncertainty

并且要显式写明：

> `TDC` 只用于 `parasol_misc` / tail-risk 削顶，不得向 head families 全局扩散。

### CX26-A: `RS-HST` — Hotspot-Scoped Trigger

**解决问题**

- 证书调用范围过宽，导致 `flange` 误杀。

**核心想法**

以 `RS-DTO` 为底座，只在以下强证据段触发证书：

1. occupancy hotspot
2. transition hotspot
3. false-commit ledger hit
4. churn / oscillation trigger

非高风险段一律不调用证书。

**补充后的实现契约**

1. 采用 **分层 gate**，不是自由组合阈值：
   - gate-1：`occupancy / transition / ledger` 至少一项命中；
   - gate-2：动态风险分数超阈，且 `churn / loop / disagreement` 至少 `2-of-3` 成立；
   - gate-3：`B_review / B_intervene` 预算未耗尽。
2. 必须显式报告：
   - per-episode trigger 频率
   - budget 消耗率
   - 各 family 的 trigger 覆盖分布。

**创新点**

把 DTO 从 passive evidence layer 升级为 **trigger compiler**。

### CX26-B: `RS-MGI` — Monotone Graded Intervention

**解决问题**

- hard veto 过强，`CLR/SSC` 又没有真正 graded 化。

**核心想法**

将风险 / margin 分数映射为单调动作强度：

1. commit TTL
2. sibling priority
3. soft-commit strength
4. fallback timing

不再只输出 yes/no certificate。

**补充后的实现契约**

1. 不允许多个动作通道各自独立标定；
2. 必须先定义单一干预强度 `z∈[0,1]`；
3. 再由 `z` 单调映射到：
   - TTL
   - sibling priority
   - soft-commit strength
   - fallback timing。

**创新点**

把证书变成 **连续控制律**，而不是离散 gate。

### CX26-C: `RS-TDC` — Tail Definition Compiler

**解决问题**

- `parasol_misc` 的 tail 没定义对。

**核心想法**

先编译 tail definition：

1. churn
2. commit→recover loop
3. local proxy disagreement
4. sibling inconsistency
5. tail uncertainty

只有被这个 compiler 判定为 tail-risk，才做 soft downgrade。

**补充后的实现契约**

1. tail feature family 必须优先是 **结构性不一致**，而不是 rarity / generic OOD；
2. 必须显式限定作用域：
   - 只对 `parasol_misc` / tail-risk 削顶；
   - 不得对 head families 做全局降级。

**创新点**

把 tail 从“少样本”升级为 **结构性不一致状态**。

## 5. Recommended Order

1. `CX26-A / RS-HST`
2. `CX26-B / RS-MGI`
3. `CX26-C / RS-TDC`

## 6. Final Judgment

`CX26` 的核心结论是：

1. 下一轮不该再平铺更多 gate；
2. 应先把证书的 **作用域** 修对；
3. 再把证书的 **动作强度** 做成可校准单调函数；
4. 最后再把 `parasol_misc` 的 tail 定义做对。

也就是说，后续最合理的结构路线是：

> **DTO first, trigger second, grading third, tail last.**
