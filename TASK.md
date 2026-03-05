# NeurIPS/ICML 冲线任务书（贡献度增强版：避免“纯工程集成”质疑）

更新日期：2026-03-04

本任务书面向 **Dual-Path Router（Fast/Slow）** 主线（入口：`README_router.md`），目标是补齐 *NeurIPS/ICML 审稿视角下* 仍缺的“方法级贡献”，把项目从“强工程集成/强系统”推进到“方法 + 理论 + 实证都能站住”的顶会水准。

> 说明：本仓库的工程闭环与复现链路已经很强（`outputs/final_v2/` + `artifacts/router_camera_ready_v2/`）。但在 NeurIPS/ICML 语境下，仅有闭环与 SOTA 表格仍可能被认为“主要贡献是系统集成与工程验证”。本任务书聚焦 **补充/重构哪些工作** 才能把贡献重心拉回“方法”。

---

## ⚠️ 2026-03-04 重要审计更新：严格协议下的“优势消失”已被修复（Phase27 Recovery 完成）

为排除 **test 调参/数据泄露** 对结论的影响，本仓库已将 Phase8 的选择逻辑改为：
1) 在 `calib` 内部再切分（`calib_train/calib_val`）完成选择；  
2) `test` **只做一次性最终评估**（不再参与选择/搜索）；  
3) 并对下游脚本增加 `parquet sha256` 绑定校验（发现覆盖则强制全量重跑，避免“跳过逻辑 + 旧产物”造成的伪优势）。

最新严格审计显示：在上述约束下，旧版（v1）在 Phase9/Phase13/Phase22 上的主要优势 **不再成立**（strict v2/v3），并出现轻微负增益；但在 Step12 的 **Recovery** 中，我们引入了一个可单独成“方法贡献”的严格选择机制（`knapsack_lcb`：signed gain + split-conformal LCB + budgeted greedy knapsack），已在 strict 协议下重新拿回显著优势（strict v6）。

证据（对照）：
- Phase9（Probe vs Conformal，公共 cross-benchmark test）：  
  - legacy v1：`outputs/router_phase9_bench_v1/stats.json`（`mean_delta_j=+0.03479` 且显著）  
  - strict v2：`outputs/router_phase9_bench_v2_calibsplit/stats.json`（`mean_delta_j=-0.00490`，CI 跨 0，不显著）  
  - strict v6（Recovery, knapsack_lcb）：`outputs/router_phase9_bench_v6_strict_knapsack/stats.json`（`mean_delta_j=+0.02588`，CI 不跨 0，`p_boot=0`）
- Phase13（vs strongest baseline 的外部 SOTA 汇总）：  
  - legacy v1：`outputs/router_phase13_sota_v1/stats.json`（`J_improve≈+5.71%` 且显著）  
  - strict v2：`outputs/router_phase13_sota_v2_calibsplit/stats.json`（`J_improve≈-0.125%`，CI 跨 0，不显著）  
  - strict v4（Recovery, knapsack_lcb）：`outputs/router_phase13_sota_v4_strict_knapsack/stats.json`（`J_improve≈+3.283%`，CI 不跨 0，`p_boot=0`）
- Phase22（CDT/CRC 直接基线对齐）：  
  - legacy v1：`outputs/router_phase22_direct_baselines_v1/stats.json`  
  - strict v2：`outputs/router_phase22_direct_baselines_v2_calibsplit/stats.json`（`either_win_or_reframe=False`，`main_result_significant=False`）  
  - strict v4（Recovery, knapsack_lcb）：`outputs/router_phase22_direct_baselines_v4_strict_knapsack/stats.json`（`either_win_or_reframe=True`，`main_result_significant=True`）

因此：本任务书中所有与“顶会可投稿主结果（显著优势）”相关的 `DONE` 判定，必须以 **strict（calib-only selection/search）** 作为准绳重新验收。Step 12（严格协议重评估 + 结果修复）现已完成，`NeurIPS/ICML Ready` 可恢复终局判定（仍以 gate 全绿为准）。

