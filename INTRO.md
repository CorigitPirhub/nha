# Risk-Calibrated Compute Shaping（Weighted-Search Tree Portfolio）— strict 主线 INTRO

修改日期：2026-03-17

> 本仓库包含多条研究主线；**当前 strict 语义下可成立的 Router 主叙事**，已经从早期的 **Dual-Path Probe Router**，切换为 **Risk-Calibrated Single-Search Compute Shaping / Weighted-Search Tree Portfolio**。
> 
> 也就是说：
> - 旧的 `P5 -> P6` probe-router 线仍保留在仓库里，作为**历史主线 / 理论背景 / 负结果审计对象**；
> - 当前真正通过 `Phase29 -> Phase13 -> Phase22` 全链路 strict 验证的，是 **零-probe、单搜索内部 compute-shaping** 的 `O / TreeWeightPortfolio`；
> - 因而本文档以下所有“当前主方法 / 当前主结论 / 当前 strict 口径”均以 `Phase29/13/22` 的新产物为准，而不是以旧 probe-router 的 v5 strict bundle 为准。
> - `Step 14` 的后继方法筛查现已完成四轮 strict `calib_train/calib_val` 验证：`A/B/C/D` 见 `reports/router_phase30_step14_trials_v1.md`，`E/F/G/H` 见 `reports/router_phase31_step14_fresh_trials_v1.md`，沿 `14-F` 主线继续推进的 TARP-line 变体见 `reports/router_phase32_step14_tarp_line_v1.md`（最强定向 follow-up 见 `reports/router_phase32_step14_tarp_line_f2b_hgb_v1.md`），最终 `RCWS-B` 冲刺见 `reports/router_phase33_step14_rcwsb_trials_v1.md`（高容量 follow-up 见 `reports/router_phase33_step14_rcwsb_b1_followup_v1.md`）；四轮都没有候选强到足以替换 `O / TreeWeightPortfolio`。
> - 当前更高优先级的下一阶段工作仍是 `P0-CX`：在 `RS` 根基之上，通过**基础模型层面**的创新去建立显著优势区间；截至 `2026-03-19`，paper-facing accepted `RS` 主线仍保持为 `RS + CX34-A / Subtype-Specific Macro Rescue`。该主线的 public canonical artifact 见 `reports/rs_p0cx34_round1_summary.md`，full-support audit 见 `reports/rs_p0cx34_standard_audit_v1.md`，复核审计见 `reports/rs_p0cx34_recheck_audit_v1.md`；frozen hard-test eval `reports/rs_p0cx34_a_hard_eval_v1.md` 在 `rs_root_hard_v2/test` 上相对 `CX3-D` 取得 `success_delta_pp = +2.740`、`exp_delta = +196.548`，但仍伴随高 runtime overhead 与若干 hard-family 负项。
> - 当前最强的**融合主线候选**仍是 `RS + CX34-A + CX42-B / Query Compatibility Release`，但其证据边界已更新：统一 public 对齐复现实验 `reports/rs_p0cx42_public_compare_v1.md` 显示它相对 `CX34-A` 仅为 `success / exp` 持平且平均 runtime 略慢（`mean_time_overhead_ratio = +0.010346`），因此 public 升级尚未被确认；目前真正稳固的正证据来自 frozen `rs_root_hard_v2`，其在保持 `success / exp / path` 完全不变的前提下把 runtime 再下降约 `29.0%`。因此这条线当前应视为 hard-runtime fusion candidate，而不是已冻结主结论。
>
> 术语约定：
> - **arm / 臂**：可选的计算动作/规划器配置。当前主线中，arm 不是“额外 probe 模块”，而是同一 A* 主搜索内部的不同启发权重，例如 `fast`, `wa_w125`, `wa_w135`, `slow`。
> - **counterfactual table（反事实表）**：每个样本同时记录各 arm 的离线结果，例如 `L_a`, `T_a`。
> - **strict（严格协议）**：所有模型选择/阈值搜索/结构搜索仅在 `calib_train/calib_val` 上进行，`test` 仅做一次性最终评估，且产物用 sha256 绑定输入 parquet。

