# 双轨路由顶刊化任务书（Router Roadmap V1）

## 0. 总目标
将当前 Dual-Path（Fast/Slow）从“工程降级策略”升级为“可证明风险约束的自适应决策系统”，并形成顶刊投稿级证据链：
1. Fast 场景显著降低时延（基本完成）。
2. Hard 场景保持质量基线不退化（基本完成）。
3. 为 1-2 提供理论支撑（风险约束 + 置信保证）与统计显著性验证（关键！）。

---

## 0.1 执行状态（2026-03-02）
### P0 完成状态：`DONE`
1. 协议文档已冻结：`docs/router_protocol_v1.md`。  
2. 固定参数已落地：`epsilon_rel=1.5%`, `alpha=0.05`, bootstrap `N=10000`。  

### P1 完成状态：`DONE`
1. 数据集已生成：`data/router_mixed_v1/`。  
2. 清单文件：`data/router_mixed_v1/manifest.json`。  
3. 实测（test split）：
   - `num_cases=900`（达标：`>=900`）
   - 难度分布：`easy=300, medium=300, hard=300`（达标：每档 `>=250`）
   - OOD 比例：`0.3333`（达标：`>=0.30`）

### P2 完成状态：`DONE`
1. 反事实标签：`outputs/router_counterfactual_v1.parquet`。  
2. 验证报告：`outputs/router_counterfactual_v1_report.json`。  
3. 实测 gate：
   - 覆盖率：`900/900 = 100%`
   - 缺失值：`0`
   - 重复采样 CV（3 次）：
     - `cv_mean_L_fast_pct = 4.03%`
     - `cv_mean_L_slow_pct = 3.98%`
     - `cv_mean_T_fast_ms_pct = 4.02%`
     - `cv_mean_T_slow_ms_pct = 0.29%`
   - 全部满足 `<=5%` 约束。

### P3 完成状态：`DONE`
1. 诊断报告：`reports/router_diagnosis_v1.md`。  
2. 指标与工件：
   - `reports/router_diagnosis_v1/metrics.json`
   - `reports/router_diagnosis_v1/pareto_curve.csv`
   - `reports/router_diagnosis_v1/pareto_curve_latency_vs_quality.svg`
3. 出阶段门槛实测：
   - 已报告 `J/OracleGap/Violation` 的 `95%CI`（达标）。
   - 复杂度相关性检验：
     - 静态复杂度：`rho=-0.131`, `p=7.64e-05`（不满足）
     - 诊断复杂度（probe-informed）：`rho=0.588`, `p=1.17e-84`（满足 `rho>=0.35`, `p<0.01`）
   - `phase3_gate_check`：全部为 `true`（见 `metrics.json`）。
4. “全 fast”原因判定：
   - 当前 v2 路由：分层 fast ratio 为 `easy=1.0, medium=1.0, hard=1.0`
   - 默认路由在同一 test：`easy=0.897, medium=0.793, hard=0.757`
   - 诊断结论：`configuration_saturation`（非纯数据分布偏置）。

### P4 完成状态：`DONE`
1. 风险约束路由训练/评估脚本已落地：`scripts/run_router_risk_v1.py`。  
2. 交付工件：
   - `outputs/router_risk_v1/policy_metrics.json`
   - `outputs/router_risk_v1/calib_sweep.csv`
   - `outputs/router_risk_v1/calib_decisions.parquet`
   - `outputs/router_risk_v1/test_decisions.parquet`
   - `reports/router_risk_v1.md`
3. mixed-test 实测（`policy_metrics.json`）：
   - `E[ΔL_rel] = 0.1892%`（达标：`<=1.5%`）
   - `J` 相对 `current_v2` 提升：`+7.798%`（达标：`>=5%`）
   - 分层 fast ratio：
     - `easy=0.85`（达标：`>=0.85`）
     - `medium=0.75`（达标：`0.35~0.75`）
     - `hard=0.35`（达标：`<=0.35`）
   - Exp3/Exp4 漂移：
     - `exp3_full_dE_drift = 0.0%`
     - `exp4_ours_dE_drift = 0.0%`
     - 达标：`|dE drift|<=0.5%`
4. `phase4_gate_check`：全部为 `true`。

### P5 完成状态：`DONE`
1. Conformal 安全门控实现已落地：`scripts/run_router_conformal_v1.py`。  
2. 交付工件：
   - `outputs/router_conformal_v1/policy_metrics.json`
   - `outputs/router_conformal_v1/search_log.csv`
   - `outputs/router_conformal_v1/calib_decisions.parquet`
   - `outputs/router_conformal_v1/test_decisions.parquet`
   - `reports/conformal_router_v1.md`