---

## 0. 目标、范围与停止规则

### 0.1 三种达标状态（不同 venue 期待不同）
1. `Robotics-TopConf Ready`：RSS/CoRL/ICRA/IROS 方向的顶会投稿水准（更看重系统闭环与鲁棒性）。  
2. `NeurIPS/ICML Ready`：NeurIPS/ICML（含 adaptive computation / uncertainty / decision-making / safe ML 等相关 track）的顶会投稿水准（更看重方法新意与通用性）。  
3. `Top-Journal Ready`：T-RO/IJRR 等顶刊投稿水准（通常额外要求更长时的真实硬件与失效归因闭环）。  

### 0.2 范围与不变量（冲线前不允许破坏）
1. **协议冻结**：`docs/router_protocol_v1.md` 已冻结；任何口径变更必须升级版本并重跑所有受影响 phase。  
2. **不做“为了好看数字”的主线调参**：Phase7~15 的封版结论不做结果导向调参；只允许做 *补强证据、补齐对齐、补齐通用性与方法表达*。  
3. **证据链要求**：新增任何 claim 必须对应：
   - 代码（脚本）+ 输出（`outputs/*/stats.json`）+ 报告（`reports/*.md`）+ 表/图（`paper/tables_*`, `paper/figures_*`）+ 复现包（`artifacts/*`）。  
4. **停止规则**：当达到某一达标状态后：
   - 禁止修改冻结协议与主要结论口径；
   - 后续只允许新增 extension，且不得影响主结论可复现。  

---

## 1. 当前已具备（但容易被 NeurIPS/ICML 认为“偏工程”）

以下能力对机器人顶会很加分，但在 NeurIPS/ICML 中往往只算“必要但不充分”：
1. **冻结协议 + 风险口径**：`docs/router_protocol_v1.md`（`J` 与 `V=P(delta_l_rel>epsilon_rel)`）。  
2. **可部署策略工件**：单一 policy artifact（`artifacts/router_policy_v1/`）+ 部署 runner 加载一致性（`reports/router_phase17_policy_alignment_v1.md`）。  
3. **统计与证据闭环**：5 seeds + bootstrap/Wilcoxon（见 `reports/router_phase13_sota_v1.md`、`reports/router_phase16_related_baselines_v1.md`）。  
4. **Camera-ready 复现包**：`artifacts/router_camera_ready_v2/` 与 `outputs/final_v2/`（一键复现主表主图）。  

---

## 2. NeurIPS/ICML 审稿视角的“方法贡献缺口”（必须补齐）

为了避免被一句话打回（“这是已有思想的工程集成/系统化”），需要正面补齐：
1. **直接对齐顶会同类方法**：不仅是“相关工作写了”，而是要有 *同协议可复现实现*，尤其是 CDT/CRC/Selective decision、budgeted prediction、algorithm selection / meta-reasoning 等。  
2. **非平凡（non-trivial）的方法新意**：需要能在摘要/引言里写成 1-2 句的 *明确方法贡献*，而不是“我们做了一个系统”。  
3. **通用性证据**：至少证明方法不是“只对这一套 fast/slow 规划器 + 这一套地图特征”有效（≥2 个设置/栈/任务的泛化）。  
4. **更强的理论支撑**：当前 V1/V2 理论包含单调安全与分层鲁棒上界，但偏“正确但简单”。NeurIPS 更偏好：对两阶段/多臂/流式 shift 的 *可验证、可复现实验支撑* 的理论结论。  

---

## 3. 剩余必须完成的工作（完成后可宣称 `NeurIPS/ICML Ready`）

> 约定：下面新增工作使用 Phase 编号从 `Phase21` 开始，不改动既有 Phase7~20 的冻结产物。

---

