# NeurIPS/ICML 主线任务书（当前 strict 主线版）

更新日期：2026-03-06

本任务书只保留 **当前仍会延续的主线内容**：
- 冻结协议与严格口径；
- 当前有效的 strict 主结论；
- 当前距离 `NeurIPS/ICML` 的真实差距；
- 后续必须完成的、以“方法级贡献”为核心的工作。

> Frozen protocol 仍以 `docs/router_protocol_v1.md` 为准。
> 当前主线如何映射到该冻结协议，统一见 `docs/router_protocol_v1_current_mainline_note.md`。

---

## 0. 当前状态（一句话版本）

当前仓库的 **strict 主方法** 已经不再是历史上的 `dual-path probe router`，而是：

- **Risk-Calibrated Compute Shaping / Weighted-Search Tree Portfolio**
- 当前最佳实现：`O / TreeWeightPortfolio`
- 主证据链：`Phase29 -> Phase13 -> Phase22`

当前真实结论：
1. **旧的 probe-router 主结论在 strict 下不成立**；
2. **新的 zero-probe weighted-search compute-shaping 主结论在 strict 下成立**；
3. **但当前创新度与证据形态仍不足以宣称已达到 NeurIPS/ICML 稳中稿水准**。

当前最重要的 evidence roots：
- 主线说明：`README.md`
- 顶层拆解：`INTRO.md`
- 协议映射说明：`docs/router_protocol_v1_current_mainline_note.md`
- 当前主方法筛选：`reports/router_phase29_step12r4_trials_v1.md`
- 当前 strongest-baseline 结果：`reports/router_phase13_sota_v10_strict_weighted_tree_o.md`
- 当前 direct-baseline 结果：`reports/router_phase22_direct_baselines_v10_strict_weighted_tree_o.md`
- 效果来源审计：`reports/router_effect_source_audit_v3.md`
- 历史 strict 负结果：`reports/router_strict_audit_v2.md`

---

## 1. 当前主线的诚实判定

### 1.1 当前已经成立的内容
1. 在 frozen strict protocol 下，`O / TreeWeightPortfolio` 的全链路主结论成立；
2. 该正结果来自 **zero-probe、单搜索内部 compute-shaping**，不是来自额外 probe；
3. Phase13 与 Phase22 的当前正结果都已完成严格复核；
4. 当前 strict 主线没有发现明显的数据泄露、伪造结果、下游评测错配或 hash 绑定缺失问题。

### 1.2 当前不能过度声称的内容
1. 不能再把当前主结论写成“旧 dual-path probe router 被 strict 审计后仍然成立”；
2. 不能把当前结果过度声称为“adaptive tree routing 本身带来了主要增益”；
3. 不能把当前结果表述成“在一般路径质量意义下显著更优”；
4. 不能把当前 direct-baseline 比较表述成“在旧 flip-budget 语义下赢过更强的 CRC/CDT”。

### 1.3 当前最关键的限制
1. 当前主质量代理仍是 frozen protocol 下的 `L = node expansions`；
2. weighted-search arm family 与该指标天然高度对齐；
3. 当前 `tree selector` 相对简单常数/分组 weighted baselines 的附加收益很小；
4. 因而当前正结果 **真实，但更像“方法雏形 + 严格证据成立”**，还不是顶会级方法结论。

---

## 2. 冲击 NeurIPS/ICML 的总目标

目标不是继续修补旧 probe-router，也不是继续堆工程实验；
而是把当前 strict 主线升级成一个 **可单独论道的、方法上更完整的新方法**。

最终目标表述为：

> 在不改变 frozen protocol 的前提下，提出一种 **风险校准的单搜索 compute-shaping policy**，能够在 strict 语义下显著优于固定 weighted-search 与最近邻强基线，并给出直接支撑当前主方法的理论与泛化证据。

为达到 `NeurIPS/ICML Ready`，至少要同时满足：
1. **方法门**：新方法必须显著优于当前 `M / WAStarConst` 与 `N / DifficultyWeightPortfolio`；
2. **理论门**：至少两条 theorem 直接支撑当前主方法，而不是历史 probe 线；
3. **基线门**：必须与最近邻方法正面对齐，而不只是对齐远邻基线；
4. **指标门**：除了 `expansions` 主口径外，还要证明路径质量等辅助口径不崩；
5. **泛化门**：不能只在当前单套 strict benchmark 上有效。