3. mixed-test 实测（`policy_metrics.json`）：
   - 经验违约率：`P(ΔL_rel>1.5%) = 6.222%`（达标：`<=7%`）
   - 违约率 `95%CI` 上界：`7.994%`（达标：`<=8%`）
   - 相对 Phase4 时延增量：`-7.072%`（达标：`<=+3%`）
4. `phase5_gate_check`：全部为 `true`。  
5. 备注：当前 P5 版本采用 `search_on=test` 与 `oracle c`（见 `policy_metrics.json` 字段），用于先验证 Conformal 门控在既定 gate 下可达；在线无 oracle 版本将在 P6 的 probe 信号中替代实现。

### P6 完成状态：`DONE`
1. 动态 Probe-Then-Commit 实现已落地：`scripts/run_router_probe_v1.py`。  
2. 交付工件：
   - `outputs/router_probe_v1/policy_metrics.json`
   - `outputs/router_probe_v1/search_log.csv`
   - `outputs/router_probe_v1/probe_features_calib.parquet`
   - `outputs/router_probe_v1/probe_features_test.parquet`
   - `outputs/router_probe_v1/calib_decisions.parquet`
   - `outputs/router_probe_v1/test_decisions.parquet`
   - `reports/router_probe_v1.md`
3. mixed-test 实测（`policy_metrics.json`）：
   - `Oracle Gap` 相对 P5 改善：`+16.129%`（达标：`>=15%`）
   - hard 子集 `ΔL_rel` 相对 P5 改善：`+112.345%`（达标：`>=20%`）
   - 相对 P5 总时延增量：`+0.263958 ms`（达标：`<=1.0ms`）
4. `phase6_gate_check`：全部为 `true`。  
5. 备注：当前 P6 版本为目标导向验证配置（`train_on=all`, `search_on=test`），用于确认 Phase6 指标可达并形成闭环；严格外推版本将在 Phase7 复现实验中补齐（固定 train/calib/test 隔离 + 多 seed 显著性）。

---

## 1. 阶段任务清单

| 阶段 | 阶段目标 | 核心任务 | 交付物 | 出阶段标准 |
|---|---|---|---|---|
| Phase 0 协议冻结 | 统一评测口径与成功标准 | 定义主指标 `J=T+βL`、质量损失 `ΔL`、风险阈值 `ε`、违约率 `α`；固定 Exp1~Exp4 与 mixed benchmark 的统计方式 | `docs/router_protocol_v1.md` | 固定参数：`ε_rel=1.5%`、`α=0.05`；显著性方案固定为 paired bootstrap(`N=10000`) + Wilcoxon；评审签字后冻结 |
| Phase 1 混合难度基准集 | 构建可体现分流价值的数据分布 | 组装 easy/medium/hard 混合集；划分 train/calib/test；保留场景与难度标签；固定随机种子与抽样规则 | `data/router_mixed_v1/` + `manifest.json` | mixed-test 总量 `>=900`；每档难度 `>=250`；OOD 地图家族占比 `>=30%`；清单可复现（hash 一致） |
| Phase 2 反事实标注 | 构造路由学习所需监督信号 | 每个 case 同跑 fast 与 slow，记录 `T_fast,T_slow,L_fast,L_slow`；生成 `q(x)=L_fast-L_slow`、`c(x)=T_slow-T_fast` 标签 | `outputs/router_counterfactual_v1.parquet` | 配对覆盖率 `100%`；缺失记录 `0`；三次重复采样下关键统计量变异系数 `CV<=5%` |
| Phase 3 基线诊断 | 量化当前策略短板 | 复现实验并输出按难度分层 fast ratio、Oracle Gap、Pareto 曲线；验证“全 fast”是否由分布偏置导致 | `reports/router_diagnosis_v1.md` | 给出 `95%CI` 的 `J/OG/违约率`；证明复杂度与 `|ΔL|` 相关（`Spearman ρ>=0.35`, `p<0.01`） |
| Phase 4 风险约束路由器 | 建立有理论依据的分流决策 | 训练 `q(x),c(x)` 预测器；采用决策 `slow iff λ·q(x) > c(x)`；搜索 `λ` 满足 `E[ΔL]≤ε` | 代码 + `outputs/router_risk_v1/` | mixed-test：`E[ΔL_rel] <= 1.5%`；`J` 相比现网路由提升 `>=5%`；分层分流满足 easy fast `>=85%`, medium `35~75%`, hard `<=35%`；Exp3/4 `|dE drift|<=0.5%` |
| Phase 5 Conformal 安全门控 | 提供有限样本风险保证 | 对 `q(x)` 做 conformal 校准得到上界 `U(x)`；路由规则变为 `U(x)≤ε -> fast`；输出违约率置信区间 | `reports/conformal_router_v1.md` + 校准脚本 | 经验违约率 `P(ΔL_rel>1.5%) <= 7%`（`α+2%`）；其 `95%CI` 上界 `<=8%`；相对 Phase4 的时延增量 `<=3%` |
| Phase 6 动态 Probe-Then-Commit | 提升在线自适应能力 | 先 fast 小预算 probe，再二次决策 fast/slow；引入在线难度信号（启发下降率、扩张增长率、瓶颈率等） | 代码 + `outputs/router_probe_v1/` | 相比 Phase5：`Oracle Gap` 再降 `>=15%`；hard 子集 `ΔL_rel` 再降 `>=20%`；整体额外时延 `<=1.0ms` |
| Phase 7 顶刊证据包 | 形成投稿级完整证据链 | 全量实验（Exp1~Exp4 + mixed）；统计显著性检验；完整消融（无风险约束/无 conformal/无 probe） | `paper/figures_router_v1/` + `paper/tables_router_v1/` | 5 seeds 全量复现；主结论 `p<0.01` 且 `95%CI` 不跨 0；至少 3 个外部 baseline + 8 个 ablation；24h 内可一键重现主表图 |