## 0. 入口与最顶层文件

### 0.1 当前主线首先看什么
- `README.md`：仓库入口；已经同步为当前 strict 主方法的顶层叙事。
- `TASK.md`：任务书与当前状态总账；其中 Step12-R4 记录了从旧 probe-router 失败证据转向 weighted-search compute-shaping 的全过程。
- `reports/router_phase29_step12r4_trials_v1.md`：Phase29 筛选报告，说明 `M/N/O/P` 四个 weighted-search 候选的 strict 结果。
- `reports/router_phase13_sota_v10_strict_weighted_tree_o.md`：当前主方法 `O` 的 strongest-baseline 对齐结果。
- `reports/router_phase22_direct_baselines_v10_strict_weighted_tree_o.md`：当前主方法 `O` 的 direct-baseline 对齐结果。

### 0.2 协议 / 代码 / 产物的最顶层入口
- 冻结协议：`docs/router_protocol_v1.md`
- 当前主线的协议映射说明：`docs/router_protocol_v1_current_mainline_note.md`
- 当前 paper-facing claim 契约：`paper/router_current_mainline_claim_contract.md`
- 统一 schema / 指标函数：`utils/router_method_core.py`
- 当前主方法脚本：`scripts/run_router_phase29_step12r4_trials_v1.py`
- 当前主结论下游脚本：`scripts/run_router_phase13_sota.py`、`scripts/run_router_phase22_direct_baselines.py`
- 当前 strict 源数据根：`outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak`
- 当前主方法核心输出：
  - `outputs/router_phase29_o_tree_weight_v1/`
  - `outputs/router_phase13_sota_v10_strict_weighted_tree_o/`
  - `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/`
- 旧 probe-router 的 strict 失败审计：
  - `reports/router_strict_audit_v2.md`
  - `reports/router_validity_audit_v2.md`
  - `outputs/final_v5_strict/manifest.json`

### 0.3 当前 paper claim 与评测契约（Step 13）
- 当前 paper-facing 主句冻结在：`paper/router_current_mainline_claim_contract.md`。
- 当前唯一允许的主方法表述是：**Risk-Calibrated Single-Search Compute Shaping**，其当前实现是 `O / TreeWeightPortfolio`。
- 当前主结论的适用域仅限于：Protocol V1 strict semantics、`L = expansions` 为主质量代理、`path-length` 仅作辅助审计、以及当前 public strict benchmarks（`csm/mp/parasol`）。
- 当前必须显式保留的非 claim：
  - 旧 probe-router claim 未被 strict 审计“救回”；
  - 当前结果不是一般路径最优性的证明；
  - `Phase22` 不再是旧 `fast -> slow` parity。

---

# 主线 1：当前模型设计是怎样的，理论抓手有哪些

## 1.1 冻结问题定义：所有方法共用的 RBAC 目标

对于每个样本 `x` 与 arm `a`，反事实表给出：
- 时间：`T_a(x)`
- 质量代理：`L_a(x)`
- 参考臂：`slow`

统一相对损失定义为：
\[
q_{\mathrm{rel},a}(x)=\frac{L_a(x)-L_{\texttt{slow}}(x)}{\max(L_{\texttt{slow}}(x),10^{-6})}.
\]

冻结风险事件：
\[
Z_a(x)=\mathbf 1\left\{q_{\mathrm{rel},a}(x)>\epsilon_{\mathrm{rel}}\right\},
\qquad \epsilon_{\mathrm{rel}}=0.015.
\]

冻结目标函数：
\[
J_a(x)=\frac{T_a(x)}{T_{\mathrm{ref}}}+\beta\,\max\bigl(q_{\mathrm{rel},a}(x),0\bigr).
\]

其中：
- `T_ref` 与 `beta` 由 `calib_train` 从数据中拟合；
- 所有 strict 比较都使用同一 `epsilon_rel=0.015`、`alpha=0.05`、bootstrap `10000` 的协议。