---

## 3. 不变量（后续所有步骤必须遵守）

1. **协议冻结**：`docs/router_protocol_v1.md` 不得被追溯性修改；
2. **协议解释统一入口**：当前主线与冻结协议的对应关系统一引用 `docs/router_protocol_v1_current_mainline_note.md`；
3. **strict split 不动**：所有搜索、模型选择、阈值选择、结构搜索只能用 `calib_train/calib_val`；`test` 只做一次最终评估；
4. **sha256 绑定不动**：所有关键输入 parquet 必须有 sha256 绑定与 mismatch 检查；
5. **诚实记账不动**：任何新方法都必须 honest accounting，不允许把额外模块成本藏出主目标；
6. **不回到旧 probe 主叙事**：历史 probe 线只作为负结果、背景与框架层理论资产；
7. **不做 purely engineering patch**：若新增模块不能形成单独的方法贡献，不应进入主线；
8. **所有新 claim 都必须有完整证据链**：代码 + outputs + reports + paper tables/figures + 文档同步。

---

## 4. 当前距离 NeurIPS/ICML 的真实差距

### Gap A：方法主体还不够强
当前主增益主要来自 **weighted-search arm family 本身**，而不是 `tree selector` 本身；
因此当前主线仍容易被审稿人理解为：
- “一个很合理的 weighted A* 变体/组合”，而不是
- “一个足够独立的新方法类”。

### Gap B：最近邻 baseline 还不够到位
当前 strongest/direct baselines 已有意义，但还缺最相近的文献脉络：
- bounded-suboptimal search / weighted-A* family；
- heuristic selection / dynamic algorithm configuration；
- policy-guided search；
- prediction portfolio / learning-to-defer / multi-expert deferral。

### Gap C：理论尚未直接服务当前主方法
当前仓库里已有理论资产很有价值，但多数属于：
- 历史 probe-router 线；或
- 更框架层的 portfolio / risk 视角。

要冲 NeurIPS/ICML，需要把理论直接钉在 **当前 compute-shaping 主方法** 上。

### Gap D：指标语义仍偏窄
当前 frozen protocol 的主质量代理是 `expansions`，而 weighted A* 正好天然适配该指标；
因此必须补充：
- 路径质量辅助口径；
- 或双口径一致性；
- 或至少辅助协议下的稳定结论。

### Gap E：泛化证据不够像顶会主方法论文
当前 strict 主结果已经跨多个 benchmark/source 成立，但仍不够说明：
- 方法不是只对当前数据有效；
- 方法不是只对当前离散权重集有效；
- 方法对不同预算 regime / 地图分布 / 搜索场景都稳定。

---

## 5. 当前主线的未来执行方案（NeurIPS/ICML 冲击版）

> 下面只保留未来还会继续推进的步骤。旧步骤的细节过程不再在本任务书里展开；已完成的历史基础设施与审计资产只作为底座保留。

### Step 13：冻结论文主 claim 与评测契约
状态：`DONE`
是否需要模型/方法修改：`否`

完成情况（`2026-03-06`）：
1. 新增 paper-facing 契约文件：`paper/router_current_mainline_claim_contract.md`；
2. `README.md` / `INTRO.md` / `docs/neurips_method_v1.md` / `docs/router_theory_v3.md` / `paper/` 主文档均已同步到该契约；
3. 当前主方法的 canonical paper-facing 表述已经冻结为 **Risk-Calibrated Single-Search Compute Shaping**；
4. 本阶段只同步文档与 claim contract，不修改任何评测代码、split、协议常数或结果文件，因此不会引入新的数据泄露或协议口径不一致问题。

目标：
1. 彻底冻结当前论文主句；
2. 明确“当前主方法 / 历史主线 / frozen protocol / 辅助指标”的边界；
3. 避免后续实现与文档继续漂移。

必须完成：
1. 在文档中统一主表述为：
   - **risk-calibrated single-search compute shaping**；
   - 而非旧 dual-path probe router；
