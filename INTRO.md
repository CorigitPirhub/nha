# Dual-Path Router（Fast / Mid / Slow）— C2D-RBAC 主线 INTRO

修改日期：2026-03-05

> 本仓库包含多条研究主线；当前 NeurIPS/ICML 级投稿主线为 **Dual-Path Router（Fast/Mid/Slow）**（入口 `README.md`）。
> 本文档聚焦 Router 主线：按“模型设计与理论 → 评测口径与实验 → 二者逐层对应”的顺序，
> 从最顶层设计文件/实验入口一路拆到最底层代码函数与输出产物，确保可审计、可复现、可对齐论文叙述。
>
> 术语约定：
> - **arm / 臂**：可选的计算动作/规划器配置（本 repo 默认 `fast/slow`，扩展到 `fast/mid/slow`）。
> - **counterfactual table（反事实表）**：离线表格，每个样本同时包含各 arm 的 `T`（时延）与 `L`（质量代理）。
> - **strict（严格协议）**：所有“选择/搜索/调参”只在 `calib_train/calib_val` 上完成；`test` 仅用于一次性最终评估。

## 0. 入口与“最顶层文件”

### 0.1 设计/协议/理论（从上到下）
- `README.md`：主线入口与一键复现入口（V2/V3 bundle）
- `docs/router_protocol_v1.md`：冻结评测口径（\(\epsilon_{\text{rel}}=0.015\)、\(\alpha=0.05\)、bootstrap=10000、主 claim 判定）
- `docs/neurips_method_v1.md`：论文式方法叙述（RBAC / C2D-RBAC、两阶段 router、与相关工作的对齐点）
- `docs/router_theory_v3.md` + `docs/router_theory_v3_appendix.md`：可验证理论（多臂 portfolio、prior shift 风险证书、两阶段 probe 单调性）
- `TASK.md`：任务书 + strict 审计状态（主结论以 strict 产物为准）

### 0.2 实验/产物（从上到下）
- 一键复现（方法线 V3）：`artifacts/router_camera_ready_v3/reproduce_main_tables_figures.sh`
- strict 主链路总控：`scripts/run_router_phase27_strict_audit_v1.py:main`
- strict 终局打包（hash 可追溯）：`outputs/final_v4_strict/manifest.json`
- strict 审计报告（单一真相源）：`reports/router_strict_audit_v1.md`

---

# 主线 1：模型设计是怎样的 + 理论推导有哪些（逐层拆解到文件/函数）

本主线回答两件事：
1) Router 在“问题定义/目标/约束”上到底是什么；  
2) 静态路由（P5）与 probe 升级（P6）为何不是纯工程拼装：它们的**可写公式**、**可证明性质**与**可验证脚本**分别在哪里。

## 1.1 问题定义：Risk-Bounded Adaptive Computation（RBAC）

对每个规划查询/样本 \(x\)，我们在 arm 集合 \(\mathcal A\) 中选择一个动作：
\[
\pi(x)\in\mathcal A.
\]

### 观测量（由反事实表提供）
对每个 arm \(a\in\mathcal A\)，有：
- 时延（ms）：\(T_a(x)\)
- 质量代理（默认 expansions）：\(L_a(x)\)

在双臂（fast/slow）时，以 slow 为 reference 定义相对质量损失：
\[
\Delta L_{\text{rel}}(x)=\frac{L_{\texttt{fast}}(x)-L_{\texttt{slow}}(x)}{\max(L_{\texttt{slow}}(x),10^{-6})}.
\]

在多臂（fast/mid/slow）时，对任意 \(a\neq \texttt{slow}\)：
\[
\Delta L_{\text{rel}}^{(a)}(x)=\frac{L_{a}(x)-L_{\texttt{slow}}(x)}{\max(L_{\texttt{slow}}(x),10^{-6})}.
\]

代码落点：
- 协议常量（\(\epsilon_{\text{rel}},\alpha\)）：`utils/router_method_core.py:RiskBudgetProtocol`
- 表字段命名：`utils/router_method_core.py:CounterfactualSchema`
- `q_rel/c` 推导：`utils/router_method_core.py:derive_q_rel_and_c`