代码落点：
- 协议常量：`utils/router_method_core.py:RiskBudgetProtocol`
- schema 与派生量：`utils/router_method_core.py:{CounterfactualSchema,derive_q_rel_and_c}`
- 当前主线中的 `T_ref/beta` 标定：`scripts/run_router_phase29_step12r4_trials_v1.py:_objective_from_calib_train`
- 当前主线中的 arm 级指标汇总：`scripts/run_router_phase29_step12r4_trials_v1.py:_selection_metrics`

## 1.2 当前主方法：零-probe 的 Weighted-Search Tree Portfolio（O）

### 1.2.1 设计动机：把“路由”改写成同一搜索内部的 compute-shaping

旧的 dual-path probe-router 结构是：
1. 先跑静态 router / conformal router；
2. 再跑一个额外 probe 或额外模型；
3. 再决定是否从 `fast` 升级到 `slow`。

strict 审计后，问题暴露得很明确：
- `route-only` 增益几乎为 0；
- 额外的 `probe / model` 开销是**加法项**，会直接吞掉增益；
- 因而旧主结论不再能在 honest strict 口径下成立。

当前主方法的改写是：
- **不再引入外部 probe**；
- 保持同一 A* 主搜索骨架；
- 只改变启发权重 `w(x)`，把“路由”变成“单搜索内部的计算预算分配”。

因此，新增计算不会以 `+ T_probe` 的形式出现，而是直接体现在一次搜索本身的 `T_a(x)` 上。

### 1.2.2 arm 空间：同一 A* 主骨架上的多权重族

Phase29 的 arm 集合来自：
\[
\mathcal A_{\mathrm{ws}}=\{\texttt{fast}\}\cup\{\texttt{wa\_w105},\texttt{wa\_w110},\ldots,\texttt{wa\_w135}\},
\]
`P` 方案再额外允许 `slow` 作为 fallback。

对应的搜索打分函数是 Weighted A*：
\[
f_w(n)=g(n)+w\,h(n),\qquad w\ge 1.
\]

实现落点：
- A* / Weighted A* 核心：`scripts/evaluate_baselines.py:_astar_grid`
- weighted arm 反事实表生成：`scripts/run_router_phase29_step12r4_trials_v1.py:_build_weight_tables`
- 产物：
  - `outputs/router_phase29_step12r4_trials_v1/common/router_counterfactual_calib_wastar.parquet`
  - `outputs/router_phase29_step12r4_trials_v1/common/router_counterfactual_test_wastar.parquet`

### 1.2.3 选择器：浅层树分区 + 叶子级 arm 选择

当前最优方案 `O / TreeWeightPortfolio` 不是“再叠一个外部网络模块”，而是一个**轻量、可部署、可解释**的 partitioned selector：

1. 先构造特征：
   - 静态 geometry / occupancy 特征：`STATIC_BASE_COLS`
   - fast path 几何特征：`FASTGEOM_COLS`
   - difficulty 分组
2. 用浅层树对样本空间分区；
3. 在每个叶子上，从候选 arm 集合里选择在 `calib_val` 上最优且通过风险/路径审计 gate 的 arm；
4. 在 `test` 上仅执行“查叶子 -> 取 arm”。

代码落点：
- fastgeom 特征生成：`scripts/run_router_phase29_step12r4_trials_v1.py:_make_fastgeom_tables`
- fastgeom 底层实现：`utils/router_fastgeom.py:build_fastgeom_features`
- 训练/搜索树分区：`scripts/run_router_phase29_step12r4_trials_v1.py:_run_tree_portfolio`
- 统一特征矩阵构造：`scripts/run_router_phase29_step12r4_trials_v1.py:_build_feature_matrices`
- 每 seed 决策落盘：`scripts/run_router_phase29_step12r4_trials_v1.py:_save_weighted_policy_seed`

最终决策形式可以写成：
\[
\pi_O(x)=a_{\ell(x)},\qquad \ell(x)=\text{Tree}\bigl(\phi_{\text{static}}(x),\phi_{\text{fastgeom}}(x),d(x)\bigr).
\]

其中：
- `\ell(x)` 是样本落入的树叶；
- `a_\ell` 是该叶子绑定的 weighted-search arm。