2. 明确写出当前主结论的适用域：
   - frozen protocol；
   - `L = expansions` + path audit；
   - current public strict benchmarks；
3. 明确列出当前不能声称的点。

验收：
- `README.md` / `INTRO.md` / `docs/neurips_method_v1.md` / `docs/router_theory_v3.md` / `paper/` 主文档的叙事完全一致。

---

### Step 14：做出真正的新方法模块（NeurIPS/ICML 主方法）
状态：`IN_PROGRESS（2026-03-06：A/B/C/D 已按 strict calib-only 逐个尝试；本轮无候选通过 Step 14 验收，因此未进入 test）`
是否需要模型/方法修改：`是（关键步骤）`

> 核心要求：必须具备足够的创新性。不能照抄别人的方法；切忌做成纯工程化实现。
> 当前主线协议映射与非变更项统一遵守 `docs/router_protocol_v1_current_mainline_note.md`。

本轮已完成（`2026-03-06`）：
1. 基于 frozen protocol + current-mainline note 重新冻结 Step 14 不变量；
2. 完成一轮文献勘察，重点覆盖 `NeurIPS / ICML / ICLR / AAAI / ICAPS` 邻近脉络；
3. 冻结 Step 14 候选方案队列与执行顺序；
4. 已实现并按 `calib_train/calib_val` 逐个严格筛查 `14-A / 14-B / 14-C / 14-D`；
5. 为避免 test 口径污染，仅当候选在 `calib_val` 上同时打赢 `M/N/O` 且通过 risk/path gate 时才允许进入 test；本轮没有候选达到该条件，因此 **test 未被消耗**。

直接影响 Step 14 设计的文献脉络（只保留与当前主线最相关者）：
1. **prediction portfolio / algorithm-with-predictions**：
   - `Algorithms with Prediction Portfolios`（NeurIPS 2022）
   - `Online Algorithms with Uncertainty-Quantified Predictions`（ICML 2024）
   启发：当前方法不应只做 best-arm 分类，而应显式建模“预测 + 不确定度 + 选择”的耦合。
2. **learned search guidance with guarantees**：
   - `Single-Agent Policy Tree Search With Guarantees`（NeurIPS 2019）
   - `Policy-Guided Heuristic Search with Guarantees`（近邻搜索脉络；Step 16 也将正面对齐）
   启发：学习模块必须直接落到搜索 effort / suboptimality / guarantee 上，不能只给经验打分。
3. **dynamic algorithm configuration for search**：
   - `Learning Heuristic Selection with Dynamic Algorithm Configuration`（AAAI 2021）
   启发：如果静态实例特征不足以明显超越 `M/N`，则必须考虑 search dynamics，而不是继续堆浅层树。
4. **finite-sample risk control / conformal selection**：
   - `Conformal Risk Control`
   - `Learn then Test`
   - `Quantile Learn-Then-Test`
   - `Automatically Adaptive Conformal Risk Control`
   启发：新方法必须把 feasible-set / risk envelope 的选择留在 `calib_train/calib_val` 内完成，不能用 test 试出来。
5. **defer / multi-expert selection**：
   - `Two-Stage Learning to Defer to Multiple Experts`
   - `Regression with Multiple Expert Deferral`
   启发：当前权重臂本质上是有序 expert family，不能继续把它当普通 multiclass label 去做平面分类。

排除项（Step 14 不再重复的方向）：
1. 历史 `probe` / `prefix-reuse` / 外置额外计算主线；
2. 已完成筛选的 `K/I/J/L` 系列；
3. 已成立但创新度不足的 `M/N/O/P` 静态 weighted-search portfolio 系列；
4. 任何只是在现有浅树上继续堆 feature、但没有新方法对象与理论接口的改造。

候选方案队列（按执行顺序冻结为 `14-A -> 14-B -> 14-C -> 14-D`）：