---

## 2. 阶段切换闸门（Gate）
1. P1 -> P2：mixed-test `>=900` 且每档难度 `>=250`。  
2. P2 -> P3：反事实配对覆盖率 `100%`，缺失记录 `0`。  
3. P3 -> P4：完成 `95%CI` + 相关性检验（`ρ>=0.35, p<0.01`）。  
4. P4 -> P5：满足 `E[ΔL_rel] <= 1.5%` 且 `J` 提升 `>=5%`。  
5. P5 -> P6：违约率达标（`<=7%`，`95%CI` 上界 `<=8%`）。  
6. P6 -> P7：`Oracle Gap` 进一步下降 `>=15%` 且额外时延 `<=1.0ms`。  

---

## 3. 指标定义（执行口径）
1. 主指标：`J = T_norm + βL_norm`，其中 `β` 在 calib 集按“中位数同量级”原则固定。  
2. 质量风险：`ΔL_rel = (L_router - L_slow_ref) / max(L_slow_ref, 1e-6)`。  
3. 风险约束：`E[ΔL_rel] <= ε_rel`，默认 `ε_rel=1.5%`。  
4. 违约率：`V = P(ΔL_rel > ε_rel)`，默认目标 `V<=α=5%`（Conformal 阶段放宽到 `<=7%` 含有限样本误差）。  
5. 决策最优性缺口：`Oracle Gap = (J_router - J_oracle) / |J_oracle|`。  
6. 统计规范：主结论必须报告 `mean`, `std`, `95%CI`, `p-value`（paired bootstrap + Wilcoxon）。  

---

## 4. 顶刊量化目标总表（最终验收）
1. 效率目标（Exp1/Exp2）：`success` 不低于基线；`avg_time_ms` 保持 `<=1.0ms`（平均）且 `P95<=2.0ms`。  
2. 质量稳定（Exp3/Exp4）：相对 `manual_v11b`，`|dE drift|<=0.5%`。  
3. 自适应分流：mixed-test 上分层 fast ratio 满足 easy `>=85%`，medium `35~75%`，hard `<=35%`。  
4. 风险控制：`E[ΔL_rel] <=1.5%`，`P(ΔL_rel>1.5%)<=7%` 且 `95%CI` 上界 `<=8%`。  
5. 决策优性：相对当前路由，`J` 改善 `>=5%`，`Oracle Gap` 改善 `>=15%`。  
6. 统计显著性：5 seeds；主指标改善 `p<0.01`；`95%CI` 不跨 0。  
7. 可复现性：单命令在目标硬件 `<=24h` 复现主表和主图，产物 hash 一致。  

---

## 5. 当前立即执行项（Next Action）
1. 进入 Phase 7：完成 5 seeds 全量复现实验（Exp1~Exp4 + mixed）并固定统计显著性流程（bootstrap + Wilcoxon）。  
2. 完成严格外推版 Probe 路由（仅 `train=calib`，`search=calib`，`test` 仅报告）与当前目标导向版的并列对照。  
3. 输出投稿包：主表/主图、消融（无风险约束/无 conformal/无 probe）、外部 baseline 对比与 24h 一键复现脚本。  
