# Router Theory V3（Dual-Layer）：当前 Weighted-Search 主线 + 历史 Probe 主线

状态：`living-doc`  
版本：`v3.1-dual-layer`  
日期：`2026-03-06`

本文件现在明确分成两层：
1. **当前 strict 主线的理论抓手**：`Risk-Calibrated Single-Search Compute Shaping / Weighted-Search Tree Portfolio`；
2. **历史 V3 主线的正式定理**：多臂 portfolio、prior shift 风险证书、两阶段 probe 单调性。

这样做的原因是：
- 当前正向 strict 结论来自 `Phase29 -> Phase13 -> Phase22` 的 weighted-search 路线；
- 原有 V3 定理仍然成立，但它们不再直接支撑“probe-router 仍是当前 strict 主方法”这一说法。

当前正向结果：
- `reports/router_phase29_step12r4_trials_v1.md`
- `reports/router_phase13_sota_v10_strict_weighted_tree_o.md`
- `reports/router_phase22_direct_baselines_v10_strict_weighted_tree_o.md`

历史严格负结果：
- `reports/router_strict_audit_v2.md`
- `reports/router_validity_audit_v2.md`

协议参考：
- frozen protocol 原始定义：`docs/router_protocol_v1.md`
- 当前主线到冻结协议的映射说明：`docs/router_protocol_v1_current_mainline_note.md`
- 当前 paper-facing claim 契约：`paper/router_current_mainline_claim_contract.md`

## 当前 paper claim 契约

论文中的当前主 claim 以 `paper/router_current_mainline_claim_contract.md` 为准。
本文件负责回答：
- 当前主线有哪些理论抓手；
- 哪些定理只属于历史 probe 主线或框架层；
- 为什么这些理论不能被误写成“旧 probe-router 仍是当前主方法”的证明。

因此，当本文件与 paper-facing claim 的表述粒度不同，以 claim contract 的边界表述为准。

---

## 1. Shared setup

对任意 arm 集合 `A`、样本 `x`，以 `slow` 为 reference，定义：

- 相对质量损失
  \[
  \Delta L_{\mathrm{rel}}^{(a)}(x)=\frac{L_a(x)-L_{\texttt{slow}}(x)}{\max(L_{\texttt{slow}}(x),10^{-6})}.
  \]

- 风险事件
  \[
  Z_\pi(x)=\mathbf 1\{\pi(x)\neq \texttt{slow}\ \land\ \Delta L_{\mathrm{rel}}^{(\pi(x))}(x)>\epsilon_{\mathrm{rel}}\}.
  \]

- 联合目标
  \[
  J_\pi(x)=\frac{T_{\pi(x)}(x)}{T_{\mathrm{ref}}}+\beta\cdot\max\bigl(\Delta L_{\mathrm{rel}}^{(\pi(x))}(x),0\bigr).
  \]

冻结协议见：`docs/router_protocol_v1.md`。

重要语义提醒：在当前 repo 的 frozen protocol 中，`L` 的默认定义是 **node expansions**，path length 仅作为辅助审计量。这决定了当前 weighted-search 主线的理论解释方式：
- 它首先是在 **expansions + latency** 的联合目标下取得优势；
- 不是在“严格路径成本最优”意义下自动成立。

---

## 2. 当前 strict 主线：Weighted-Search Compute Shaping 的理论抓手

这一部分只写当前主线**真正拥有**的理论支撑，不虚构新的强定理。

### 2.1 Classical anchor: Weighted A* bounded-suboptimality

对 admissible heuristic 的 Weighted A*，经典搜索理论给出：
\[
C(\pi_w)\le w\,C^*.
\]

这不是本仓库原创定理，但它提供了当前方法最核心的理论锚点：
- `w` 越大，通常搜索更激进、扩展更少、时间更短；
- 但路径代价膨胀并非完全失控，而是受 `w` 限制。

在本仓库里的对应关系：
- 算法实现：`scripts/evaluate_baselines.py:_astar_grid`
- weighted arm 反事实表：`scripts/run_router_phase29_step12r4_trials_v1.py:_build_weight_tables`
- 路径审计输出：`reports/router_phase29_step12r4_trials_v1.md`

### 2.2 Structural honesty: zero-probe latency semantics

当前主线不是
\[
T_{\mathrm{total}}=T_{\pi(x)}+T_{\mathrm{probe}},
\]
而是
\[
T_{\mathrm{total}}=T_{w(x)}.
\]

这不是一个深刻定理，而是一个**关键的结构性质**：
- 额外 compute 不再来自外部 probe；
- 所有开销都体现在主搜索本身；
- 因而 strict 记账没有“外置模块加法项”可低估。

这正是当前路线能绕开旧 probe-router 结构性瓶颈的主要原因。

### 2.3 Deployable selector: tree partition over weighted arms

当前 deployable 策略 `O / TreeWeightPortfolio` 可写成：
\[
\pi_O(x)=a_{\ell(x)},\qquad \ell(x)=\text{Tree}(\phi_{\text{static}}(x),\phi_{\text{fastgeom}}(x),d(x)).
\]