#### 14-A：RCWS-Q — Risk-Calibrated Weight Surface with Quantile LTT
类型：`需要新增模型模块（轻量）`
目标：从“样本 -> 离散 arm 分类”升级为“(特征, 预算) -> 连续/有序 weight surface `w(x,b)`”。
核心设计：
1. 用当前 counterfactual weight tables 拟合 `J(w|x)` 与 `ΔL_rel(w|x)` 的 surrogate；
2. 在 `calib_val` 上用 `Quantile Learn-Then-Test / CRC` 选出可行的 weight surface 超参数；
3. 在推理时选择“估计上最激进、但仍满足风险包络”的权重；
4. 显式加预算单调约束：预算更宽时允许更激进、但不更高风险的权重选择。
为什么它可能超越 `M/N/O`：
- `M/N/O` 只学静态 `leaf -> arm` 映射，没有显式建模 ordered weight ladder 的连续结构；
- `RCWS-Q` 直接优化“有序权重面 + 分位风险包络”，理论和方法对象都更像一个新方法。
最低验收：
1. test 前在 `calib_val` 上不能塌缩成单一常数权重；
2. strict test 下显著优于 `M` 与 `N`；
3. 选中权重分布必须展示真实 instance differentiation，而不是 95% 以上都回到 `wa_w135`。
失败判据：
- 最终 surface 基本常数化；
- 相对 `M/N` 的 pooled CI 仍跨 0；
- `path audit` 或 `risk gate` 任一失败。

#### 14-B：PCSE — Pareto-Calibrated Search Envelope
类型：`需要新增模型模块`
目标：不再直接预测 best arm，而是预测整个 `weight -> (T, ΔL_rel, path_audit)` 包络，再做受约束决策。
核心设计：
1. 对每个样本预测多权重下的 trade-off envelope；
2. 把选择问题写成：
   `argmin_w  \hat T_norm(w|x) + beta * \hat L_norm(w|x)`
   s.t. calibrated risk / path constraints；
3. 用 split-conformal / LTT 在 `calib_val` 上给 envelope 决策加有限样本风险控制；
4. 可自然扩展到多 budget / 多 objective setting。
为什么它可能超越 `M/N/O`：
- 现有方法只会“选臂”；`PCSE` 直接建模整条 Pareto 结构；
- 若当前 benchmark 的最优权重集中在少数区间，envelope 学习比 leaf 分类更容易泛化。
最低验收：
1. 相比 `M/N/O` 至少在一个 pooled strict metric 上形成 clear margin；
2. 预测 envelope 与真实 counterfactual 排序具有稳定相关性；
3. 不是依靠 `path audit` 崩坏来换主指标。
失败判据：
- envelope 预测噪声过大导致选择退化到常数；
- 仅在单一 difficulty 上有效。

#### 14-C：OMWD — Ordered Multi-Weight Deferral
类型：`需要新增模型模块`
目标：把 weighted-search arm family 明确视作“有序多 expert 家族”，先学可行集，再在可行集中选择最激进 arm。
核心设计：
1. 第一阶段预测各 weight arm 的 `J / ΔL_rel / violation`；
2. 第二阶段做 conformalized feasible-set selection，而不是单点分类；
3. 决策规则改为“从可行集里选最省时 / 最激进 arm”；
4. 对 ordered arm family 加邻接一致性与 ordinal loss，避免把 `wa_w125` / `wa_w135` 当互不相关 label。
为什么它可能超越 `M/N/O`：
- 当前树分类忽略 arm 的有序结构；
- multi-expert deferral 脉络提示：在 ordered experts 上，先学 defer / feasible set 往往比硬分类更稳。
最低验收：
1. 相比 `O` 产生更丰富的 arm usage，而不是仍只选两个叶子常数；
2. strict 下显著优于 `M/N`；
3. feasible-set coverage 与 violation rate 在 `alpha=0.05` 下 honest 通过。
失败判据：
- feasible set 过宽，最后仍等价于常数策略；
- 或 feasible set 过窄，导致收益消失。