### 风险事件（冻结协议）
冻结阈值 \(\epsilon_{\text{rel}}\)（默认 1.5%），定义 violation 指示变量（双臂）：
\[
Z_\pi(x)=\mathbf 1\{\pi(x)=\texttt{fast}\land \Delta L_{\text{rel}}(x)>\epsilon_{\text{rel}}\},
\qquad
V(\pi)=\mathbb E[Z_\pi].
\]
目标约束：\(V(\pi)\le \alpha\)（默认 \(\alpha=0.05\)）。

协议落点：`docs/router_protocol_v1.md`  
统一计算口径（含 Wilson CI）：`utils/router_method_core.py:router_metrics`、`utils/router_method_core.py:wilson_ci95`

### 目标函数（时延-质量折中）
冻结口径使用“归一化时延 + 质量惩罚”：
\[
J_\pi(x)=\frac{T_{\pi(x)}(x)}{T_{\text{ref}}}+\beta\cdot\max(\Delta L_{\text{rel}}^{(\pi(x))}(x),0).
\]
目标：\(\min_\pi \mathbb E[J_\pi(x)]\) s.t. \(V(\pi)\le\alpha\)。

代码落点（\(T_{\text{ref}},\beta\) 的选取保持一致）：
- 双臂 strict（P6）：`scripts/run_router_phase8_strict.py:_run_probe_seed`（`t_ref`、`beta` 计算；`_j_gain_signed`/`_j_gain_pos`）
- 多臂（K=3）：`scripts/run_router_phase23_portfolio_v1.py:_calibrate_beta`（与 `scripts/run_router_risk_v1.py:_calibrate_beta` 同构）
- 通用指标计算：`utils/router_method_core.py:router_metrics`

---

## 1.2 C2D-RBAC：为什么反事实表是“方法而非工程”

Router 不是把一个系统堆起来，而是把“离线可学习/可证书/可消融”的对象固定成一张表：
\[
\big(T_{\texttt{fast}}(x),L_{\texttt{fast}}(x),T_{\texttt{slow}}(x),L_{\texttt{slow}}(x)\big),
\]
并辅以特征 \(\phi(x)\)（静态）与 \(\psi(x)\)（probe）。

本 repo 的反事实表由 `scripts/run_router_counterfactual.py:main` 生成，关键字段：
- `L_fast/L_slow`：A* 扩展节点数（默认质量代理）
- `T_fast_ms/T_slow_ms`：对应总时延（slow 额外包含 `infer_slow_ms`）
- `q_rel = (L_fast - L_slow)/L_slow`、`c = T_slow_ms - T_fast_ms`

实现落点：
- 反事实生成：`scripts/run_router_counterfactual.py:main`
  - fast：`scripts/evaluate_baselines.py:_astar_grid(..., heuristic_map=None)`
  - slow：`network/inference.py:NeuralHeuristicPredictor.predict_field` → `scripts/evaluate_baselines.py:_resolve_2d_heuristic` → `_astar_grid(..., heuristic_map=h_slow)`

这一步把“部署时只能二选一的 compute 决策问题”变成：**在冻结指标下学习 \(\pi\) 的离线监督/校准问题**，从而允许：
- 严格的 split（避免 test 泄露）
- 可审计的 policy artifact（hash 绑定）
- 可复现的统计显著性与消融对齐

---

## 1.3 两阶段 Router：P5 静态 conformal → P6 probe 只升级（fast→slow）

论文式 framing 见 `docs/neurips_method_v1.md`；这里把公式落到实际实现。

### Stage-1（P5）：静态 Conformal Cost-Aware Routing

**目标**：只用 \(\phi(x)\)（便宜静态特征）学习一个“风险/代价比”分数，并按组阈值路由。