### 1.2.4 当前已落地的 deployable 形式

当前最优 `O` 的 per-seed 决策文件在：
- `outputs/router_phase29_o_tree_weight_v1/seeds/seed_*/test_decisions.parquet`
- `outputs/router_phase29_o_tree_weight_v1/seeds/seed_*/policy_metrics.json`

其关键实现特征：
- 输出字段不再是“是否 `use_fast`”的二元布尔，而是 `route_arm`；
- `scripts/run_router_phase13_sota.py` 与 `scripts/run_router_phase22_direct_baselines.py` 现已支持直接读取 `route_arm`；
- 下游会根据 `route_arm` 映射到相应的 `T_a/L_a` 列来计算统一的 `J` 与 `V`。

新接入点：
- `scripts/run_router_phase13_sota.py:{_resolve_policy_time_length,_compute_probe_overhead_ms}`
- `scripts/run_router_phase22_direct_baselines.py:{_resolve_policy_time_length,_compute_probe_overhead_ms,_weighted_slow_budget_check}`

### 1.2.5 当前实际学到的策略是什么

在真实 strict 结果里，`O` 与 `P` 完全一致：
- 实际出现的 `route_arm` 只有 `{wa_w125, wa_w135}`；
- `slow` fallback 实际使用次数为 `0`；
- 因而当前主方案应收敛到更简单的 `O / TreeWeightPortfolio`。

这点可以直接在下列产物中验证：
- `outputs/router_phase29_o_tree_weight_v1/seeds/seed_*/test_decisions.parquet`
- `outputs/router_phase29_p_tree_weight_slow_v1/seeds/seed_*/test_decisions.parquet`
- `reports/router_phase29_step12r4_trials_v1.md`

## 1.3 当前主方法的理论抓手是什么

### 1.3.1 Weighted A* 的经典 bounded-suboptimality

若启发函数 `h` admissible，则 Weighted A* 给出经典形式：
\[
C(\pi_w)\le w\,C^*.
\]

这不是本仓库新造的定理，但它为当前主方法提供了关键理论抓手：
- 随着 `w` 增大，搜索通常更快；
- 但路径代价的膨胀有可解释的上界结构；
- 因而“速度提升 vs 质量退化”不是黑箱关系，而是有已知搜索理论支撑的 tradeoff。

在本仓库里，这个理论抓手通过两层证据落地：
1. `route_arm -> T_a/L_a` 的真实反事实表；
2. 额外路径审计：限制 `mean path_rel_vs_slow <= 1%`、`p95 <= 5%`。

对应产物：
- `reports/router_phase29_step12r4_trials_v1.md`
- `outputs/router_phase29_step12r4_trials_v1/summary.json`

### 1.3.2 为什么这条线比旧 probe-router 更“honest”

旧线的问题是多出一个外部模块，其开销可以在不同记账口径下被低估或遮蔽；
当前线没有这个自由度：
- `T_a` 就是这一次 weighted A* 真正的搜索时间；
- `J_a` 直接由统一反事实表计算；
- 下游 `Phase13/22` 只是重新聚合 `route_arm` 选择后的 `T_a/L_a`，不再存在“probe 额外记账模式”导致的解释歧义。

这也是为什么当前主结论可以在 strict 语义下恢复，而旧主结论不能。

### 1.3.3 旧 dual-path 理论现在处于什么位置

旧理论并没有“消失”，但其角色已变化：
- `docs/router_theory_v3.md` / `docs/router_theory_v3_appendix.md` 里的 prior-shift / portfolio / monotone-upgrade 内容，仍然是仓库的重要理论资产；
- 但 **Theorem 3（probe 只升级到更慢臂不增风险）** 现在主要服务于“历史主线为何风险上可控、但 `J` 上不再成立”的解释；
- 它不应再被写成当前 strict 主方法的核心贡献。

因此，当前论文叙事应区分：
- **当前主贡献**：zero-probe weighted-search compute-shaping + tree portfolio；
- **历史背景 / 对照线**：dual-path probe router 与其 monotone safety 分析。