## 3.1 Step 6：问题重构 + 方法抽象（把“router”提升为通用方法）（Phase21 NeurIPS Positioning + Core Method）
状态：`DONE`（证据：`docs/neurips_method_v1.md`，`utils/router_method_core.py`，`scripts/run_router_phase21_minimal_demo.py`，`outputs/router_phase21_neurips_positioning_v1/stats.json`，`reports/router_phase21_neurips_positioning_v1.md`；gate 全部满足）

执行目标：
1. 将论文主叙事从“规划系统路由”重构为：**风险约束下的自适应计算分配（adaptive computation under risk）** / **多保真算法组合（multi-fidelity portfolio）**。  
2. 将方法核心抽象为可复用模块（输入是 counterfactual/features 表，输出是决策），让读者看到“方法本体”而不是系统细节。  

必须完成的工作（全部必做）：
1. **重写贡献声明（写成 3 条，可在 abstract 里出现）**：
   - 方法贡献（Algorithm）：我们提出什么 *可复现算法*（不是系统描述）。  
   - 理论贡献（Theory）：我们证明/证书化了什么（不是经验观察）。  
   - 实证贡献（Empirical）：我们在哪些设置上验证通用性与优势。  
2. **方法最小化实现（core-only）**：把 “学习/拟合 → 校准/证书 → 决策” 抽出为独立模块（不依赖闭环 runner），并提供 toy 示例脚本（10s 内可跑）。  
3. **方法接口冻结**：为后续基线/扩展提供统一 API（fit/predict/evaluate），避免每加一个 baseline 就“工程堆脚本”。  

交付物（必须全部生成）：
1. 叙事与方法文档：`docs/neurips_method_v1.md`（含 Problem / Algorithm 1 / Guarantees / Limitations）。  
2. Core 方法模块：`utils/router_method_core.py`（或新建 `router/` 包，但需保持最小依赖）。  
3. 最小示例：`scripts/run_router_phase21_minimal_demo.py`（用合成数据或极小 parquet 展示风险-代价权衡）。  
4. 报告：`reports/router_phase21_neurips_positioning_v1.md`（列出 3 条贡献与所有 gate）。  

验收指标（全部满足）：
1. `contribution_triple_clear = True`（Algorithm/Theory/Empirical 三条贡献可独立陈述）。  
2. `core_method_minimal_demo_runs = True`（toy demo 可在 CPU <10s 跑通，且输出可解释指标）。  
3. `api_frozen_for_baselines = True`（后续 Step7/8/10 的新方法都通过同一接口评测）。  

---

## 3.2 Step 7：顶会同类方法“直接实现 + 同协议对齐”（Phase22 CDT/CRC + Budgeted Decision Baselines）
状态：`DONE`（已完成 direct baselines 实现与 strict 审计复跑；并已按 strict 结果完成 claim reframe 与 paper-facing 文档同步）

证据（legacy v1；历史对照）：
- 脚本：`scripts/run_router_phase22_direct_baselines.py`  
- 输出：`outputs/router_phase22_direct_baselines_v1/stats.json`  
- 报告：`reports/router_phase22_direct_baselines_v1.md`  
- 论文表：`paper/tables_router_v7/table_phase22_direct_baselines.csv`  
- 对齐文档：`paper/related_work_neurips_alignment.md`（包含 legacy 与 strict 两套结论）  

证据（strict v2 calibsplit 审计；协议干净版本）：
- 输出：`outputs/router_phase22_direct_baselines_v2_calibsplit/stats.json`  
- 报告：`reports/router_phase22_direct_baselines_v2_calibsplit.md`  
- 论文表（审计版）：`paper/tables_router_v7_calibsplit_audit/table_phase22_direct_baselines.csv`  
- 相关说明更新：`paper/related_work_neurips_alignment.md`、`docs/neurips_method_v1.md`  

执行目标：
1. 让审稿人无法用一句话否定创新：“这就是 CDT/CRC/Selective decision 的应用”。  
2. 用 *同协议、同预算口径、同数据表* 做 **直接可复现对照**，并明确我们“比它新在哪/强在哪/限制在哪”。  