1) 风险标签（在 fast 下是否违反）：
\[
y(x)=\mathbf 1\{\Delta L_{\text{rel}}(x)>\epsilon_{\text{rel}}\}.
\]
2) 拟合分类器给出 \(\hat p(x)\approx \mathbb P(y=1\mid \phi(x))\)。
3) 组内（difficulty）一侧 split conformal 上界：
\[
s_i=\max(y_i-\hat p_i,0),\quad
q_d=\mathrm{Quantile}_{\lceil (n_d+1)(1-\alpha_c)\rceil/n_d}(s;\ \texttt{higher}),
\]
\[
\hat p^{\text{up}}(x)=\mathrm{clip}(\hat p(x)+q_{d(x)},0,1).
\]
4) 拟合代价差预测 \(\hat c(x)\approx \mathbb E[T_{\texttt{slow}}-T_{\texttt{fast}}\mid \phi(x)]\)，归一化 \( \hat c_{\text{norm}}=\hat c/\mathrm{median}(\hat c)\)。
5) 评分（risk-per-compute）：
\[
u(x)=\frac{(\hat p^{\text{up}}(x))^a}{(\hat c_{\text{norm}}(x))^b}.
\]
6) 组内阈值路由：
\[
\pi_{P5}(x)=\texttt{fast}\ \text{iff}\ u(x)\le \tau_{d(x)};\ \text{else slow}.
\]

代码落点（strict 实现为准）：
- 训练/选择/落盘：`scripts/run_router_phase8_strict.py:_run_conformal_seed`
  - 构造特征：`scripts/run_router_phase8_strict.py:_build_conformal_xy`
  - split conformal 偏移：`scripts/run_router_phase8_strict.py:_split_conformal_offsets`（对应上式 \(q_d\)）
  - 阈值/预算选择：`scripts/run_router_phase8_strict.py:_apply_k_by_diff` + `_conformal_metric_from_k`（用 Wilson CI 上界约束）
- 产物（兼容命名）：每个 seed 在
  `outputs/*/router_eval/seeds/seed_*/mixed/conformal_strict_v2/{policy_metrics.json,calib_decisions.parquet,test_decisions.parquet}`。

方法抽象（轻量 API，用于 Phase21 最小 demo/复用）：
- `utils/router_method_core.py:ConformalStageRouter`
- split conformal 工具：`utils/router_method_core.py:split_conformal_upper_q`

### Stage-2（P6）：Probe Flip-to-Slow（严格只允许 fast→slow）

**动机**：静态 \(\phi(x)\) 可能无法捕捉“局部搜索早期就能观测到的难例征兆”，因此引入一个**受预算约束的 probe**，抽取 \(\psi(x)\) 并只做“升级到更慢臂”的翻转。

#### Probe 特征 \(\psi(x)\)：一次受限 A* 小跑得到的搜索形态
probe 特征由 `scripts/run_router_probe_v1.py:_build_probe_features` 计算（strict 阶段复用同一实现）：
- 例如 `probe_expansions/probe_runtime_ms/probe_h_drop_ratio/probe_bottleneck_rate/...`

strict 脚本复用关系（保证“probe 定义”不随 recovery 改变）：
- `scripts/run_router_phase8_strict.py` 顶部 `from scripts.run_router_probe_v1 import _build_probe_features`

#### 关键优化量：signed J-gain
对每个样本定义（使用同一 \(T_{\text{ref}},\beta\)）：
\[
g(x)=J_{\texttt{fast}}(x)-J_{\texttt{slow}}(x).
\]
当 \(g(x)>0\) 时，切到 slow 会降低 \(J\)（尽管更慢，但质量惩罚更少）。

代码落点：
- `scripts/run_router_phase8_strict.py:_run_probe_seed`
  - `def _j_gain_signed(df)` 直接实现 \(g(x)\)