## 1.4 当前主结论与旧主结论的关系

一句话概括：
- **旧主结论**：`P6 probe router` 在 strict 下显著优于 `P5` —— 该结论不成立；
- **新主结论**：`O / TreeWeightPortfolio` 在 strict 下显著优于 strongest same-protocol baseline 与 matched direct baselines —— 该结论成立。

因此，仓库中与 router 相关的代码可以分成两类：
- **当前主线**：`scripts/run_router_phase29_step12r4_trials_v1.py` + `Phase13/22` 的 `route_arm` 接入；
- **历史/对照线**：`scripts/run_router_phase8_strict.py`、`docs/router_theory_v3*.md`、`reports/router_strict_audit_v2.md`。

---

# 主线 2：当前 strict 口径、数据集、基线与实验分别在验证什么

## 2.1 为什么当前必须使用 strict 口径

当前所有主结论都必须建立在同一个 frozen strict protocol 上：
- 选择 / 搜索 / 结构选择：只允许用 `calib_train/calib_val`
- `test`：只做一次最终评估
- 所有 skip/cache/复用 产物：用 sha256 绑定输入 parquet
- 统一 `epsilon_rel=0.015`、`alpha=0.05`、bootstrap `10000`

代码落点：
- calib 内部分割：`scripts/run_router_phase8_strict.py:_split_calib_train_val`
- 输入绑定：`utils/parquet_guard.py`
- 下游写入 hash：`scripts/run_router_phase13_sota.py`、`scripts/run_router_phase22_direct_baselines.py`

## 2.2 当前主结论使用的数据集是什么

当前 strict 主结论使用的统一数据根是：
- `data/router_phase9_public_v1`
- 对应 strict 源产物根：`outputs/router_phase9_bench_v7_strict_alpha05_probeT_noleak`

该数据在下游表现为 3 个 public benchmarks：
- `csm`
- `mp`
- `parasol`

对应统计可在：
- `outputs/router_phase13_sota_v10_strict_weighted_tree_o/stats.json`
- `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json`
中看到 `public_benchmarks = 3` 与各 benchmark 的 `delta_j_mean`。

## 2.3 当前比较了哪些基线，各自验证什么

### A. strongest same-protocol baseline（Phase13）

`Phase13` 固定把 strongest same-protocol baseline 设为：
- `conformal_strict_v2`

它验证的问题是：
- 在**同协议、同数据、同 strict 审计约束**下，我们是否真的优于最强的 in-repo paper-valid baseline？

对应脚本与产物：
- 脚本：`scripts/run_router_phase13_sota.py`
- 输出：`outputs/router_phase13_sota_v10_strict_weighted_tree_o/`

### B. 其他 in-repo baselines（Phase13 汇总）

`Phase13` 同时汇总：
- `risk_v1`
- `current_v2`
- `default_router`
- `all_fast`
- `all_slow`

它们分别验证：
- 静态风险路由是否足够；
- 现有工程默认策略是否已足够；
- “永远快 / 永远慢”是否就已经覆盖最优区域。

### C. direct baselines（Phase22）

`Phase22` 对齐的 direct baselines 是：
- `crc_static_pupper_v1`
- `cdt_worstcase_j_v1`

它们验证的问题是：
- 我们的方法是否只是“可以被直接的 cost-sensitive / conformal ranking 方法解释完”？

当前严格结果的诚实答案是：
- 在 weighted-search 的 zero-probe budget semantics 下，`O` 依然显著优于它们；
- 但因为最优 `O` 根本没用到 `slow` fallback，`Phase22` 中的 parity cap 实际为 `0`，于是 CRC/CDT 退化为与 `P5` 等价的策略。

所以 `Phase22` 支撑的是：
- **旧 probe-router 不是唯一解释**；
- **当前 zero-probe weighted-search tree portfolio 也不能被现有 CRC/CDT 直接替代**；
而不是“CRC/CDT 本身在当前预算下也非常强”。

### D. Step12-R4 内部消融 / 方案池（Phase29）