必须完成的工作（全部必做）：
1. **实现并对齐至少 2 个 NeurIPS/ICML 直系 baseline**（至少各 1 个可复现实现）：
   - `CDT-style decision`（cost-aware conformal decision / abstain-with-cost 的等价实现）。  
   - `CRC-style`（conformal risk control / risk-limited selective decision 的等价实现）。  
   - （推荐加分）`Budgeted prediction / early-exit`（在预算约束下做路由；可用简单 gating network + 校准）。  
2. **同口径公平性**：
   - 使用同一 `router_counterfactual_{calib,test}.parquet`（或协议冻结的等价表）。  
   - 统一计价：把 probe 计算、额外规划开销都计入 `T`（避免 baseline 偷算力）。  
3. **结论写法要求**：如果我们赢，写清“赢在哪”（不是只报数字）；如果我们不赢，必须明确 “方法边界 + 失败模式”，并调整主贡献声明（回到 Step6 修正）。  

交付物（必须全部生成）：
1. 脚本：`scripts/run_router_phase22_direct_baselines.py`  
2. 输出：`outputs/router_phase22_direct_baselines_v1/`（含 `stats.json` + seed 明细）  
3. 报告：`reports/router_phase22_direct_baselines_v1.md`  
4. 论文表：`paper/tables_router_v7/table_phase22_direct_baselines.csv`  
5. 论文段落：`paper/related_work_neurips_alignment.md`（明确“我们 vs CDT/CRC”的差异点）  

验收指标（全部满足）：
1. `direct_baselines_ge_2 = True`。  
2. `same_protocol_and_budget = True`。  
3. `strict_audit_completed = True`（已生成 strict 版本 stats/report/table，且引用路径在任务书中固定）。  
4. `paper_claims_synced = True`（`paper/related_work_neurips_alignment.md` 与 `docs/neurips_method_v1.md` 明确写出 strict 结果下的边界与 reframe）。  

---

## 3.3 Step 8：方法升级到“多臂/多预算”并证明泛化（Phase23 Portfolio Router）
状态：`DONE`  
证据：
- 中间臂（mid）确认：`outputs/router_phase23_midnet_arm_full_tiny_b64_v1/stats.json`，`reports/router_phase23_midnet_arm_full_tiny_b64_v1.md`  
- K=3 counterfactual（calib/test 全量）：`outputs/router_phase23_portfolio_v1/common/router_counterfactual_{calib,test}_k3_midnet.parquet`  
- Phase23 脚本与主结果：`scripts/run_router_phase23_portfolio_v1.py`，`outputs/router_phase23_portfolio_v1/stats.json`，`reports/router_phase23_portfolio_v1.md`  
- Sweep/Pareto 诊断表：`outputs/router_phase23_portfolio_v1/common/sweep_grid_mean_over_seeds.csv`  
- 论文表/图：`paper/tables_router_v7/table_phase23_portfolio.csv`，`paper/figures_router_v7/fig_portfolio_tradeoff.svg`  

本轮尝试记录（候选 mid 臂逐个落地）：
1. `lowres`：质量指标崩坏（违约率极高），放弃。证据：`outputs/router_phase23_portfolio_v1/pilot/router_counterfactual_test_k3_lowres2_n500_report.json`  
2. `crop_padded`：可用但平均更慢于 slow，作为中间臂不理想。证据：`outputs/router_phase23_portfolio_v1/pilot/router_counterfactual_test_k3_crop_p32_n500_report.json`  
3. `midnet`：确认作为中间臂（时延介于 fast/slow，风险可控），进入 Phase23 主评测。  

执行目标：
1. 将二选一（fast/slow）扩展到 `K>=3` 的多臂选择（或多预算同一规划器），证明方法是通用的 *portfolio selection under risk*。  
2. 让“这是为某个系统手工调出来的规则”这种质疑站不住：方法应在新的臂集合中仍保持风险控制与收益。  