#### LCB + 预算选择：`knapsack_lcb`（strict recovery 的 paper-valid 版本）
为避免“在 strict 审计下依赖大量超参 sweep”带来的不稳定，我们在 strict 主链路使用**一侧 split-conformal 的 LCB**：
1) 在 selection split（strict 下为 `calib_val`）计算残差：
\[
r_i=\hat g(x_i)-g(x_i).
\]
2) 组内量化得到 \(q^{\text{res}}_d\)（higher quantile）：
\[
q^{\text{res}}_d=\mathrm{Quantile}_{\lceil (n_d+1)(1-\alpha)\rceil/n_d}(r;\ \texttt{higher}).
\]
3) 得到一侧 LCB：
\[
\mathrm{LCB}(x)=\hat g(x)-q^{\text{res}}_{d(x)}.
\]
4) 在平均额外时延预算 \(B\) 下做贪心 knapsack（按 \(\mathrm{LCB}/c\) 排序）选择要 flip 的子集：
\[
\max_{S\subseteq \{x:\pi_{P5}(x)=\texttt{fast}\}}\ \sum_{x\in S}\mathrm{LCB}(x)
\quad\text{s.t.}\quad
\sum_{x\in S} c(x)\le B\cdot n.
\]

代码落点（逐行可对照）：
- `scripts/run_router_phase8_strict.py:_run_probe_seed`
  - LCB 计算：`probe_sel_mode == "knapsack_lcb"` 分支（`resid`→`q_by_diff`→`lcb_search`）
  - 贪心 knapsack：`score_search = lcb_search / c_search` + 预算累计选择
  - 将选中集合折算成 `k_by_diff`，再用 `_apply_probe_k_by_diff` 作为“可部署的 top-k-by-score”规则
- 输出版本标识写在 `policy_metrics.json`：
  - `version: "probe_strict_v4_knapsack_lcb"`
  - 兼容目录名仍为 `probe_strict_v2/`（Phase9/13/22 下游脚本固定读取该目录名）

方法抽象（轻量 API）：
- `utils/router_method_core.py:ProbeFlipRouter`（核心约束：只 flip fast→slow）

---

## 1.4 关键可证明性质（并且脚本可验证）

### Theorem 3：两阶段“只升级到更慢臂”不会增加风险
若 probe 只允许升级（fast→slow，或多臂时 fast→mid/slow、mid→slow），则逐点有：
\[
Z_{\pi_{\text{probe}}}(x)\le Z_{\pi_{\text{static}}}(x)\quad \forall x
\quad\Rightarrow\quad
V(\pi_{\text{probe}})\le V(\pi_{\text{static}}).
\]

证明与完整表述：
- `docs/router_theory_v3.md`（Theorem 3 摘要）
- `docs/router_theory_v3_appendix.md`（Theorem 3：Assumptions/Statement/Proof）

脚本验证（把“理论”变成“产物”）：
- `scripts/run_router_phase24_theory_v3.py:main`
  - 输出 `outputs/router_phase24_theory_v3/probe_monotone.csv`

### Theorem 2：prior shift（仅先验偏移）下的分组风险证书
若只发生分组先验变化（组内条件分布不变），则：
\[
V_p(\pi)=\sum_{g\in\mathcal G} p_g v_g\le \sum_{g\in\mathcal G} p_g u_g,
\]
其中 \(u_g\) 取校准集上每组的风险上界（实现中使用 Wilson CI 上界，与冻结协议一致）。

落点：
- 理论：`docs/router_theory_v3_appendix.md`（Theorem 2）
- 逐组 Wilson CI：`utils/router_method_core.py:wilson_ci95`（Phase24 直接复用）
- 验证脚本：`scripts/run_router_phase24_theory_v3.py:main` 输出 `outputs/router_phase24_theory_v3/shift_bounds.csv`

### Theorem 1：Portfolio（K≥3）相对 oracle 的 regret 上界（可验证）
对任意固定策略 \(\pi\)，单样本 regret：
\[
R(x)=J_\pi(x)-\min_{a\in\mathcal A}J_a(x)\in[0,M].
\]
经验 Bernstein 上界（见理论文档）用于给出 \(\mathbb E[R]\) 的高置信上界，并报告 slack。

落点：
- 理论：`docs/router_theory_v3_appendix.md`（Theorem 1）
- 上界计算：`scripts/run_router_phase24_theory_v3.py:_empirical_bernstein_upper`
- 验证产物：`outputs/router_phase24_theory_v3/seed_checks.csv`

---

## 1.5 多臂/多预算（Portfolio）在代码里对应什么