#### 14-D：SDAC-WA — Search-Dynamics Adaptive Compute for Weighted A*
类型：`需要新增 planner 模块`
目标：若 `14-A/B/C` 仍无法显著超越 `M/N`，则把适应性从“实例级”推进到“单搜索内部的阶段级”。
核心设计：
1. 不引入外置 probe；所有额外判断都在同一次 Weighted A* 内完成；
2. 仅在若干 milestone（如 expansions 阈值或 frontier 统计突变点）更新 weight；
3. 动态特征只来自当前搜索内部可观测量，如 `frontier entropy / duplicate ratio / g-h geometry / corridor proxies / RS disagreement`；
4. 保持单调 schedule 与 honest accounting：所有前缀 expansions 都保留，不允许丢弃后重跑。
为什么它可能超越 `M/N/O`：
- 若当前数据上静态 per-instance 选择空间几乎被常数权重吃满，剩余增益更可能来自 in-search dynamics；
- 这比继续堆更复杂的静态树更有机会形成真正的新方法点。
最低验收：
1. 不是 disguised probe；
2. search-dynamics feature 与最终 weight updates 有清晰可解释关系；
3. strict 下相对 `M/N/O` 的优势不再是噪声级 refinement。
失败判据：
- 动态控制带来的 accounting 成本抵消收益；
- 或本质上退化为 ARA* 式 schedule 而无当前主线独特性。

本轮冻结的执行顺序与停机规则：
1. 先做 `14-A`，因为它最贴近当前 counterfactual infrastructure，且最容易与 Step 15 理论闭环；
2. 若 `14-A` 明确失败，再做 `14-B`；
3. 若 `14-B` 仍失败，再做 `14-C`；
4. 只有当 `14-A/B/C` 都不能稳定打赢 `M/N`，才进入 `14-D`；
5. 每完成一个方案，都必须把“成功/失败 + 证据路径 + 是否进入下一方案”记回本任务书；
6. 任何方案一旦消耗 `test` 结果后，不允许基于同一 `test` 回头继续调参；若需继续迭代，必须新建版本并保持 `calib_train/calib_val` 内选型。

所有 Step 14 方案统一遵守的 strict guardrails：
1. 输入源只允许来自当前 frozen strict 主链路与其 hash 绑定产物；
2. 所有拟合 / 网格搜索 / 阈值搜索 / 校准 / 结构搜索仅允许用 `calib_train/calib_val`；
3. `test` 只用于每个冻结候选的最终一次性评估；
4. 所有输出必须写入独立 versioned 目录，并带 `inputs_parquet_sha256.json`；
5. 所有方案都必须产出：
   - `policy.json`
   - `seed_runs.csv`
   - `stats.json`
   - `report.md`
   - `ablation.csv`
   - `failure_cases.md`
6. 若 `risk gate / path audit / hash mismatch` 任一失败，该方案直接记为失败，不得进入主结论。

本轮阶段性验收结果：
1. `14-A -> 14-B -> 14-C -> 14-D` 已全部按 strict `calib_train/calib_val` 口径完成实现与筛查；
2. 所有候选都已产出独立 versioned outputs 与 `inputs_parquet_sha256.json`；
3. 本轮没有任何候选达到“允许进入 test”的前置条件，因此 `test` 未被消耗；
4. 当前主线保持 `O / TreeWeightPortfolio` 不变，Step 14 继续保持 `IN_PROGRESS`。

证据产物（本轮新增要求）：
- `TASK.md` 中保留上述计划；
- 后续实现阶段为每个方案单独新增 phase 输出目录；
- 与 `M/N/O` 的 head-to-head 对比表必须成为固定产物。

### 2026-03-06 本轮实现与结论
主报告：`reports/router_phase30_step14_trials_v1.md`  
总汇总：`outputs/router_phase30_step14_trials_v1/summary.json`

1. **14-A / RCWS-Q**（`outputs/router_phase30_step14_a_rcws_q_v1/`）  
   - 在 `calib_val` 上形成了真实的多权重使用（`wa_w120 / wa_w125 / wa_w135`），没有塌缩成常数；  
   - 但相对 `M` 的 pooled head-to-head `ΔJ=-0.000208`、相对 `N` 为 `-0.000577`，只相对 `O` 为正；  
   - 结论：**是目前最接近可行的新模块，但尚未达到 Step 14 的最低门槛**。
2. **14-B / PCSE**（`outputs/router_phase30_step14_b_pcse_v1/`）  
   - 在 strict `calib_val` 上退化为 `fast` 主导，风险 gate 不通过；  
   - 相对 `M/N/O` 的 pooled head-to-head 均大幅为负（约 `-0.91`）；  
   - 结论：**当前 envelope surrogate + constrained selection 设计失败**。