必须完成的工作（全部必做）：
1. 增加至少一个中间臂（示例）：`mid`（介于 fast/slow 的预算与质量）。  
2. 定义并冻结多臂版本的风险事件与约束（建议保留 `epsilon_rel` 语义，或给出等价 mapping）。  
3. 给出多臂决策规则（必须是可复现算法，而不是“手工 if-else”），并写入 Step6 的 Algorithm 1。  

交付物（必须全部生成）：
1. 脚本：`scripts/run_router_phase23_portfolio_v1.py`  
2. 输出：`outputs/router_phase23_portfolio_v1/`（含 `stats.json`）  
3. 报告：`reports/router_phase23_portfolio_v1.md`  
4. 论文表/图：`paper/tables_router_v7/table_phase23_portfolio.csv`、`paper/figures_router_v7/fig_portfolio_tradeoff.*`  

验收指标（全部满足）：
1. `num_arms_ge_3 = True`。  
2. `risk_constraint_hold_all_seeds = True`（在冻结 protocol seeds 上成立）。  
3. `pareto_improve_vs_best_arm = True`（相对最强单臂或最强直接 baseline，在 `J`-risk-latency 三者上至少形成明确 Pareto 优势区域）。  

备注（重要）：当前 Phase23 的 gate 满足 `pareto_improve_vs_best_arm=True`，但“选中策略相对 best single-arm 的 `J` 改善”未必显著（见 `outputs/router_phase23_portfolio_v1/stats.json` 的 `ours_vs_always_mid` 段）。若要把 Phase23 写成 NeurIPS/ICML 的主结果，需要在 Step12 的 strict 协议总复跑下确认其显著性与稳定性。

---

## 3.4 Step 9：理论 V3（两阶段/多臂/流式 shift 的可验证保证）（Phase24 Theory Upgrade）
状态：`DONE`  
证据：
- 文档：`docs/router_theory_v3.md`，`docs/router_theory_v3_appendix.md`（≥2 条定理，含 Assumptions/Statement/Proof）  
- 脚本：`scripts/run_router_phase24_theory_v3.py`  
- 输出：`outputs/router_phase24_theory_v3/stats.json`，`outputs/router_phase24_theory_v3/seed_checks.csv`，`outputs/router_phase24_theory_v3/shift_bounds.csv`，`outputs/router_phase24_theory_v3/probe_monotone.csv`  
- 报告：`reports/router_phase24_theory_v3.md`（逐 seed、逐 OOD family 校验结果 + slack 阈值）  

执行目标：
1. 产出 **非平凡** 的理论贡献：覆盖两阶段（conformal→probe）、多臂、与至少一种非 i.i.d./shift 情况。  
2. 理论必须做到“可验证”：提供脚本在冻结 seeds 上自动检查每个不等式/上界是否成立。  

必须完成的工作（全部必做）：
1. 给出至少 2 条 V3 级别结论（示例方向，二选一或更多）：
   - 多臂/多预算下的风险证书（与 CDT/CRC 的关系清晰）。  
   - 两阶段选择在 *数据依赖 probe 特征* 下的有效性条件（什么时候保证成立、什么时候会破）。  
   - 流式/轻度非 i.i.d.（例如按 map-family 分块）的风险上界（martingale/自归一化界均可，但必须可复现实证验证）。  
2. 明确假设与可检验条件，并在报告中列出“假设可能不成立”的真实案例。  

交付物（必须全部生成）：
1. 文档：`docs/router_theory_v3.md` + `docs/router_theory_v3_appendix.md`  
2. 脚本：`scripts/run_router_phase24_theory_v3.py`（输出逐 seed 校验表）  
3. 输出：`outputs/router_phase24_theory_v3/`（含 `stats.json` + 校验 CSV）  
4. 报告：`reports/router_phase24_theory_v3.md`  

验收指标（全部满足）：
1. `theory_v3_nontrivial = True`（结论不等价于“子集⇒更安全”这一级别）。  
2. `empirical_checks_all_hold = True`（冻结 5 seeds + OOD families 上逐条校验通过）。  
3. `bound_gap_reasonable = True`（上界 slack 给出量化阈值并达标）。  