当 \(\mathcal A=\{\texttt{fast},\texttt{mid},\texttt{slow}\}\) 时，“臂”就是**三种可选计算动作/规划器配置**。本 repo 的 Phase23 以 slow 为 reference，扩展相对损失与风险事件到非 slow 的 arm：
- fast/mid 任何一个被选中，只要其相对损失超过 \(\epsilon_{\text{rel}}\) 即计 violation；
- 仍使用冻结的 \(J\) 定义做折中；
- 通过 split conformal + Wilson gate 在 calib 上选择阈值，使得风险满足预算（并保留 safety margin）。

实现入口：
- `scripts/run_router_phase23_portfolio_v1.py:main`
  - 多臂指标缓存：`scripts/run_router_phase23_portfolio_v1.py:_prep_k3_cache`
  - 多臂策略评估：`scripts/run_router_phase23_portfolio_v1.py:_policy_metrics_k3`
  - split conformal：`utils/router_method_core.py:split_conformal_upper_q`

---

# 主线 2：当前用什么口径/标准、什么数据集、对比哪些基线、做哪些消融（逐层拆解到产物）

本主线回答：
1) “当前结论”是在什么冻结口径下成立的，为什么要这样做；  
2) 数据集与 split 是什么；  
3) baseline/ablation 各自验证什么；  
4) strict 审计链路如何确保优势不是数据泄露/缓存命中造成的假象。

## 2.1 冻结口径（Protocol V1）：指标 + 显著性 + 允许的主 claim

冻结协议：`docs/router_protocol_v1.md`（Freeze date: 2026-03-02）

核心指标：
- \( \Delta L_{\text{rel}} \)（slow 为 reference）
- violation 概率 \(V(\pi)=\mathbb E[Z_\pi]\)，阈值 \(\epsilon_{\text{rel}}=0.015\)，预算 \(\alpha=0.05\)
- 目标 \(J = T/T_{\text{ref}} + \beta\cdot \max(\Delta L_{\text{rel}},0)\)

为什么用这套口径（不是随意挑指标）：
- 用 **\(\Delta L_{\text{rel}}\)** 而不是绝对差值：把不同场景尺度归一化，避免某些大图/长路径主导统计量。
- 用 **risk budget \(V(\pi)\le\alpha\)**：控制“坏例比例”（尾部风险），避免仅优化均值导致少数难例严重退化。
- 质量代理默认用 **expansions**：在 `scripts/run_router_counterfactual.py:main` 中对 fast/slow 都可稳定记录；协议允许在 expansions 不可用时回退到路径代价代理（见 `docs/router_protocol_v1.md`）。

统计检验（主 claim 必须同时满足）：
- paired bootstrap（`N=10000`）
- Wilcoxon signed-rank（paired）
- `p < 0.01` 且 `95% CI` 不跨 0（按 improvement 方向）

代码落点（严格执行）：
- Phase9：`scripts/run_router_phase9_bench.py:_bootstrap_ci`、`_bootstrap_p_gt0`、`scipy.stats.wilcoxon`
- Phase13/22：各自脚本内同构的 bootstrap/Wilcoxon 汇总逻辑（见对应 `stats.json`）

## 2.2 strict 协议（防泄露）：calib 内部切分 + test 一次性评估 + sha256 绑定

### strict 核心规则
- 选择/搜索/调参：只在 `calib_train/calib_val` 上做  
- `test`：只做一次最终评估（产物写盘，严禁反复调参）

代码落点：
- calib 内部切分：`scripts/run_router_phase8_strict.py:_split_calib_train_val`（`--calib-split-mode train_val`）
- 选择 split 绑定：`scripts/run_router_phase8_strict.py:_run_conformal_seed`（`--conformal-select-on calib`）与 `_run_probe_seed`（`--probe-search-on calib`）

### sha256 输入绑定（覆盖即强制重跑，避免缓存误导）
为避免“下游 skip/cache 复用命中旧结果”，关键阶段在输出目录写入 `inputs_parquet_sha256.json`：
- 写入/校验工具：`utils/parquet_guard.py:{write_record,compare_record,mismatch_summary}`
- Phase9 总控在检测到输入 parquet 被覆盖时自动 `--force` 全量重跑：
  - `scripts/run_router_phase9_bench.py:main`（`compare_record(...)`）