3. **14-C / OMWD**（`outputs/router_phase30_step14_c_omwd_v1/`）  
   - 与 `14-B` 类似，最终退化为近乎 `fast-only` 的保守策略；  
   - 风险 gate 未通过，且没有形成 ordered expert family 的有效使用；  
   - 结论：**当前多 expert deferral 设计失败**。
4. **14-D / SDAC-WA**（`outputs/router_phase30_step14_d_sdac_wa_v1/`）  
   - 已实现单搜索内 milestone-based dynamic weight switching，并生成独立动态 counterfactual 表；  
   - 但 `calib_val` 上相对 `M/N/O` 的 pooled head-to-head 分别为 `-0.003708 / -0.004078 / -0.000620`；  
   - 平均 switch rate 仅 `0.0349`，未达到“非平凡动态控制”的要求；  
   - 结论：**当前动态 compute shaping 设计没有带来足够剩余增益**。
5. **总判定**  
   - 本轮 `A/B/C/D` 全部已在 strict `calib_train/calib_val` 口径下完成尝试；  
   - 没有任何候选同时满足“打赢 `M/N/O` + risk/path gate 通过 + 非退化使用结构”，因此**没有候选被允许进入 test**；  
   - 当前 paper-facing mainline 继续保持 `O / TreeWeightPortfolio`，Step 14 **尚未完成**；  
   - 下一轮若继续推进 Step 14，需要重新设计新的方法对象，而不是继续在本轮四个失败形态上做小修小补。

---

### Step 15：把理论直接重构到当前主方法上
状态：`TODO`
是否需要模型/方法修改：`否（但与 Step 14 强耦合）`

目标：
让理论直接服务当前主方法，而不再主要服务历史 probe 线。

至少需要的理论块：
1. **bounded-suboptimality / path inflation 解释**：继承 weighted A* 质量界，并写清当前主方法如何落到该框架；
2. **risk-calibration guarantee**：对 `w(x,b)` 或其离散近似的风险控制给出 split-conformal / CRC 风格保证；
3. **best-in-family / oracle-regret guarantee**：相对最佳固定权重或最佳预算策略，给出有限样本上界；
4. 如果使用连续权重，还需补离散逼近或 surrogate 逼近误差说明。

验收：
1. 至少两条 theorem 直接指向当前主方法对象；
2. 至少一条 theorem 可由实验脚本验证；
3. 理论章节与主实验一一对应。

---

### Step 16：补齐最近邻强基线（必须 head-to-head）
状态：`TODO`
是否需要模型/方法修改：`否`

必须优先覆盖的近邻脉络：
1. `Type-WA*`（bounded-suboptimal exploration）
2. `Policy-Guided Heuristic Search with Guarantees`
3. `Learning Heuristic Selection with Dynamic Algorithm Configuration`
4. `Algorithms with Prediction Portfolios`
5. `Two-Stage Learning to Defer with Multiple Experts`
6. `Regression with Multi-Expert Deferral`

执行要求：
1. 至少实现其中 2~3 个最相近、最可落地的基线；
2. 保持同样的信息预算、同样 strict split、同样 honest accounting；
3. 不允许对 baseline 使用更弱协议；
4. 若无法完全复现，必须给出“为何不可直接对齐 + 已做的最公平替代”说明。

验收：
- 至少与一个真正近邻强 baseline 形成可写进主文的正面对比，并非只对比远邻。

---

### Step 17：补齐双口径指标与辅助协议验证
状态：`TODO`
是否需要模型/方法修改：`否`

目标：
解决“当前主结果主要建立在 `L = expansions` 口径上”的 claim-scope 限制。

必须完成：
1. 保留 Protocol V1 主口径不动；
2. 新增至少一组辅助主实验：
   - path cost / path length；或
   - `J_exp` 与 `J_path` 双口径；或
   - 明确的 Pareto 图；
3. 写清主结论与辅助结论之间的关系；
4. 明确说明当前方法不是依靠灾难性路径退化来换取主指标提升。

验收：
1. 辅助口径下不出现原则性崩塌；
2. 论文中可诚实写成“主赢在 Protocol V1，辅助口径保持稳定/可接受”。

---

### Step 18：做真正像 NeurIPS/ICML 的消融与泛化
状态：`TODO`
是否需要模型/方法修改：`视 Step 14 实现而定`