---

## 3.5 Step 10：跨设置泛化（证明“不是某一套系统调参”）（Phase25 Generalization）
状态：`DONE`  
证据：
- 脚本：`scripts/run_router_phase25_generalization_v1.py`  
- 输出（总 gate）：`outputs/router_phase25_generalization_v1/stats.json`  
- 输出（分设置）：`outputs/router_phase25_generalization_v1/settings/mp/stats.json`、`outputs/router_phase25_generalization_v1/settings/csm/stats.json`  
- 报告：`reports/router_phase25_generalization_v1.md`  
- 论文图：`paper/figures_router_v7/fig_generalization_mp.svg`、`paper/figures_router_v7/fig_generalization_csm.svg`  

执行目标：
1. 在至少 **两个** 与当前主设置有明显差异的设置上复现主要趋势（risk 控制 + `J` 优势/不劣）。  
2. 让方法贡献具有“可移植性”：换 planner、换地图族、换噪声/延迟模型，方法仍成立。  

必须完成的工作（全部必做，二选一但必须是“明显不同”）：
- 方案 A（推荐）：同领域跨栈  
  1) 新 planner family（例如不同启发式/不同运动学/不同栅格规模）；  
  2) 新 OOD family（显著不同的 map 生成分布/障碍统计）。  
- 方案 B：跨域  
  1) 一个非规划领域的 algorithm portfolio / budgeted decision 任务（只要能构造 counterfactual 表并复用 core 方法即可）。  

交付物（必须全部生成）：
1. 脚本：`scripts/run_router_phase25_generalization_v1.py`  
2. 输出：`outputs/router_phase25_generalization_v1/`（含 `stats.json`）  
3. 报告：`reports/router_phase25_generalization_v1.md`  
4. 论文图：`paper/figures_router_v7/fig_generalization_*.{pdf,svg,png}`  

验收指标（全部满足）：
1. `new_settings_ge_2 = True`。  
2. `risk_control_holds_in_new_settings = True`。  
3. `trend_consistent = True`（主要优势方向不翻车；若翻车必须定位原因并在 Limitations 明确写出）。  

---

## 3.6 Step 11：NeurIPS/ICML Camera-ready 复现包（V3）（Phase26 Camera-Ready V3）
状态：`DONE`  
证据：
- 脚本：`scripts/run_router_phase26_camera_ready_v3.py`  
- 复现包审计：`artifacts/router_camera_ready_v3/audit_summary.json`  
- 终局 bundle：`outputs/final_v3/manifest.json`  
- 更新清单：`paper/final_submission_checklist.md`  

执行目标：
1. 把 Step6~Step10 的新增方法/理论/泛化结果全部纳入一键复现包。  
2. 让审稿人/复现者能在“方法层”复现，而不仅是系统跑通。  

必须完成的工作（全部必做）：
1. 新复现包：`artifacts/router_camera_ready_v3/`（含 Dockerfile、lock、主入口脚本、audit）。  
2. 新终局 bundle：`outputs/final_v3/`（manifest + paper assets + reports + stats）。  
3. 审计覆盖：claim→evidence 覆盖 Step6~Step10，并在 checklist 冻结。  

交付物（必须全部生成）：
1. `artifacts/router_camera_ready_v3/`  
2. `outputs/final_v3/manifest.json`  
3. `artifacts/router_camera_ready_v3/audit_summary.json`  
4. 更新清单：`paper/final_submission_checklist.md`（新增 Step6~Step10 claims）  

验收指标（全部满足）：
1. `cold_start_runtime_le_48h = True`。  
2. `hash_consistency_100pct = True`。  
3. `claim_coverage_100pct = True`。  
4. `audit_blocker_zero = True`。  

---

## 3.7 Step 12：严格协议重评估 + 结果修复（Phase27 Strict-Audit + Recovery）
状态：`DONE`（strict 协议下 Phase9/13/22 主结果已恢复且显著；strict vs legacy A/B 已固化到 Phase27 审计）