当前还做了四类内部候选比较：
- `M / WAStarConst`：固定单一权重
- `N / DifficultyWeightPortfolio`：按 difficulty 三桶选权重
- `O / TreeWeightPortfolio`：浅层树分区选权重（当前最佳）
- `P / TreeWeightSlowFallback`：`O` + 可选 `slow` fallback

它们验证的问题是：
- 仅靠固定权重是否已经够用？
- 是否真的需要可部署的 partitioned selector？
- slow fallback 是否真的有必要？

当前答案：
- `O` 略优于 `M/N`；
- `P` 与 `O` 完全一致，因为 `slow` 从未被使用；
- 因而最佳叙事是：**树分区的 weighted-search selector 是当前最简洁且最强的 strict 主方法**。

## 2.4 当前关键实验链路分别在验证什么

### Phase29：当前主方法的结构搜索与消融

脚本：`scripts/run_router_phase29_step12r4_trials_v1.py`

它验证：
- 在 strict 约束下，零-probe weighted-search family 是否能绕开“route-only≈0 + probe 开销主导”的结构性问题；
- `M/N/O/P` 哪个是最佳 deployable 方案；
- 路径审计是否仍然通过。

当前结论：
- `O/P` 最优且并列；
- `P` 没有真正使用 `slow`，所以主方案收敛到 `O`。

### Phase13：对 strongest same-protocol baseline 的主比较

脚本：`scripts/run_router_phase13_sota.py`

当前主产物：`outputs/router_phase13_sota_v10_strict_weighted_tree_o/stats.json`

它回答：
- 我们相对 strongest same-protocol baseline（固定为 `conformal_strict_v2`）是否显著更好？

当前 strict 结果：
- `j_improve_vs_strongest_baseline_mean = 0.9976992728000766`
- pooled ΔJ 95% CI = `[0.9663033544282551, 1.02944877581246]`
- 风险差值均值 = `-3.281541330018645 pct`
- gate 全部通过

也就是说：
- 当前主方法不仅更快，而且 `V` 更低；
- 且 `csm/mp/parasol` 三个 benchmark 的方向全部一致。

### Phase22：对 direct baselines 的解释力检验

脚本：`scripts/run_router_phase22_direct_baselines.py`

当前主产物：`outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json`

它回答：
- 现有直接方法（CRC/CDT）是否已经能解释掉我们的优势？

当前 strict 结果：
- best direct baseline = `cdt_worstcase_j_v1`
- `j_improve_vs_best_direct_mean = 99.76992728000766`
- pooled ΔJ 95% CI = `[0.9667465807411415, 1.0293682886138211]`
- `main_result_significant = True`
- 但 `best_direct_vs_p5_significant_p_lt_0_01 = False`

这说明：
- `O` 显著优于 direct baselines；
- 但 direct baselines 在当前 zero-probe parity 下并没有形成一个比 `P5` 更强的竞争者。

### Legacy strict audit：为什么旧 probe-router 不能再作为主 claim

旧严格审计产物：
- `reports/router_strict_audit_v2.md`
- `reports/router_validity_audit_v2.md`
- `outputs/final_v5_strict/manifest.json`

它们现在的角色不是“当前主结论来源”，而是：
- 解释为什么必须从外部 probe 切换到内部 compute-shaping；
- 为当前论文叙事提供一条完整、诚实、可追溯的 negative-to-positive 研究路径。

---

# 主线 3：模型设计与实验结论如何逐层对应

## 3.1 设计层 → 代码层 → 实验层 对照表