## 2.3 数据集：router_mixed_v1（门控）与 router_phase9_public_v1（跨基准）

### A) `router_mixed_v1`（协议门控用的混合难度集）
- 构建脚本：`scripts/build_router_mixed_dataset.py:main`
- manifest：`data/router_mixed_v1/manifest.json`
- 特点：`test=900` 且 `easy/medium/hard` 各 `300`，并保证 `OOD ratio >= 30%`（CSM 作为 OOD family）
- 用途：Phase7（系统/证据包）与早期门控（Protocol 数据集约束的落地）

### B) `router_phase9_public_v1`（Phase9/13/22 主结论的 public cross-benchmark 集）
- 构建脚本：`scripts/build_router_phase9_dataset.py:main`
- manifest：`data/router_phase9_public_v1/manifest.json`
- 规模（当前 repo 快照）：
  - `calib=1800`（mp=1500,csm=300）
  - `test=3218`（mp=2300,csm=900,parasol=18）
  - OOD family：由 `--ood-map-ids` 指定 map_id + `parasol` 全部标为 OOD（见构建脚本 `_is_ood`）
- 用途：
  - Phase9：跨数据源泛化（mp/csm/parasol），并要求 per-benchmark direction consistent
  - Phase13：与外部强基线做统一口径的对齐汇总
  - Phase22：与 CRC/CDT 等“直接方法”做公平对齐，回答“差距到底来自哪里”

## 2.4 对比基线（Baselines）分别在验证什么

### 同协议/同数据的 in-repo baselines（Phase13 汇总）
落点：`scripts/run_router_phase13_sota.py` 内 `policies = {...}`，对应：
- `conformal_strict_v2`：P5 静态 conformal 路由（我们的 stage-1；也是 strongest same-protocol baseline）
- `ours_probe_strict_v2`：P6 两阶段 router（P5 + probe flip）
- `risk_v1`：`scripts/run_router_risk_v1.py` 训练出的风险约束 baseline（更偏“直接拟合 q_pos/c”）
- `current_v2` / `default_router`：系统内已有的 dual-path 规则路由（从静态特征直接判 fast/slow）
- `all_fast` / `all_slow`：两个 sanity baselines（分别对应极端的“全省算力/全保质量”）

Phase13 的评测口径落点（把 `policies` 变成 `J/V/OG` 等指标）：
- `scripts/run_router_phase13_sota.py:_eval_policy`（对齐 frozen \(J,V\) 语义，seed 级与 pooled 级显著性）

这些 baselines 的作用是把贡献拆开：
- P5 vs P6：probe 是否带来额外收益（不是“静态分数+阈值”就能解释）
- vs `current_v2/default_router`：是否超越已有系统经验规则（不是“阈值工程”）
- vs `risk_v1`：是否超越“只学静态风险/代价模型”的直接方法

### 相关工作对齐（Phase22：CRC/CDT 直接基线）
落点：`scripts/run_router_phase22_direct_baselines.py`
- `crc_static_pupper_v1`（CRC family）：用静态 \(p^{up}\) 直接做风险控制路由
- `cdt_worstcase_j_v1`（CDT family）：用 conformal worst-case \(J\)（或其代理）做决策

Phase22 的“直接方法”训练与落点（便于逐层审计）：
- `scripts/run_router_phase22_direct_baselines.py:_train_crc_static_pupper_v1`
- `scripts/run_router_phase22_direct_baselines.py:_train_cdt_worstcase_j_v1`

目的不是“再加两个工程 baseline”，而是回答论文质疑点：
> 我们的提升是否能被 CDT/CRC 这类顶会方向的直接方法完全解释？

## 2.5 关键实验链路（Phase9→13→22→24→27）在验证什么

### Phase9：跨基准泛化 + P6 相对 P5 的显著增益
总控脚本：`scripts/run_router_phase9_bench.py:main`