执行目标：
1. 在 **严格“只用 calib 做选择/搜索”** 的协议下，重新获得可写进主论文的显著优势（或给出足够强的 reframe，并用严格证据支撑）。  
2. 把“数据泄露/覆盖导致伪优势”这个风险从流程层面消灭：任何关键 parquet 覆盖必须触发全量重跑，且所有选择逻辑必须显式记录“使用了哪些 split”。  

本阶段任务目标（写入并冻结）：
1. **全链路严格 split**：所有选择/搜索只用 `calib_train/calib_val`，`test` 仅一次最终评估，并在产物里可追溯记录。  
   - 设计改动：`不需要`（属于协议/runner 行为约束与日志可追溯性补强）。  
2. **sha256 绑定全覆盖**：对所有有 `skip/cache/复用` 的关键阶段写入+校验 `inputs_parquet_sha256.json`；发现 parquet 覆盖/变化则强制全量重跑并报告 mismatch。  
   - 设计改动：`不需要`（属于可复现/审计基础设施）。  
3. **Strict 主链路总复跑出终局**：Phase8→Phase9→Phase13→Phase22（必要时含 Phase23/25）生成 `*_v3_strict` 输出，并汇总成 `outputs/final_v4_strict/manifest.json`。  
   - 设计改动：`不需要`（属于严格协议下的复跑与归档）。  
4. **泄露影响 A/B 量化**：legacy（诊断：允许在 `test` 上选/搜）vs strict（主结论：只用 `calib_train/calib_val` 选/搜，`test` 只评）对照，产出可写 Appendix 的差异表。  
   - 设计改动：`不需要`（属于诊断实验与写作证据）。  
5. **解除 BLOCK 的验收**：在 strict 下达成 `phase9_gain_significant / phase13_sota_significant / phase22_alignment_honest`，否则按 strict 证据重写主 claim。  
   - 设计改动：`条件性需要`：验收与重写 claim 本身不需要；但若坚持“显著优势”作为主结果而 strict 下未通过，则需要进入 **Recovery**（方法/模型层的改进），这会涉及对现有模块的算法与训练/选择机制做改动（但仍应遵守“不大幅改动当前设计逻辑”的约束）。  

必须完成的工作（全部必做）：
1. **Strict split 规范化（全链路）**：统一约定并在脚本里强制：
   - `calib → calib_train/calib_val`：所有阈值/超参/预算/搜索只允许在这两者上完成；
   - `test`：只允许一次性 final evaluation，严禁参与选择（包括 probe 的 `k` 搜索、portfolio 的 tau 搜索、任何 sweep 的 pick）。
2. **全链路 sha256 绑定**：
   - 对 Phase8→Phase14、Phase22、Phase23、Phase25 等所有“有 skip/cache/复用”的关键阶段，写入并校验 `inputs_parquet_sha256.json`；
   - 检测到覆盖/变化后必须强制重跑，并在报告中给出 mismatch summary。
3. **严格协议总复跑（主链路）**：产出一套“strict 终局”主结果（建议统一命名 `*_v3_strict` / `final_v4_strict`）：
   - Phase8 strict（calib split 选择）；
   - Phase9（Probe vs Conformal）；
   - Phase13（SOTA 汇总）；
   - Phase22（direct baselines 对齐）；
   - 视情况补跑 Phase23/Phase25（用于支撑“多臂/泛化”的主张）。
4. **泄露影响的可复现量化（可写进 Appendix）**：用同一代码，跑一个 A/B：
   - A：允许 legacy 的“在 test 上选/搜”（仅用于诊断，不作为主结果）；  
   - B：strict（calib_train/calib_val 选，test 只评）；  
   并输出“增益差异”的统计表与解释，避免审稿人质疑。

