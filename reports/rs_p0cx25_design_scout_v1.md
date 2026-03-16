# P0-CX25 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-14`

## 1. Executive Summary

`CX24-E + CX24-D` 已经把当前 repair 路线推进到一个更清楚的位置：

1. `CX24-E` 补齐了 automaton 的 observability plane；
2. `CX24-D` 证明 counterfactual commit certificate 的确能修掉 `maze`；
3. 但 `CX24-D` 也明显过于保守，直接砍掉了 `flange` 的主收益；
4. `parasol_misc` 仍未被真正修复。

因此 `CX25` 的问题不应再写成“再调证书 margin”，而应写成：

> **如何把 `CX24-D` 从 global hard veto 证书升级成 selective + soft + calibrated + tail-aware + observable 的证书系统。**

本轮冻结 5 条方案：

1. `CX25-A / RS-SSC`
2. `CX25-B / RS-DTO`
3. `CX25-C / RS-CLR`
4. `CX25-D / RS-TSD`
5. `CX25-E / RS-GSC`

## 2. Problem Diagnosis

### 2.1 `maze`

`CX24-D` 已经说明：

- counterfactual certificate 可以修掉 `maze`；
- 说明问题不是 “maze 完全不可分”；
- 而是当前证书触发和处置方式过硬，导致 head positive signal 一起被杀。

### 2.2 `flange`

`CX24-D` 从 `+1428.4` 掉到 `+218.0` 说明：

- 当前 certificate 不是只在真正危险段工作；
- 它在很多本来应当放行的高收益段也被触发了。

### 2.3 `parasol_misc`

`CX24-B` 没能改善 `parasol_misc`，说明：

- tail problem 不是简单 support gate 能解决的；
- 需要更温和、只削顶不归零的控制形式。

### 2.4 `ATO` 的意义

`CX24-E` 目前还只是日志；
下一轮必须把它变成 policy 可消费的证据对象。

## 3. Literature Sweep by Issue

### 3.1 Selective / Soft Certificate

1. **Selective Classification for Deep Neural Networks**  
   Link: https://proceedings.mlr.press/v97/geifman19a.html
2. **Selective Prediction with Conformal Guarantees**  
   Link: https://proceedings.mlr.press/v152/luo21a.html
3. **Decision Point RL**  
   Link: https://arxiv.org/abs/2110.04555

**启发**

1. 强约束不应全局常驻；
2. selective trigger 和 graded action 比 hard veto 更适合保住 head positive signal。

### 3.2 Diagnostics → Policy

1. **Introspective Planning**  
   Link: https://proceedings.neurips.cc/paper_files/paper/2024/file/8451a20c5a7e0ee5671dda28f7daf7f3-Paper-Conference.pdf
2. **Execution Trace Debugging**  
   Link: https://www.sciencedirect.com/science/article/abs/pii/S0167642324000406

**启发**

1. observability 若不编译成 control-facing object，就只是日志；
2. 需要 diagnostic compiler 把 trace 变成可行动的 risk signal。

### 3.3 Calibrated Local Review

1. **Conformal Decision Rules for Efficient Optimization Under Uncertainty**  
   Link: https://proceedings.mlr.press/v235/lu24f.html
2. **Counterfactual Explanations as Plans**  
   Link: https://arxiv.org/abs/2502.09205
3. **Counterfactual Scenarios for Automated Planning**  
   Link: https://arxiv.org/abs/2508.21521

**启发**

1. local review 更适合比较少量相关候选；
2. “margin 足够大才放行”比 binary win/lose 更适合校准。

### 3.4 Tail-only Downgrade

1. **Introspective Planning**
   Link: https://proceedings.neurips.cc/paper_files/paper/2024/file/8451a20c5a7e0ee5671dda28f7daf7f3-Paper-Conference.pdf
2. **Conformal Prediction Meets Long-tail Classification**  
   Link: https://arxiv.org/abs/2508.11345

**启发**

1. tail problems 更适合 risk capping 而不是 full abstention；
2. “只降级不否决”更有机会保住 head families。

### 3.5 Group-stable Objective

1. **Distributionally Robust Neural Networks for Group Shifts**  
   Link: https://openreview.net/pdf?id=ryxGuJrFvS
2. **On the Foundation of Distributionally Robust RL**  
   Link: https://arxiv.org/abs/2404.10645

**启发**

1. 若目标是 across-family 稳态，必须把 worst-group penalty 前置；
2. 只看平均 gain 会继续偏向 `flange` 这类高收益 family。

## 4. Frozen `CX25` Plans

### CX25-A: `RS-SSC` — Selective Soft Certificate

把 `CX24-D` 从 global hard veto 升级成：

1. risk detector 先判断当前是否高风险被骗段；
2. 只有高风险段才触发 certificate；
3. 证书不过时做 soft downgrade，而不是直接禁用。

### CX25-B: `RS-DTO` — Diagnostic-to-Operation Compiler

把 `CX24-E` 的 trace / transition / false-commit ledger 编译成 control-facing 中间件，供证书、review 与 tail downgrade 统一调用。

### CX25-C: `RS-CLR` — Calibrated Local Review

把 `CCC` 依赖的 local review 从 binary veto 改成 margin-based certificate，并用 `ATO` 的成功/误触发样本做可复现校准。

### CX25-D: `RS-TSD` — Tail Soft Downgrade

对 tail / low-support / high-churn states，不做 hard gate，而只降低 commit 强度与持续时间。

### CX25-E: `RS-GSC` — Group-Stable Certificate

把 certificate system 的设计目标改成：

1. average gain
2. worst-group penalty
3. tail-risk penalty

的联合目标，而不是只靠单 family ceiling。

## 5. Recommended Order

1. `CX25-B / RS-DTO`
2. `CX25-A / RS-SSC`
3. `CX25-C / RS-CLR`
4. `CX25-D / RS-TSD`
5. `CX25-E / RS-GSC`

## 6. Final Judgment

围绕 `CX24-E + CX24-D` 的下一步，不应再是调 margin，而应把证书系统升级成：

1. selective
2. soft
3. calibrated
4. tail-aware
5. diagnosable

这 5 条线分别对应当前 5 个明确问题，也都能被单独陈述为方法对象。