链路（从顶层到下游）：
1) 构建数据集：`scripts/build_router_phase9_dataset.py:main`
2) 生成反事实表：`scripts/run_router_counterfactual.py:main`（calib/test 两张 parquet）
3) 构建静态特征 + 系统 baseline 决策：`scripts/run_router_risk_v1.py`（输出 `features_*.parquet`、`test_decisions.parquet`）
4) strict P5/P6 训练与落盘：`scripts/run_router_phase8_strict.py:main`
5) 统计与 gate：`scripts/run_router_phase9_bench.py:_compute_benchmark_metrics` + bootstrap/Wilcoxon

主验证点：
- 在 strict 下，P6 相对 P5 的 pooled ΔJ \(>0\) 且显著（并要求 per-benchmark 方向一致）

主要产物：
- `outputs/router_phase9_bench_v6_strict_knapsack/stats.json`
- `reports/router_phase9_bench_v6_strict_knapsack.md`

### Phase13：SOTA 汇总（同协议 strongest baseline + 外部强基线）
脚本：`scripts/run_router_phase13_sota.py:main`

主验证点：
- 我们相对 strongest same-protocol baseline（固定为 `conformal_strict_v2`）的 \(J\) 提升达标且显著
- 风险不更差（`risk_delta` 约束）
- 外部强基线数量达标（`external_strong_baselines_ge_6`）

产物：
- `outputs/router_phase13_sota_v4_strict_knapsack/stats.json`
- `reports/router_phase13_sota_v4_strict_knapsack.md`
- `paper/tables_router_v11_strict_knapsack/table_phase13_external_sota_summary.csv`

### Phase22：对齐 CDT/CRC（回答“是不是被直接方法解释完了”）
脚本：`scripts/run_router_phase22_direct_baselines.py:main`

主验证点：
- 在同协议/同预算下，我们相对 best direct baseline（当前为 `cdt_worstcase_j_v1`）仍有显著优势

产物：
- `outputs/router_phase22_direct_baselines_v4_strict_knapsack/stats.json`
- `reports/router_phase22_direct_baselines_v4_strict_knapsack.md`

### Phase24：理论可验证性（不是写在纸面上的“空保证”）
脚本：`scripts/run_router_phase24_theory_v3.py:main`
- 读取 Phase23 决策产物与 Phase9 P5/P6 决策产物
- 输出 regret bound、prior-shift bound、probe 单调性检查表

产物：
- `reports/router_phase24_theory_v3.md`
- `outputs/router_phase24_theory_v3/{seed_checks.csv,shift_bounds.csv,probe_monotone.csv}`

### Phase27：strict 审计（strict vs legacy 诊断 A/B + final bundle）
脚本：`scripts/run_router_phase27_strict_audit_v1.py:main`

主验证点：
- strict 链路 Phase9/13/22 的 gate 全通过（可作为主 paper claim 的证据）
- legacy 只作为泄露影响诊断（不可作为主 claim）
- 生成 final bundle 并 hash 记录关键文件

产物：
- `reports/router_strict_audit_v1.md`（含 strict/legacy A/B 差异表）
- `outputs/final_v4_strict/manifest.json`
- `paper/tables_router_v11_strict_knapsack/table_phase27_leakage_ab.csv`

---

# 主线 3：主线 1（设计/理论）与主线 2（口径/实验）如何逐层对应

这一节把“写在设计文档里的对象/公式/结论”逐条对齐到“跑在实验脚本里的实现/产物/表格”。

## 3.1 设计层 → 代码层 → 实验层：对照表