这里并没有声称一个新的“树策略 regret 定理”；当前可诚实主张的是：
- 该选择器只在 `calib_train/calib_val` 上拟合与筛选；
- `test` 只做一次最终评估；
- 因而它满足 strict 反泄露协议。

对应代码：
- `scripts/run_router_phase29_step12r4_trials_v1.py:_run_tree_portfolio`
- `scripts/run_router_phase29_step12r4_trials_v1.py:_build_feature_matrices`
- `scripts/run_router_phase29_step12r4_trials_v1.py:_save_weighted_policy_seed`

### 2.4 What the current theory does **not** prove

当前主线没有一个新的严格定理可以直接推出：
\[
J_{\text{weighted tree}} < J_{\text{P5 or CRC/CDT}}
\]
在所有分布上都成立。

当前这部分仍然是**经验结论**，其可信度来自：
- frozen protocol,
- strict split,
- sha256 input binding,
- downstream reproducibility,
- and cross-benchmark consistency.

也就是说：
- 当前主线的“强点”是**结构更 honest + 经验结果更强**；
- 不是“我们已经为 `TreeWeightPortfolio` 证明了新的 distribution-free superiority theorem”。

---

## 3. 历史 V3 正式定理（仍然成立，但主要服务于历史主线 / 框架层）

完整证明仍见：`docs/router_theory_v3_appendix.md`。

### Theorem 1：K 臂 Oracle-regret 的有限样本上界（可验证）

对任意固定策略 `pi`，定义单样本 regret：
\[
R(x)=J_\pi(x)-\min_{a\in\mathcal A}J_a(x)\in[0,M].
\]

在 i.i.d. / 可交换样本下，可用经验 Bernstein 型不等式给出 `E[R]` 的高置信上界，并在脚本中输出 slack。

### Theorem 2：分组 prior-shift 下的多臂风险鲁棒证书（可验证）

若部署仅发生组先验变化、组内条件分布保持不变，则：
\[
V_p(\pi)\le \sum_{g\in\mathcal G} p_g u_g.
\]

这里 `u_g` 是校准集上每组的风险上界。

### Theorem 3：两阶段 Probe 只升级到更慢臂，则风险不增

若 probe 阶段只允许：
- `fast -> mid/slow`
- `mid -> slow`

则：
\[
V(\pi_{\mathrm{probe}})\le V(\pi_{\mathrm{static}}).
\]

这一定理在逻辑上仍然完全正确，但它只说明**风险单调性**，不说明 `J` 一定改善。

---

## 4. 哪些理论支持当前主线，哪些主要支持历史主线

### 4.1 当前主线直接依赖的理论锚点

- Weighted A* bounded-suboptimality（经典搜索理论）
- zero-probe latency honesty（结构性质）
- strict split + hash-bound artifacts（协议性质）

### 4.2 历史主线 / 框架层仍然重要的理论资产

- Theorem 1：portfolio regret 上界
- Theorem 2：prior-shift 风险证书
- Theorem 3：probe monotone safety

这些仍然重要，因为它们说明本仓库不是“纯工程堆叠”；但它们现在更适合：
- 作为框架层理论背景；
- 或作为历史 probe-router 线为何“风险有保证但 `J` 不再成立”的解释。

---

## 5. 与脚本 / 产物的对应关系

### 当前主线
- Phase29 结构搜索：`scripts/run_router_phase29_step12r4_trials_v1.py`
- 当前主结果：`outputs/router_phase29_step12r4_trials_v1/summary.json`
- strongest-baseline 对齐：`outputs/router_phase13_sota_v10_strict_weighted_tree_o/stats.json`
- direct-baseline 对齐：`outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json`

### 历史 / 框架层验证
- 定理验证脚本：`scripts/run_router_phase24_theory_v3.py`
- 附录证明：`docs/router_theory_v3_appendix.md`
- probe-router 严格负结果：`reports/router_strict_audit_v2.md`

---

## 6. 必须写在论文里的限制

1. **指标语义限制**：当前 frozen protocol 的主质量代理 `L` 是 expansions，不是纯 path cost。
2. **当前正增益的主要来源**：来自 weighted-search arm family 本身；树选择器相对常数权重只提供很小的附加收益。
3. **Phase22 解释限制**：当前 parity 模式是 `weighted_search_slow_fallback_cap`；在最优策略中该 cap 为 `0`，所以 CRC/CDT 在该 parity 下退化为 `P5`。
4. **历史定理不等于当前主结论**：probe monotone safety、prior-shift 证书、portfolio regret 上界，并不能单独推出当前 weighted-search strict 主结论。
5. **经验结论的适用域**：当前正结论应限定为“在 frozen strict protocol 与当前 public benchmarks 上”。

---

## 7. 一句话理论定位

最诚实的一句话写法是：

> 当前 router 主线的理论基础是“经典 Weighted A* 的可解释 compute–quality tradeoff + zero-probe honest accounting + strict calibration-only model selection”，而原 V3 的 probe monotonicity / prior-shift / regret 定理则保留为框架层与历史主线的正式理论资产。