交付物（必须全部生成）：
1. strict 输出（主结论）：`outputs/router_phase9_bench_v6_strict_knapsack/`、`outputs/router_phase13_sota_v4_strict_knapsack/`、`outputs/router_phase22_direct_baselines_v4_strict_knapsack/`  
2. 诊断输出（legacy_diag，仅 Appendix 诊断）：`outputs/router_phase9_bench_v3_legacy_diag/`、`outputs/router_phase13_sota_v3_legacy_diag/`、`outputs/router_phase22_direct_baselines_v3_legacy_diag/`  
3. strict 终局 bundle：`outputs/final_v4_strict/manifest.json`（paper tables/figures/reports/stats 对应 strict 版本；同时包含 diagnostics 目录）  
4. 报告：`reports/router_strict_audit_v1.md`（严格协议主结论 + legacy 对照 + gate 总结）  

验收指标（全部满足，才能解除 BLOCK）：
1. `no_test_tuning = True`（strict：`outputs/router_phase9_bench_v6_strict_knapsack/stats.json` 中记录 `conformal_select_on=calib`、`probe_search_on=calib`；Phase27 审计报告固化）。  
2. `phase9_gain_significant = True`（strict：`outputs/router_phase9_bench_v6_strict_knapsack/stats.json`，CI 不跨 0 且 `p_boot=0`）。  
3. `phase13_sota_significant = True`（strict：`outputs/router_phase13_sota_v4_strict_knapsack/stats.json`，gate 全绿）。  
4. `phase22_alignment_honest = True`（strict：`outputs/router_phase22_direct_baselines_v4_strict_knapsack/stats.json`，`either_win_or_reframe=True` 且 `main_result_significant=True`）。  

---

## 4. 既有工程证据链（不回退，仅复用）

> 这部分是 `Robotics-TopConf Ready` 的主要组成，也为 NeurIPS 提供“强实证/强复现”底座；但它本身不足以消除“纯工程”质疑。

### Step 1：相关工作对齐 + 强基线补齐（Phase16 Related-Work Baselines）
状态：`DONE`  
证据：`reports/router_phase16_related_baselines_v1.md`、`outputs/router_phase16_related_baselines_v1/stats.json`  

### Step 2：部署链路一致性封口（Phase17 Policy Alignment）
状态：`DONE`  
证据：`reports/router_phase17_policy_alignment_v1.md`、`outputs/router_phase17_policy_alignment_v1/stats.json`、`artifacts/router_policy_v1/`  

### Step 3：真实硬件长时闭环（Phase18 Real-hardware Longrun）
状态：`TODO`（仅 `Top-Journal Ready` 必需；本轮评估按要求忽略实机部署）  

### Step 4：指标与任务定义增强（Phase19 Metrics Extension）
状态：`DONE`  
证据：`reports/router_phase19_metrics_extension_v1.md`、`outputs/router_phase19_metrics_extension_v1/stats.json`  

### Step 5：文档、报告与复现包升级（Phase20 Camera-Ready V2）
状态：`DONE`  
证据：`reports/router_phase20_camera_ready_v2.md`、`artifacts/router_camera_ready_v2/audit_summary.json`、`outputs/final_v2/manifest.json`  

---

## 5. 终局判定（完成即停止主线）

### 5.1 `Robotics-TopConf Ready`（系统/机器人顶会）
判定条件（全部为 True）：
1. Step 1/2/4/5 全部 `DONE` 且 gate 全绿。  
2. `outputs/final_v2/` 审计通过，`blocker=0`。  

### 5.2 `NeurIPS/ICML Ready`（方法/理论/通用性顶会）
判定条件（全部为 True）：
1. Step 6~12 全部 `DONE` 且 gate 全绿（其中 Step12 必须通过 strict 协议验收）。  
2. Step 1/2/4/5 作为底座不回退（复现审计通过）。  
3. `outputs/final_v4_strict/` 审计通过，`blocker=0`。  

### 5.3 `Top-Journal Ready`（顶刊）
判定条件（全部为 True）：
1. 满足 `Robotics-TopConf Ready`；  
2. Step 3（真实硬件长时闭环）`DONE` 且 gate 全绿。  