| 设计模块（公式/结论） | 代码实现（文件:函数/类） | 实验验证（脚本 → 产物） |
|---|---|---|
| 冻结 protocol：\(\epsilon_{\text{rel}},\alpha\)、\(Z_\pi,V,J\) | `docs/router_protocol_v1.md`；`utils/router_method_core.py:{RiskBudgetProtocol,router_metrics}` | Phase9/13/22 的 `stats.json` 与 `reports/*.md` |
| 反事实表 schema（同时有 fast/slow 结果） | `scripts/run_router_counterfactual.py:main`（生成 `L_*/T_*`、`q_rel`、`c`） | Phase9 `outputs/*/common/router_counterfactual_{calib,test}.parquet` |
| P5：split conformal 上界 \(\hat p^{up}=\hat p+q_d\) | `scripts/run_router_phase8_strict.py:_split_conformal_offsets`；`utils/router_method_core.py:split_conformal_upper_q` | Phase9 `.../conformal_strict_v2/policy_metrics.json`（风险/CI 满足 gate） |
| P5：risk-per-compute 分数 \(u=p^{up\,a}/c_{norm}^b\) + 组阈值 | `scripts/run_router_phase8_strict.py:_run_conformal_seed`（score + search） | Phase9 `.../conformal_strict_v2/test_decisions.parquet` |
| P6：probe 只 flip fast→slow（单调升级） | `utils/router_method_core.py:ProbeFlipRouter`；`scripts/run_router_phase8_strict.py:_apply_probe_k_by_diff` | Phase24 `outputs/router_phase24_theory_v3/probe_monotone.csv` |
| P6：LCB + 预算 knapsack（\(\mathrm{LCB}/c\) 贪心） | `scripts/run_router_phase8_strict.py:_run_probe_seed`（`knapsack_lcb` 分支） | Phase9 strict 主链路 `outputs/router_phase9_bench_v6_strict_knapsack/*`（并在 Phase27 审计固定） |
| Theorem 2：prior shift 风险证书 \(V_p\le \sum p_g u_g\) | `docs/router_theory_v3_appendix.md`；`scripts/run_router_phase24_theory_v3.py`（Wilson 上界） | Phase24 `outputs/router_phase24_theory_v3/shift_bounds.csv` |
| Theorem 1：oracle regret 的经验 Bernstein UCB | `docs/router_theory_v3_appendix.md`；`scripts/run_router_phase24_theory_v3.py:_empirical_bernstein_upper` | Phase24 `outputs/router_phase24_theory_v3/seed_checks.csv` |
| strict：calib 内部切分 + test 一次性评估 + hash 绑定 | `scripts/run_router_phase8_strict.py:_split_calib_train_val`；`utils/parquet_guard.py`；`scripts/run_router_phase9_bench.py:main` | Phase27 `reports/router_strict_audit_v1.md` + `outputs/final_v4_strict/manifest.json` |

## 3.2 从“实验最上层入口”一路拆到“最底层公式”的链路图（可检索）

1) 一键复现入口  
`artifacts/router_camera_ready_v3/reproduce_main_tables_figures.sh`

2) strict 总控（paper-valid）  
`scripts/run_router_phase27_strict_audit_v1.py:main`

3) 主结论链路（Phase9→13→22）  
- Phase9：`scripts/run_router_phase9_bench.py:main`  
  ↳ dataset：`scripts/build_router_phase9_dataset.py:main`  
  ↳ counterfactual：`scripts/run_router_counterfactual.py:main`  
  ↳ static features + legacy baselines：`scripts/run_router_risk_v1.py:_compute_features`  
  ↳ strict router：`scripts/run_router_phase8_strict.py:{_run_conformal_seed,_run_probe_seed}`  
- Phase13：`scripts/run_router_phase13_sota.py:main`（聚合 baselines + 外部表）  
- Phase22：`scripts/run_router_phase22_direct_baselines.py:main`（CRC/CDT 对齐）

4) 理论可验证链路（Phase23→24）  
- Phase23：`scripts/run_router_phase23_portfolio_v1.py:main`（K≥3 arms）  
- Phase24：`scripts/run_router_phase24_theory_v3.py:main`（三条定理逐条输出检查表）

5) 终局产物与可追溯性  
- strict 审计报告：`reports/router_strict_audit_v1.md`
- strict bundle：`outputs/final_v4_strict/manifest.json`
- 下游 sha256 绑定文件：各阶段输出目录下的 `inputs_parquet_sha256.json`

---

## 附：当前 strict 结论“是否恢复投稿优势”的单一引用点

不要在论文/报告里“手抄数字”。当前 strict 结论以：
- `reports/router_strict_audit_v1.md`
- `outputs/final_v4_strict/manifest.json`
为准（两者在 Phase27 里同时生成并被 hash 记录）。