必须完成的消融：
1. 无校准 vs 有校准；
2. 固定权重 vs 分组权重 vs 树分区 vs 新方法；
3. 仅预测质量损失 vs 联合预测 `T + ΔL_rel`；
4. 无预算条件 vs 有预算条件；
5. 无结构约束 vs 单调结构约束；
6. 与 `M/N/O` 的分步收益分解。

必须完成的泛化：
1. 不同地图分布 / 难度分布；
2. 不同 budget regime；
3. 至少一个更接近机器人搜索的问题族（若本轮不做实机，则至少做更高保真搜索设定）；
4. 明确 OOD 或 distribution shift 下的表现。

验收：
1. 能清楚回答“究竟是什么设计带来了增益”；
2. 方法不只是当前 benchmark 上的特化技巧；
3. 泛化结果足以支撑“方法论文”而非“数据集命中”。

---

### Step 19：NeurIPS/ICML go/no-go 收口
状态：`TODO`
是否需要模型/方法修改：`否`

目标：
在所有关键 evidence 就位后，诚实判定是否真的达到 `NeurIPS/ICML Ready`。

通过条件（全部满足才算通过）：
1. Step 14 的新方法在 strict 下显著优于 `M` 与 `N`；
2. Step 15 的理论直接服务当前主方法；
3. Step 16 至少打赢一个最近邻强 baseline；
4. Step 17 的辅助口径不崩；
5. Step 18 的消融与泛化完整且不揭穿方法本身；
6. 文档、表格、图、报告、复现命令全部同步。

若未满足：
- 不得继续硬写 `NeurIPS/ICML Ready`；
- 应诚实改投更匹配的 venue（优先 `ICAPS / SoCS / RA-L / RSS-style planning track`）。

---

## 6. 当前保留的底座资产（不再展开历史过程）

这些内容已完成，可作为当前主线的底座复用，但不再作为任务书主体展开：
1. strict split / hash 绑定 / 泄露修复链路；
2. 历史 probe 线的负结果审计；
3. 当前 weighted-search 主线的 strict-positive 复跑；
4. README / INTRO / method / theory / protocol note 的当前主叙事同步；
5. camera-ready 风格的工程复现基础设施。

必要时查阅：
- `reports/router_strict_audit_v2.md`
- `reports/router_validity_audit_v2.md`
- `reports/router_phase29_step12r4_trials_v1.md`
- `reports/router_effect_source_audit_v3.md`
- `outputs/final_v5_strict/manifest.json`
- `paper/router_current_mainline_claim_contract.md`

---

## 7. 当前阶段的明确判断

### 7.1 已达到什么
- 已达到：**strict 下当前主结论真实成立**；
- 已达到：**当前主线从旧 probe-router 成功切换到 zero-probe weighted-search compute-shaping**；
- 已达到：**较强的审计可信度与复现可信度**。

### 7.2 还没达到什么
- 还没达到：`NeurIPS/ICML Ready`；
- 还没达到：一个显著强于简单 weighted baselines 的新方法主体；
- 还没达到：直接支撑当前主方法的理论闭环；
- 还没达到：足够强的最近邻 baseline 对比与双口径泛化证据。

### 7.3 当前最优策略
- 不要再回到旧 probe-router recovery；
- 不要把时间主要花在文档润色或继续堆远邻 baseline；
- 资源应优先投入 `Step 14 -> Step 16 -> Step 17 -> Step 18`。

---

## 8. 投稿策略建议（仅作任务收口时参考）

1. 若 Step 14~19 全部通过：可认真冲 `NeurIPS/ICML`；
2. 若 strict 主结果仍成立，但新方法始终不能明显超越 `M/N`：
   - 更适合 `ICAPS / SoCS / RA-L / RSS-style planning track`；
3. 若后续补出更强机器人任务外延，但方法创新仍一般：
   - 更适合机器人系统/规划向 venue，而非 ML 顶会；
4. 若未来还要冲 `TRO/IJRR`：
   - 需在本任务书之外另开“高维/连续/机器人系统外延”任务书；
   - 当前版任务书只服务 `NeurIPS/ICML` 主方法冲线。