| 设计对象 | 代码实现 | 产物 / 实验验证 |
|---|---|---|
| 冻结协议 `epsilon_rel`, `alpha`, `J`, `V` | `docs/router_protocol_v1.md`；`utils/router_method_core.py` | `Phase29/13/22` 的 `stats.json` 与报告 |
| weighted arm 反事实表 `T_w/L_w` | `scripts/evaluate_baselines.py:_astar_grid`；`scripts/run_router_phase29_step12r4_trials_v1.py:_build_weight_tables` | `outputs/router_phase29_step12r4_trials_v1/common/router_counterfactual_{calib,test}_wastar.parquet` |
| fastgeom 辅助特征 | `utils/router_fastgeom.py:build_fastgeom_features`；`scripts/run_router_phase29_step12r4_trials_v1.py:_make_fastgeom_tables` | `outputs/router_phase29_step12r4_trials_v1/common/fastgeom_features_{calib,test}.parquet` |
| 树分区选择器 `pi_O(x)=a_{ell(x)}` | `scripts/run_router_phase29_step12r4_trials_v1.py:{_build_feature_matrices,_run_tree_portfolio}` | `outputs/router_phase29_o_tree_weight_v1/seeds/seed_*/test_decisions.parquet` |
| per-seed deployable policy | `scripts/run_router_phase29_step12r4_trials_v1.py:_save_weighted_policy_seed` | `outputs/router_phase29_o_tree_weight_v1/seeds/seed_*/policy_metrics.json` |
| `route_arm -> T_a/L_a` 的统一下游评估 | `scripts/run_router_phase13_sota.py:{_resolve_policy_time_length,_eval_policy}`；`scripts/run_router_phase22_direct_baselines.py:{_resolve_policy_time_length,_eval_policy}` | `outputs/router_phase13_sota_v10_strict_weighted_tree_o/stats.json`；`outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json` |
| weighted-search 的 honest budget parity | `scripts/run_router_phase22_direct_baselines.py:_weighted_slow_budget_check` | `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/tables/budget_caps.csv` |
| 历史 dual-path line（对照 / 负结果审计） | `scripts/run_router_phase8_strict.py`；`docs/router_theory_v3*.md` | `reports/router_strict_audit_v2.md`；`outputs/final_v5_strict/manifest.json` |

## 3.2 从最顶层入口一路走到最底层公式的实际链路

1. 入口叙事：`README.md`
2. 当前方法总账：`TASK.md`（看 Step12-R4）
3. 当前方法筛选：`scripts/run_router_phase29_step12r4_trials_v1.py`
   - 生成 weighted-search 反事实表
   - 生成 fastgeom 特征
   - 在 `calib_train/calib_val` 上比较 `M/N/O/P`
   - 产出 `O/P` 的 per-seed `route_arm`
4. strongest-baseline 对齐：`scripts/run_router_phase13_sota.py`
   - 读取 `route_arm`
   - 映射回 `T_a/L_a`
   - 统一计算 `J/V`
5. direct-baseline 对齐：`scripts/run_router_phase22_direct_baselines.py`
   - 同样读取 `route_arm`
   - 用 honest weighted-search parity 做 CRC/CDT 比较
6. 如果要解释“为什么旧方法不再是主 claim”，再回到：
   - `reports/router_strict_audit_v2.md`
   - `reports/router_validity_audit_v2.md`

## 3.3 当前单一引用点：写论文时到底该引用哪些产物

如果论文要写**当前 strict 主结论**，优先引用：
- `reports/router_phase29_step12r4_trials_v1.md`
- `outputs/router_phase13_sota_v10_strict_weighted_tree_o/stats.json`
- `outputs/router_phase22_direct_baselines_v10_strict_weighted_tree_o/stats.json`
- `TASK.md`（Step12-R4 的阶段性结论与 caveat）

如果论文要解释**为什么旧 probe-router 叙事被放弃**，再补充引用：
- `reports/router_strict_audit_v2.md`
- `reports/router_validity_audit_v2.md`

---

## 附：当前一句话版本的论文主叙事

当前 router 论文最稳妥、与代码/实验一致的一句话主叙事应写成：

> 我们提出一种 **Risk-Calibrated Compute Shaping** 框架：在冻结 strict 协议下，不再通过额外 probe 做样本级 `fast -> slow` 路由，而是在**同一 Weighted A* 主搜索内部**选择 `w(x)`，并用一个浅层树把 `static + fastgeom + difficulty` 映射到 deployable 的多预算搜索臂；该方法在 `Phase29 -> Phase13 -> Phase22` 的全链路 strict 验证中显著优于 strongest same-protocol baseline 与 matched direct baselines。
