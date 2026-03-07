# NeurIPS/ICML 主线任务书（当前 strict 主线版）

更新日期：2026-03-07

本任务书只保留 **当前仍会延续的主线内容**：
- 冻结协议与严格口径；
- 当前有效的 strict 主结论；
- 当前距离 `NeurIPS/ICML` 的真实差距；
- 后续必须完成的、以“方法级贡献”为核心的工作。

> Frozen protocol 仍以 `docs/router_protocol_v1.md` 为准。
> 当前主线如何映射到该冻结协议，统一见 `docs/router_protocol_v1_current_mainline_note.md`。

---

## P0. RS 根基补强优先级清单（最高优先级，先于所有后续任务）

> 这是当前任务书中 **优先级最高** 的前置清单。  
> 在“`RS 代价场` 这一核心创新点本身”尚未被补强到足够稳固之前，后续所有上层方法设计（包括 Step 14 的继续冲刺、Step 15~19 的论文化收口）都不应被当作主矛盾的替代品。

### P0.1 当前对 `RS 代价场` 的诚实判断

当前已经成立、且比较 solid 的内容：
1. `RS 代价场` 是当前系统可解性的关键底座：去掉 `RS` 后，`parasol` 与 `parasol:narrow_passage` 的成功率明显崩塌；
2. 在普通环境（如 `mp/csm`）上，基于该底座训练出的模型在 **扩展节点数** 上可大致维持与 `A*` 同级，不会系统性恶化；
3. 在当前 fair 口径下，相对最接近的 `Hybrid A* (RS)` 已存在正收益，但幅度仍偏小；
4. “显著快于 `Kinodynamic BIT* / RRT*`”这一说法目前并不在所有公平口径下稳定成立，因此**不能**继续把它当作最核心、最稳固的根基性结论。

因此，当前 `RS 代价场` 的状态是：
- **必要性 / 有效性已经较强成立**；
- 但“至少在某一方面达到足够硬的、可作为 NeurIPS/ICML 根基的 SOTA 级优异性”**尚未完成**。

### P0.1b 当前定位调整（2026-03-07）

基于 `P0-C` 已完成的多轮证据，当前必须做一个定位调整：
1. **纯 `RS-only` 根基线** 已经证明了必要性与有效性，但尚未在 `mp/csm/parasol_narrow` 上建立足够硬的优势轴；
2. 因而 `P0` 阶段当前的**主实施目标**不应再被理解为“继续榨纯 `RS-only` marginal gain 直到自然变成 SOTA”；
3. 从现在起，`P0` 的主目标调整为：
   - 以 `RS 代价场` 为根基；
   - 允许引入**基础模型层面**的模块/方法创新；
   - 但创新必须直接服务 `RS` 根基主线，而不是跳到更高层的 router / portfolio 叙事；
   - 最终在 `mp/csm/parasol_narrow` 三类实验上建立一个**独特且显著的优势区间**。
4. `P0-A/B/C` 的角色因此调整为：
   - `P0-A`：冻结根基主口径；
   - `P0-B`：扩充 hard benchmark；
   - `P0-C`：给出纯根基线在最近邻强基线前的边界诊断；
   - 它们继续保留，且必须作为后续参考，但不再是 `P0` 唯一的主实施任务。

### P0.1c 基于 P0-C 四轮结果的 go / no-go 判断（2026-03-07）

当前判断：
1. **No-Go**：继续把“纯 `RS-only` 根基线 + 不改基础模型”当作当前主攻方向，去硬凿 `Hybrid A* (RS)` 上的显著优势轴；
2. **Go**：以 `RS 代价场` 为底座，转入 `P0-CX` 所定义的**基础模型层面创新主线**，去建立显著优势区间；
3. `P0-C` 继续保留，但其角色从“主攻目标”收缩为：
   - 最近邻强基线前的边界诊断；
   - 证明当前纯根基线尚未过线；
   - 为后续 `RS-grounded` 方法创新提供对照与约束。

这个判断的含义是：
- 不能再把主要资源投入到继续细修纯 `RS-only` 根基线；
- 若仍坚持 `NeurIPS/ICML` 主目标，必须把主要资源转到 `P0-CX -> P0-D -> P0-E -> P0-F/G/H` 这条更像“基础模型主方法”的路线；
- 只有在该路线先建立起显著优势区间后，后续更高层的方法/论文包装才有稳固基础。

### P0.2 必须补齐的条件（缺一不可）

#### P0-A：冻结一条单一、公平、不可摇摆的 RS 根基主口径
状态：`DONE（2026-03-07：已冻结 RS Root Protocol V1；主证据链、主/辅基线角色与禁止叙事均已固定）`
目标：不再允许通过改变预算上限、采样迭代数或对手口径来得到不同叙事。

完成情况（`2026-03-07`）：
1. 新增冻结协议文档：`docs/rs_field_root_protocol_v1.md`；
2. 新增冻结证据报告：`reports/rs_root_protocol_v1.md`；
3. 新增机器可读 manifest：`outputs/rs_root_protocol_v1/manifest.json`；
4. 已明确：
   - `Hybrid A* (RS)` 是 `RS` 根基主 claim 的**主对手**；
   - `Kinodynamic BIT* / RRT*` 仅为**辅助对手**；
   - `mp/csm` 普通环境结果仅作**辅助支持口径**；
5. 已明确禁止继续把非 fair 口径下的 `BIT* / RRT*` 时间优势写成 `RS` 根基主结论。
必须完成：
1. 为 `RS 代价场` 根基结论单独冻结 **唯一主口径**：
   - 数据集；
   - 预算；
   - 成功定义；
   - 时间统计方式；
   - 扩展节点统计方式；
   - 近邻基线集合；
2. 对 `Hybrid A* (RS)`、`Kinodynamic BIT*`、`Kinodynamic RRT*` 明确说明：
   - 哪一个是主对手；
   - 哪些只是辅助对手；
   - 哪些不能直接拿来当主 claim；
3. 在文档中明确写出：**只允许用这条冻结口径支持 `RS` 根基主结论**。
验收：
- 后续所有文档/表格/口头结论都不再出现“换口径后才成立”的主 claim。

#### P0-B：把“高难狭窄环境”补成真正可统计的 benchmark
状态：`DONE（2026-03-07：已构建 test-only 的 rs_root_hard_v1 benchmark，并完成分布审计）`
目标：不能再让 `parasol_narrow` 中极小样本量成为根基结论的薄弱点。

完成情况（`2026-03-07`）：
1. 新增 benchmark 构建脚本：`scripts/build_rs_root_hard_benchmark_v1.py`；
2. 构建完成新的 test-only hard benchmark：`data/benchmark/rs_root_hard_v1/`；
3. 新增 benchmark 审计报告：`reports/rs_root_hard_benchmark_v1.md`；
4. 新增机器可读 manifest：`outputs/rs_root_hard_benchmark_v1/manifest.json`；
5. 当前新 benchmark 的 test 规模已从旧 `parasol_narrow` 的 `18` 个样本扩展到 `78` 个样本（`18` public anchor + `60` synthetic hard），并显式区分了：
   - `narrow_passage`
   - `maze`
   - `deadend_labyrinth`
   - `bug_trap`
   - `alpha_puzzle`
   - `flange`
   - 以及保留的 `parasol_misc` anchor；
6. 为避免泄露与协议错配：
   - 新 benchmark 保持 **test-only**；
   - 不并入任何训练/校准 split；
   - 分辨率、vehicle/planner 基本设定保持与当前 `parasol_narrow` 主线一致；
7. 另外已新增专用评测脚本 `scripts/eval_rs_root_hard_v1.py`，用于后续在该 benchmark 上单独报告 `RS` 根基结论；并已完成 `20` case smoke 复核：`reports/rs_root_hard_v1_exp3_smoke.md`（显示 `Full` 相对 `No-RS` 成功率明显更高，且相对 `No-Residual` 在扩展/时间上保持正收益）。
8. 在此基础上，已进一步补充更标准化的 `v2` 版本：
   - `data/benchmark/rs_root_hard_v2/`（新增 `dev/test` 分离）；
   - `data/benchmark/rs_root_hard_v2/dev_index.csv` 与 `data/benchmark/rs_root_hard_v2/test_index.csv`；
   - `docs/rs_root_hard_benchmark_card_v1.md`（benchmark card）；
   - `reports/rs_root_hard_benchmark_v2_quality.md`（样本质量审计，按 `split/family` 报告可解性、几何难度、path stats）；
   - `paper/tables_rs_root_v1/table_rs_root_anchor_only_comparison.csv`（只保留原始 public anchor test 的对照表，避免 synthetic 扩展掩盖公开结果）。
必须完成：
1. 扩充或重组一套 **高难狭窄环境评测集**，使其规模足以支持统计结论；
2. 明确区分：
   - `narrow_passage`；
   - `maze / bug-trap / flange / alpha` 等其它 hard scenes；
3. 给出每类场景的样本数、地图数、难度分布；
4. 在该集合上单独报告 RS 根基结论，而不是把所有 hard scenes 混在一起掩盖差异。
验收：
- “RS 在高难狭窄环境下有明显优势”这句话可以建立在足够的样本量上，而不是只靠极少数 case。

#### P0-C：在最接近的强基线上，至少拿下一个足够硬的优势轴
状态：`IN_PROGRESS（2026-03-07：已完成四轮协议干净的 P0-C 尝试；当前仍未建立足够硬的优势轴）`
角色：`纯 RS-only / 冻结根基线 的边界诊断与参考，不再是 P0 唯一的主实施任务`
目标：让 `RS 代价场` 至少在某一个维度上能被写成“充分优异”。

本轮尝试（`2026-03-07`）：
1. 新增专用脚本：`scripts/run_rs_root_p0c_axis_v1.py`，用于在 `rs_root_hard_v2` 上对固定 budget cap 做 `dev` 选择，再在 `test` 上一次性验证；
2. 由于全量 `test` nearest-baseline 运行耗时较长，本轮先完成了：
   - `dev` 分层子集上的 cap 选择；
   - `public-anchor-only` test 子集上的一次性验证；
3. 该尝试的正式记录：
   - `reports/rs_root_p0c_axis_v1.md`
   - `outputs/rs_root_p0c_axis_v1/manifest.json`
   - `paper/tables_rs_root_v1/table_rs_root_p0c_attempt_anchor_only.csv`
4. 第一轮结果：
   - 在 `dev` 分层子集上，`cap=3500` 对 `Hybrid A* (RS)` 呈现正向迹象（`dE≈-5.54%`, `dT≈-4.83%`, success 持平）；
   - 但在 `public-anchor-only` test 子集上，该 cap 未能转化为更强优势轴（success 持平，且 `dE/dT` 反而略差）；
   - 因而第一轮 **尚未** 达成 P0-C 的目标。
5. 第二轮固定协议验证（`2026-03-07`）：
   - 新增脚本：`scripts/run_rs_root_p0c_axis_round2_v1.py`；
   - 固定上一轮 `dev` 选出的 `cap=3500`，不再搜索 budget cap；
   - 预先固定高约束 family 子集为 `{narrow_passage, maze, deadend_labyrinth}`，并分别在：
     - `rs_root_hard_v2:dev::high_constraint_all`
     - `rs_root_hard_v2:test::high_constraint_all`
     - `rs_root_hard_v2:test::public_anchor_only`
     上进行一次性验证；
   - 新增正式产物：
     - `reports/rs_root_p0c_axis_round2_v1.md`
     - `outputs/rs_root_p0c_axis_round2_v1/manifest.json`
     - `paper/tables_rs_root_v1/table_rs_root_p0c_round2_fixed_axis.csv`
   - 结果显示：
     - 在 `test::high_constraint_all` 上，success 仍完全持平；expansions 仍为负向（`base - ours ≈ -13.24`，即 `Ours` 平均扩展更多），且 CI 跨 0；time 也未形成稳定改善；
     - 在 `test::public_anchor_only` 上，success 仍持平；expansions 反而略差（`base - ours ≈ -5.0`），time 也未形成稳定改善；
   - 因而第二轮结论是：**此前关于“高约束 family 上 expansions 可能变硬”的判断过于乐观；按当前符号定义，第二轮并未显示出正向 expansions 优势**。
6. 第三轮 expansion-focused dev-only 搜索（`2026-03-07`）：
   - 新增脚本：`scripts/run_rs_root_p0c_axis_round3_v1.py`；
   - 固定 `cap=3500` 与 family 子集 `{narrow_passage, maze, deadend_labyrinth}`；
   - 不再搜索 budget cap，只在 `dev::high_constraint_all` 上搜索少量残差推理参数（`residual_alpha / residual_open_boost`），目标专攻 `expansions` 轴；
   - 新增正式产物：
     - `reports/rs_root_p0c_axis_round3_v1.md`
     - `outputs/rs_root_p0c_axis_round3_v1/chosen.json`
     - `paper/tables_rs_root_v1/table_rs_root_p0c_round3_expansion_focus.csv`
   - 第三轮结果：
     - `dev` 上最优配置也未把 expansions 轴翻正（最佳 `base - ours ≈ -6.42`）；
     - `test::high_constraint_all` 上仍为弱负（`base - ours ≈ -0.68`, CI 跨 0）；
     - `test::public_anchor_only` 上仍为显著负向（`base - ours ≈ -4.0`, CI 完全小于 0）；
   - 因而第三轮结论是：**围绕高约束 family 的 expansions 轴进行更强统计支撑后，当前证据反而更清楚地表明：这一轴尚未被建立，且现阶段并不是 `RS` 根基最容易变硬的优势轴**。
7. 第四轮 success-under-budget 固定协议验证（`2026-03-07`）：
   - 新增脚本：`scripts/run_rs_root_p0c_axis_round4_v1.py`；
   - 延续固定 `cap=3500` 与高约束 family 子集 `{narrow_passage, maze, deadend_labyrinth}`；
   - 不再做 budget 搜索，而是围绕“`success-under-budget` 是否能成为更硬优势轴”做定向验证，并同时保留 `high_constraint_all` 与 `public_anchor_only` 两个 test 视图；
   - 新增正式产物：
     - `reports/rs_root_p0c_axis_round4_v1.md`
     - `outputs/rs_root_p0c_axis_round4_v1/chosen.json`
     - `paper/tables_rs_root_v1/table_rs_root_p0c_round4_success_budget_focus.csv`
   - 第四轮结果：
     - `success-under-budget` 在 `dev/test` 两侧都继续与 `Hybrid A* (RS)` 持平，没有形成正向差；
     - `test::high_constraint_all` 上 expansions 仍为弱负（`base - ours ≈ -0.68`, CI 跨 0）；
     - `test::public_anchor_only` 上 expansions 仍为显著负向（`base - ours ≈ -4.0`, CI 完全小于 0）；
     - 因而第四轮结论是：**把主轴切换到 success-under-budget 后，当前 evidence 仍未能建立对 `Hybrid A* (RS)` 的更硬优势；这说明问题不在于“选错了优势轴表述”，而在于当前 RS 根基线相对该强基线的真实 margin 仍不足。**。
8. 当前总体判定：
   - `P0-C` 已完成四轮协议干净的尝试；
   - 当前对 `Hybrid A* (RS)` 最稳的说法仍是“某些子集上有弱趋势，但尚未建立足够硬的优势轴”；
   - 因而状态继续保持 `IN_PROGRESS`，但已接近 go/no-go 判断边界。
必须完成：
1. 优先对齐最接近的强基线：`Hybrid A* (RS)`；
2. 在冻结主口径下，至少拿下以下任一轴的**清晰优势**：
   - success / solvability under fixed budget；
   - time efficiency；
   - expansions / search effort；
   - 或 quality-efficiency Pareto 前沿；
3. 该优势必须：
   - 幅度足够明确；
   - 统计上成立；
   - 不是靠明显牺牲路径质量换来的。
验收：
- 至少存在一条可以被诚实写成 “`RS 代价场` 在 XXX 轴上达到当前最优/显著优于强基线” 的根基性结论。

#### P0-CX：基础模型显著优势区间构建（当前 P0 主实施任务）
状态：`IN_PROGRESS（2026-03-07：已完成首轮顶会/顶刊调研与候选路线冻结；下一轮开始逐条实现）`
是否需要模型/方法修改：`是（允许，但必须直接服务 RS 根基主线）`

目标：
在**不改变 P0-A 冻结主口径**的前提下，以 `RS 代价场` 为底座，通过基础模型层面的创新性设计，在 `mp/csm/parasol_narrow` 上建立一个可以被论文主文使用的**显著优势区间**。

这里所说的“基础模型层面”是指：
1. 允许修改或新增直接作用于 `RS field -> heuristic field -> planner guidance` 的模块；
2. 允许做残差场、校准场、结构约束、局部几何感知、场融合等创新；
3. 但**不允许**把任务偷换成更高层的 router / portfolio / policy selection 主线；
4. 必须能够拆分成：
   - `RS-only`；
   - `RS + 新模块`；
   - 必要时 `No-RS + 新模块`；
   从而证明增益来源。

主实验范围（必须优先完成）：
1. **`parasol_narrow / rs_root_hard_v2`**：这是建立“高难狭窄环境显著优势区间”的主战场；
2. **`mp`**：验证普通环境下 expansions 不崩，且新增模块代价可接受；
3. **`csm`**：验证中等复杂环境下不会因 hard-scene 优化而严重退化；
4. 以上三类实验必须构成当前基础阶段的主实验矩阵。

优势区间的合格定义（至少满足其一，并且不能靠别的轴原则性崩坏换来）：
1. 在 `parasol_narrow / rs_root_hard_v2` 上，相对 `Hybrid A* (RS)` 在以下任一轴形成**清晰且统计成立**的优势：
   - success-under-budget；
   - time efficiency；
   - expansions / search effort；
   - 或质量-效率 Pareto 前沿；
2. 同时在 `mp/csm` 上满足：
   - expansions 非劣或近似持平；
   - 时间代价可解释、可接受，不能出现原则性崩坏。

必须完成的实验：
1. `RS-only` vs `RS + 新模块` vs `No-RS` 的主消融；
2. `parasol_narrow / rs_root_hard_v2` 上与 `Hybrid A* (RS)` 的主对比；
3. `mp/csm` 上与 `A*` 的基础对比；
4. 至少一组 paper-facing 主表：
   - public-anchor-only；
   - expanded hard benchmark；
   - ordinary support (`mp/csm`)；
5. 至少一组能说明“优势区间在哪里、边界在哪里”的 family-wise 或 difficulty-wise 分解图/表。

验收：
1. 可以诚实写出一条主句：
   - “在 XXX 区间 / XXX family / XXX 预算语义下，`RS` 根基模型 + 新模块显著优于最近邻强基线”；
2. 该主句必须建立在冻结协议、明确主对手、统计支撑和消融拆分之上；
3. 若做不到，则应诚实承认：当前 `RS` 根基线更适合作为强底座，而非已独立建立 SOTA 优势区间的主方法。

本轮已完成（`2026-03-07`）：
1. 重新梳理 `P0-CX` 的问题边界：不能跳到 router / portfolio 主线，必须围绕 `RS field -> heuristic field -> planner guidance` 这一基础模型链条；
2. 补做一轮面向顶会/顶刊的原始论文调研，重点覆盖：
   - `Path Planning using Neural A* Search`（ICML 2021）
   - `Neural Weighted A*`（joint cost+heuristic learning）
   - `A Differentiable Loss Function for Learning Heuristics in A*`
   - `Generalizable Motion Planning via Operator Learning`
   - `Conformal Prediction Sets with Limited False Positives`
   - `Guaranteed Prediction Sets for Functional Surrogate Models`
3. 在不直接复用上述方法对象的前提下，冻结一组 **RS-grounded 基础模型创新路线**，作为下一轮实现顺序与评估标准。

文献启发脉络（只保留与当前基础模型最相关者）：
1. **learned guidance map / differentiable search**：
   - `Path Planning using Neural A* Search`（ICML 2021）
   - `Neural Weighted A*`（2021）
   启发：学习模块可以直接作用于“搜索指导对象”，而不只是后处理评分。
2. **heuristic-specific training objective**：
   - `A Differentiable Loss Function for Learning Heuristics in A*`
   启发：若目标是减少 expansions，就不应只用普通回归损失，而应直接优化“过度扩展”的代理量。
3. **function-space / operator learning for value fields**：
   - `Generalizable Motion Planning via Operator Learning`
   启发：当前对象本质上是一个场，不只是单点回归；应考虑低秩 / operator / basis 的函数空间表示。
4. **set-valued / uncertainty-aware prediction with guarantees**：
   - `Conformal Prediction Sets with Limited False Positives`
   - `Guaranteed Prediction Sets for Functional Surrogate Models`
   启发：若要在 hard scenes 上建立显著优势区间，关键可能不是“更激进”，而是“更有选择地激进”，即对 correction field 的局部不确定性建模。

冻结候选路线（下一轮按 `CX-A -> CX-B -> CX-C -> CX-D` 顺序执行）：

##### CX-A：RS-Tube — RS Set-Tube Twin Field
类型：`需要新增基础模型模块`
核心想法：
1. 不再只输出单一 residual field，而是输出一对 **twin fields**：
   - optimistic correction field `r^- (x, y, θ)`；
   - conservative correction field `r^+ (x, y, θ)`；
2. 通过低秩 / basis 系数预测和局部 tube width 预测，形成一个 **set-valued residual tube**；
3. planner 在 open / easy 区域用更激进的 `RS + r^-`，在高不确定 bottleneck 区域自动回退到 `RS + r^+` 或纯 `RS`；
4. 训练目标不仅拟合场值，还直接惩罚“tube 过宽但收益不足”的情形。
与现有工作的差异：
- 不是 Neural A* 那种 end-to-end guidance map；
- 不是标准 conformal label set；
- 而是 **直接作用于启发场本体的 set-valued correction field**。
预期优势轴：
- `success-under-budget` 与 hard-family 下的 time / expansions。
理论抓手：
- tube width 有界时，planner 的偏离量相对 `RS` 可控；
- hard scenes 的失败样本可被解释为“局部 tube 过宽导致回退”。

##### CX-B：RS-BPF — RS Bottleneck Progress Field
类型：`需要新增基础模型模块`
核心想法：
1. 新增一个 auxiliary field，直接预测每个状态对“穿越瓶颈 / 逃离死胡同 / 逼近可通连通域”的 **topological progress potential**；
2. residual correction 不再全局同权叠加，而是由 progress field 做乘性/门控调制；
3. 这使得网络主要把容量集中在 `narrow_passage / maze / deadend` 中真正决定成功率的局部区域，而不是在 open space 平均发力。
与现有工作的差异：
- 不是手工 `open_boost / corridor_suppress` 参数；
- 不是 route-level regime selection；
- 而是 **直接预测一个局部拓扑推进场来调控 RS correction**。
预期优势轴：
- 高约束 family 上的 `success-under-budget`。
理论抓手：
- progress gate 非负且有界时，整体 heuristic 仍保持相对 `RS` 的有界偏移；
- 若 progress field 在 bottleneck 邻域单调，则可解释为“减少无效扩展”的定向机制。

##### CX-C：RS-DVP — RS Dual-Value Pair
类型：`需要新增基础模型模块`
核心想法：
1. 学两个 residual heads，而不是一个：
   - `ΔL_exp`：剩余 search effort / expansions 的修正；
   - `ΔL_path`：剩余 path-quality / path-cost 的修正；
2. planner 使用 budget-conditioned 的 lexicographic rule：
   - 先保证 fixed-budget success / effort margin；
   - 再在 path-quality 上做约束；
3. 训练时用 expansion-centric ranking loss + path-consistency loss，而不再只做 pointwise field regression。
与现有工作的差异：
- 不是 Neural Weighted A* 那种同时学图 cost 与 heuristic；
- 而是 **以 RS 为 analytical base，只学习两个与 budget/quality 直接对应的 residual criterion**。
预期优势轴：
- `success-under-budget` 和 `quality-efficiency Pareto`。
理论抓手：
- 若 `ΔL_exp` 的 margin 超过其 calibration slack，同时 `ΔL_path` 保持有界，则可给出“优先成功、不严重牺牲路径”的充分条件。

##### CX-D：RS-PMF — RS Prototype Memory Field
类型：`需要新增基础模型模块（高风险候选）`
核心想法：
1. 引入一个小型 prototype memory，存储 hard scenes 中典型的几何/拓扑 correction kernel；
2. 对每个 query 先在 latent geometry space 中检索若干 prototypes，再把检索到的局部 correction kernel 注入 residual field；
3. 目标是专门提升 `bug_trap / flange / maze / narrow_passage` 这类少数 hard mode 上的 sharp advantage。
与现有工作的差异：
- 不是 sample-level route memory；
- 不是 TARP 的 regime clustering；
- 而是 **field-level prototype retrieval + local correction composition**。
预期优势轴：
- hard families 上的局部成功率与 search-effort 优势。
理论抓手：
- prototype approximation error 与检索误差可作为附加项写入误差分解。

本轮冻结的执行顺序与停机规则：
1. **先做 `CX-A`**：因为它最直接对应当前 `RS + residual` 结构，改动最小、理论接口最清晰；
2. **再做 `CX-B`**：若 `CX-A` 仍不能把优势轴转正，则说明单纯 uncertainty tube 不够，需要显式 bottleneck progress 模块；
3. **再做 `CX-C`**：若 hard-scene 成功与普通场景稳定性冲突，就引入 dual-value pair 做显式 trade-off；
4. **最后做 `CX-D`**：只有当 hard-family pattern 明显但前述路线都不够时，才使用 prototype memory 这种高风险模块；
5. 每条路线都必须先在冻结口径与 `P0-A/B/C` 约束下完成：
   - `RS-only` vs `RS + module` vs 必要时 `No-RS + module`；
   - `parasol_narrow / rs_root_hard_v2`；
   - `mp/csm`；
   - public-anchor-only 与 expanded hard benchmark 双表；
6. 任一路线若无法在 `dev` 上形成明确候选优势区间，不得直接消费 `test`。

#### P0-D：把“RS 本体贡献”与“残差/上层网络贡献”彻底拆开
目标：证明真正的根本创新点是 `RS 代价场`，而不是上层组合偶然奏效。
必须完成：
1. 分开报告：
   - `No-RS`；
   - `RS-only`；
   - `RS + residual`；
   - 必要时 `RS + residual + calibration`；
2. 明确回答：
   - 哪些结论是 `RS` 单独就能撑起来的；
   - 哪些只是上层 refinement；
3. 不能再把“完整系统好用”直接等同于“RS 本体已经足够强”。
验收：
- 论文里能清楚说出：`RS` 是根基，residual / 上层模块是在其上进一步增益，而不是概念混淆。

#### P0-E：补齐统计显著性与稳健性
目标：把当前“均值看起来不错”的 evidence 升级为统计可信的 evidence。
必须完成：
1. 对 RS 根基主结论做 bootstrap / CI / 多 seed 或多地图组统计；
2. 明确报告 effect size，而不是只报告平均值；
3. 至少检查：
   - 场景子类稳定性；
   - 个别极端 case 是否主导均值；
   - 随预算变化是否保持同向。
验收：
- “RS 根基优势”不再只是几行 summary 表，而是具有统计可信度。

### P0.3 强烈建议补齐的条件（能补则补）

#### P0-F：补辅助质量口径
1. 路径长度 / path cost；
2. clearance / collision margin；
3. 曲率或非完整约束下的可执行性一致性；
4. 说明 RS 根基优势不是靠灾难性路径退化换来的。

#### P0-G：补普通环境下的“代价可接受性”
1. 不仅看 expansions，也看总时间；
2. 说明在普通环境中虽然不一定绝对更快，但额外代价是否在可接受范围；
3. 若普通环境时间明显更差，则必须明确给出“为何高难收益仍值得”的使用边界。

#### P0-H：补跨分布 / 跨任务族稳定性
1. 不同场景族；
2. 不同 vehicle / planner 参数；
3. 不同 yaw_bins / resolution；
4. 至少一个额外的 hard benchmark 或更高保真设置。

### P0.4 当前主结论下不能继续偷换的叙事
1. 不能把“`No-RS` 会崩”直接等同于“`RS` 已经是 SOTA”；
2. 不能把非公平预算下快于 `BIT* / RRT*` 的结果继续当作最核心主 claim；
3. 不能在样本量很小的 `narrow_passage` 子集上直接宣称稳定 SOTA；
4. 不能把完整系统的收益直接写成 `RS` 本体收益。

### P0.5 与后续步骤的关系（硬约束）
1. 在 `P0-A ~ P0-E` 没补齐前，后续所有上层创新只可视为**探索性增强**，不能替代 `RS` 根基本体的补强；
2. Step 14 若继续推进，也必须把 `RS 根基` 的补强结果作为前提来解释其上层创新意义；
3. Step 15~19 的论文叙事必须显式区分：
   - `RS 根基本体是否已足够强`；
   - `上层方法是否在其上进一步建立方法创新`。

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
状态：`IN_PROGRESS（2026-03-07：A/B/C/D、E/F/G/H、phase32 TARP-line 与 phase33 RCWS-B 最终冲刺均已按 strict calib-only 尝试；仍无候选通过 Step 14 验收，因此未进入 test）`
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

### 2026-03-06 追加：Step 14 下一批全新候选（fresh queue）

本轮重新设计的原则：
1. **不再**继续在 `14-A/B/C/D` 上做局部补丁；
2. 候选必须把学习对象提升为 **ordered-regret / response-regime / spatial field / event-controller** 之一，而不是继续做“绝对 `J` surrogate + best-arm 分类”；
3. 必须保持 **zero-probe / single-search / strict calib-only** 语义；
4. 若只是继续在 `O / TreeWeightPortfolio` 的浅树上叠特征、调阈值或做更细切分，直接视为**创新度不足**。

这一轮 fresh queue 额外参考的文献抓手：
1. `Algorithms with Prediction Portfolios`：提示“多预测器/多策略”的关键不是再做一次 argmax，而是要把**选择不确定性**本身显式建模；
2. `Online Algorithms with Uncertainty-Quantified Predictions`：提示应把 **UQ / confidence** 直接嵌入决策规则，而不是仅作为离线诊断；
3. `Learning Heuristic Selection with Dynamic Algorithm Configuration`：提示真正的剩余增益可能在**搜索内部状态**，而非静态实例标签；
4. `Policy-Guided Heuristic Search with Guarantees` 与 `Single-Agent Policy Tree Search With Guarantees`：提示新模块若进入 planner 内部，必须能给出清晰的 search-effort / bounded-suboptimality 抓手；
5. `Conformal Risk Control / Learn then Test`：提示所有“可行集 / 触发阈值 / 风险边界”都必须留在 `calib_train/calib_val` 内完成。

候选执行顺序冻结为：`14-E -> 14-F -> 14-G -> 14-H`。

#### 14-E：CARL-WA — Calibrated Adjacent-Regret Ladder for Weighted A*
类型：`仅 router/planner 改造`
目标：把“直接选哪个权重臂”改写成“是否继续向更激进的一档权重上爬”的**有序 regret 链决策**。
核心设计：
1. 对有序权重 `w_1 < ... < w_K` 学习相邻差分
   `r_k(x)=J(w_{k+1}|x)-J(w_k|x)`，以及相邻风险增量与 path-audit 增量；
2. 共享参数地学习整条 regret ladder，并加 `isotonic / monotone` 结构约束，避免相邻边界互相打架；
3. 用 split-conformal / LTT 对每个相邻差分给 upper bound，再从保守端逐级上爬，直到“继续更激进”不再被上界支持；
4. 输出不是一次性的 multiclass label，而是一个**由局部可证成改进组成的累计决策链**。
为什么它比 `14-A/B/C` 更新：
- `14-A/B` 学的是绝对 surface / envelope，容易被全局偏差拖垮；
- `14-C` 学的是可行集 deferral，但没有把 ordered ladder 的**局部边际结构**学出来；
- `CARL-WA` 直接把问题改写成“相邻档位的累计 regret 证据是否足够”，样本效率和可解释性都更适合当前近邻权重臂。
最低验收：
1. 相邻 regret 上界不能塌缩成“始终停在同一档”；
2. `calib_val` 上必须 head-to-head 打赢 `M` 与 `N`，且不弱于 `O`；
3. 被选权重分布需展示真实 ladder traversal，而不是只落在一两个固定档位。

#### 14-F：TARP-WA — Topology-Aware Regime Portfolio for Weighted A*
类型：`仅 router/planner 改造`
目标：不再在**特征轴空间**切树，而是在“整条权重响应曲线”的**regime 空间**里学习少量 archetype。
核心设计：
1. 对每个样本构造完整 response curve：
   `w -> (T_norm(w), ΔL_rel(w), path_audit(w))`；
2. 在 `calib_train` 上对这些 curve 做原型学习 / archetype discovery，形成少量 search-regime（如 open-field、corridor、deceptive、late-bottleneck 等）；
3. 对每个 regime 单独学习一个小型 controller（常数权重、ladder controller 或小状态机）；
4. 再用 set-valued / conformal 的 regime predictor 把样本映射到一个**带不确定性的 regime 集**，并在其中做保守选择。
为什么它可能优于 `O`：
- `O` 的浅树是在 feature space 里做 axis-aligned partition；
- 当前剩余异质性更可能体现在“不同样本的整条 response curve 形状不同”，而不是单个特征阈值不同；
- 若 regime 学得稳定，这会是一个**方法对象**，而不是“更复杂的树”。
最低验收：
1. regime 原型必须在 `calib_val` 上稳定复现，而不是 seed-specific 偶然聚类；
2. 相对 `O` 的优势不能仅来自某一个 regime 的极少数样本；
3. regime 解释需要能和 map/search 几何现象对应起来。

#### 14-G：CPSF-WA — Certified Potential-Shaping Field for Weighted A*
类型：`需要新增模型模块`
目标：把当前“实例级单一权重”升级为“单次搜索内部的**空间变权 / potential shaping**”，但仍保持 zero-probe。
核心设计：
1. 为每个样本构造一个有界 shaping field `φ_x(s)`，搜索分数写成
   `f_x(s)=g(s)+h(s)+λ_x φ_x(s)`，或等价地写成 `g(s)+w_x(s) h(s)`；
2. `φ_x(s)` 来自局部地图几何、fastgeom 局部统计，以及在可用场景下的 `RS/residual disagreement` 或 heuristic uncertainty；
3. 强制 `0 <= φ_x(s) <= (w_max-1) h(s)`，使其保持在一个可解释的 bounded-suboptimality 包络内；
4. 在 `calib_val` 上只校准少量幅度/阈值超参数，不允许用 `test` 反复试 field 结构。
为什么它是更像 NeurIPS/ICML 的新方法：
- 学习对象从“选臂器”升级为**搜索内部的可证成 shaping field**；
- 与项目更早的 heuristic-field / residual-field 主线天然对齐，可向车体 / 机械臂等更广设置迁移；
- 即使最终未必最强，它也比“多切一层树”更有独立方法贡献。
最低验收：
1. field 必须展示真实空间变化，而不是退化成常数 `λ` 或常数权重；
2. 在 strict 下至少显著优于 `M` 与 `N`，且 path audit 不恶化；
3. 需要补一条清晰理论抓手：`max_s w_x(s)` 控制 bounded-suboptimality，上层 calibration 控制风险。

#### 14-H：CETA-WA — Certified Event-Triggered Automaton for Weighted A*
类型：`仅 router/planner 改造`
目标：替代 `14-D` 的 milestone schedule，做一个真正依赖**搜索事件**而非固定里程碑的 hybrid search controller。
核心设计：
1. 定义有限状态 automaton：`{aggressive, balanced, cautious, recovery}`；
2. 触发器只来自当前搜索前缀的在线统计：open-list entropy 下跌、duplicate ratio 激增、h-drop stagnation、corridor pinch、局部 field disagreement 等；
3. 所有状态切换都必须 prefix-reuse、honest-accounting，并对总切换次数设置上界；
4. 触发阈值先在 `calib_train` 拟合，再在 `calib_val` 做一次性选择，严禁 test 试阈值。
为什么它比 `14-D` 更有希望：
- `14-D` 失败的关键是 fixed milestone 与真实困难事件不对齐，导致 switch rate 过低且近乎平凡；
- `CETA-WA` 直接把“何时改变 compute regime”建成可学习的事件系统，而不是时间表；
- 这更接近一个独立的 search-control 方法。
最低验收：
1. `avg_switch_rate` 不能再落到近乎 0 的平凡区间；
2. 必须证明它不是 disguised probe，也不是换皮的 ARA* schedule；
3. 相对 `O` 的优势若存在，必须能明确归因到 event-triggered 控制而不是偶然参数。

这一批 fresh queue 的执行策略：
1. **先做 `14-E`**：最贴近现有 counterfactual infrastructure，最快判断“ordered-regret 结构”是否足够；
2. **再做 `14-F`**：若 `14-E` 仍显示实例级边界过弱，就测试 response-regime 是否比 feature tree 更有信息；
3. **再做 `14-G`**：若 router-only 仍无法明显越过 `O`，就进入真正的 field-level 新方法；
4. **最后做 `14-H`**：若剩余增益主要来自 search-time dynamics，则用 event-triggered controller 收尾；
5. 任一候选若在 `calib_val` 上已经明显不可能打赢 `M/N/O`，立即停止，不得为了“多试一次”消耗 `test`。

### 2026-03-06 fresh queue 实现结果（14-E/F/G/H）
主报告：`reports/router_phase31_step14_fresh_trials_v1.md`  
总汇总：`outputs/router_phase31_step14_fresh_trials_v1/summary.json`

1. **14-E / CARL-WA**（`outputs/router_phase31_step14_e_carl_wa_v1/`）  
   - 实现了 ordered adjacent-regret ladder，但在 strict `calib_val` 上全部退化为 `fast` fallback；  
   - 相对 `M/N/O` 的 pooled head-to-head `ΔJ` 约为 `-0.9156 / -0.9160 / -0.9125`，且 risk gate 明显失败；  
   - 结论：**当前相邻 regret 学习在本数据上没有形成可用的上爬链，直接塌缩成保守 fast-only 策略**。
2. **14-F / TARP-WA**（`outputs/router_phase31_step14_f_tarp_wa_v1/`）  
   - 是本轮 fresh queue 中最接近可行的方案；在多个 seed 上形成了 `wa_w125 / wa_w135` 的 regime-based 混合；  
   - 但 pooled head-to-head 仍对 `M/N` 略负（约 `-0.00169 / -0.00207`），只对 `O` 为弱正；同时至少一个 seed 退化为单臂，未通过 non-constantized gate；  
   - 结论：**response-regime 视角有一定信息量，但尚不足以严格打赢当前 strongest baselines**。
3. **14-G / CPSF-WA**（`outputs/router_phase31_step14_g_cpsf_wa_v1/`）  
   - 已实现 zero-probe 的 spatial potential-shaping field，并生成独立 `cpsf_calib.parquet`；  
   - field 本身并非平凡（`avg_field_std≈0.0304`），但最优配置仍出现高 violation rate（约 `0.24~0.27`），对 `M/N/O` 的 pooled head-to-head 大幅为负（约 `-2.04`）；  
   - 结论：**当前 field 设计虽然有真实空间变化，但主导作用是过度激进而非更优 compute shaping**。
4. **14-H / CETA-WA**（`outputs/router_phase31_step14_h_ceta_wa_v1/`）  
   - 已实现 event-triggered automaton，并生成独立 `ceta_calib.parquet`；  
   - 平均 switch rate 提升到 `0.1256`，明显高于 `14-D` 的平凡 schedule，但 `avg_state_diversity≈0.486` 仍不足，且 risk gate 失败，对 `M/N/O` head-to-head 仍显著为负；  
   - 结论：**event-triggered 控制比 milestone schedule 更“像一个方法”，但当前触发规则仍未把收益转成 strict `J` 优势**。
5. **fresh queue 总判定**  
   - `14-E/F/G/H` 已全部在 strict `calib_train/calib_val` 口径下完成实现与筛查；  
   - 本轮没有任何候选同时满足“打赢 `M/N/O` + risk/path gate 通过 + family-specific 非退化结构”，因此 **没有候选被允许进入 test**；  
   - 当前 paper-facing mainline 继续保持 `O / TreeWeightPortfolio`，Step 14 **仍未完成**；  
   - 下一轮若继续推进 Step 14，应重点沿 `14-F` 的 response-regime 方向或重新设计更强的 field / controller 理论接口，而不是继续小修当前 `E/G/H` 形态。

### 2026-03-06 response-regime 主线继续推进结果（phase32）
主报告：`reports/router_phase32_step14_tarp_line_v1.md`  
总汇总：`outputs/router_phase32_step14_tarp_line_v1/summary.json`  
定向 follow-up：`reports/router_phase32_step14_tarp_line_f2b_hgb_v1.md`

本轮只沿 `14-F / TARP-WA` 主线继续推进，不再修补 `E/G/H`，并额外引入了两类服务于该主线的结构：
1. **APS-style set-valued regime coverage**：对 `x -> regime set` 做响应曲线原型的有限样本集合预测；
2. **residual-to-incumbent regime decision**：把 decision object 从“绝对 response curve”改写为“相对当前最优常数权重 incumbent 的 residual response curve”，直接瞄准打赢 `M/N` 的微小剩余增益。

本轮实现的 TARP-line 变体：
1. **F2A / TARP-RRSV**（`outputs/router_phase32_step14_f2a_tarp_rrsv_v1/`）  
   - 使用 set-valued regime coverage + worst-case regime upper score 做鲁棒选臂；  
   - strict `calib_val` 下对 `O` 仅弱正（约 `+0.00091`），对 `M/N` 仍为负（约 `-0.00216 / -0.00253`）；  
   - 虽然 risk/path gate 通过，但整体退化为 `wa_w125 / wa_w135` 的近常数混合，非退化性不足；  
   - 结论：**集合预测本身有理论抓手，但当前最坏情形决策过于保守，没有形成有效的剩余增益**。
2. **F2B / TARP-RRMIX（tree classifier）**（`outputs/router_phase32_step14_f2b_tarp_rrmix_v1/`）  
   - 使用 posterior-weighted regime mixture + uncertainty penalty 做 residual-response 选择；  
   - 是 phase32 中最强的 TARP-line 变体，对 `O` 为正（约 `+0.00134`），但对 `M/N` 仍略负（约 `-0.00173 / -0.00210`）；  
   - 相比 phase31 的原始 `14-F`，并未形成足够清晰的进一步提升；  
   - 结论：**这是当前 response-regime 主线里最有信息量的实现，但还不足以恢复 Step 14 主结论**。
3. **F2C / TARP-RRGATE**（`outputs/router_phase32_step14_f2c_tarp_rrgate_v1/`）  
   - 使用“challenger 相对 incumbent 的 robust improvement gate”做局部切换；  
   - 结果几乎与 `F2A` 重合，说明当前 residual regime 上有意义的 challenger gate 很快塌回保守策略；  
   - 结论：**局部 margin gate 没有挖出新的 regime signal**。
4. **F2B / TARP-RRMIX（HGB 定向 follow-up）**（`outputs/router_phase32_step14_f2b_tarp_rrmix_hgb_v1/`）  
   - 为了排除“只是 classifier 容量不够”的可能，又在 `F2B` 上做了单独的更强 classifier 定向复跑；  
   - 该变体把 head-to-head 缩窄到接近 `14-A / RCWS-Q` 的水平：对 `M/N/O` 约为 `-0.000205 / -0.000570 / +0.002865`；  
   - 但依然没有转正到能严格打赢 `M/N`，同时仍只有 `wa_w125 / wa_w135` 两臂在起作用，非退化性也不足；  
   - 结论：**response-regime 主线在更强 classifier 下仍然只逼近、没有跨过当前 strongest baselines，说明瓶颈不只是分类器容量**。
5. **phase32 总判定**  
   - `response-regime` 这条主线已经完成了 `TARP-WA -> residual-to-incumbent -> set-valued robust selection -> mixture-of-regimes -> stronger-classifier follow-up` 的完整一轮探索；  
   - 所有实现都严格限制在 `calib_train` 内部再切分做拟合/校准，并仅用 `calib_val` 做模型选择，因此 **test 仍未被消耗**；  
   - 当前最优的 response-regime 版本是 `F2B / TARP-RRMIX (HGB)`，但它仍未满足“打赢 `M/N/O` + 非退化”这一 Step 14 门槛；  
   - 因而：**沿 14-F 主线的这一轮探索可以视为已经完成，结论是“创新性有所增强、理论接口更清晰，但方法有效性仍不足以把 Step 14 推过线”**。

### 2026-03-07 最终 Step 14 冲刺计划（phase33：RCWS-B 主线）

在坚持 `NeurIPS/ICML` 为主目标的前提下，当前 Step 14 不再继续扩展 `14-F / TARP-WA` 的 response-regime 细修，而改为启动一次**单家族聚焦的最终冲刺**：
- **RCWS-B — Residual-Calibrated Weight Surface with Basis Response Model**。

为什么在此时做该 pivot：
1. `14-F / TARP-WA` 及其 `phase32` 继续推进表明：response-regime 结构有信息，但其瓶颈不只是 classifier 容量；
2. `14-A / RCWS-Q` 仍是历史上最接近打赢 `M/N` 的方向；
3. 因而新的主线应当融合二者优点：
   - 保留 `14-F` 带来的 **residual-to-incumbent** 视角；
   - 回到 `14-A` 更接近主方法对象的 **continuous / ordered response surface**；
   - 用 split-conformal / CRC 风格校准形成可证成 feasible set。

phase33 的方法对象：
1. 以当前 seed 内 `calib_train` 上的最优常数权重 `incumbent` 作为 reference；
2. 对 ordered weight ladder 学习样本级 residual response functional：
   - `ΔJ(w|x) = J(w|x) - J(w_inc|x)`；
   - `Δd(w|x)` 与 `Δp(w|x)` 对应 risk / path residual；
3. 用低秩 / basis decomposition 表示整条 response curve，再由特征预测 basis 系数；
4. 在 `calib_train` 内部再切分出 `fit / regcal`：
   - `fit` 只负责 basis 学习与系数回归；
   - `regcal` 只负责对 `ΔJ / d / p` 的 upper envelope 做 conformal 校准；
5. 在 `calib_val` 上进行唯一允许的模型选择：
   - basis rank；
   - regressors / capacity；
   - monotone smoothing 或 ordered regularization；
   - feasible-set decision rule；
6. `test` 只有在 `calib_val` 同时打赢 `M/N/O` 且通过 risk/path/non-degenerate gate 时才允许被消费。

phase33 必须至少尝试的内部变体：
1. **B1 / RCWS-B-Direct**：直接预测 absolute response curve，再相对 incumbent 做决策；
2. **B2 / RCWS-B-Residual**：直接预测 residual response curve；
3. **B3 / RCWS-B-Monotone**：在 B2 基础上加入 ordered / monotone smoothing，避免局部锯齿导致过拟合；
4. 若上述版本接近过线，再允许做 **单次**更强容量 follow-up，但必须保持同一 strict protocol。

理论接口要求（与 Step 15 直接衔接）：
1. **finite-sample feasibility guarantee**：由 split-conformal upper envelope 提供；
2. **oracle-regret decomposition**：
   - basis approximation error；
   - coefficient estimation error；
   - calibration slack；
3. **ordered ladder approximation note**：解释离散权重梯度如何逼近连续 surface。

phase33 的停机规则：
1. 若 `calib_val` 上仍无法同时打赢 `M/N`，则不得消费 `test`；
2. 若最佳版本只比 `14-A / RCWS-Q` 持平或更差，则应诚实记为“最终 Step 14 冲刺失败”；
3. 只有在出现严格正向证据时，才允许把当前主线从 `O / TreeWeightPortfolio` 升级为新的 Step 14 方法。

### 2026-03-07 最终 Step 14 冲刺结果（phase33：RCWS-B 主线）
主报告：`reports/router_phase33_step14_rcwsb_trials_v1.md`  
总汇总：`outputs/router_phase33_step14_rcwsb_trials_v1/summary.json`  
定向 follow-up：`reports/router_phase33_step14_rcwsb_b1_followup_v1.md`

本轮按前述计划，将 Step 14 的最终冲刺聚焦到 **RCWS-B / Residual-Calibrated Weight Surface with Basis Response Model**，并严格遵守以下规则：
1. 所有 basis 学习、系数回归、upper-envelope 校准都只在 `calib_train` 内部再切分完成；
2. `calib_val` 只用于唯一允许的模型选择；
3. 只有若候选在 `calib_val` 上同时打赢 `M/N/O` 且通过 risk/path/non-degenerate gate，才允许进入 `test`；
4. 本轮没有任何候选达到该条件，因此 **test 仍未被消耗**。

本轮实现的 RCWS-B 变体：
1. **B1 / RCWS-B-Direct**（`outputs/router_phase33_step14_b1_rcwsb_direct_v1/`）  
   - 学习 absolute response curve，再相对 incumbent 做受约束决策；  
   - 在基础版搜索下是 phase33 中最强的主变体，对 `O` 为正（约 `+0.00128`），但对 `M/N` 仍为负（约 `-0.00181 / -0.00215`）；  
   - 虽然 5 个 seed 都形成了真实的 `wa_w125 / wa_w135` 混合，但整体仍未打赢当前 strongest weighted baselines。  
2. **B2 / RCWS-B-Residual**（`outputs/router_phase33_step14_b2_rcwsb_residual_v1/`）  
   - 直接学习 residual response curve；  
   - 结构上出现了 `wa_w120 / wa_w125 / wa_w135` 三臂使用，non-degenerate gate 通过；  
   - 但 pooled head-to-head 对 `M/N/O` 反而更弱（约 `-0.00326 / -0.00361 / -0.00017`）；  
   - 结论：**residual 建模本身提升了结构表达，但没有转化成更好的 strict `J`**。  
3. **B3 / RCWS-B-Monotone**（`outputs/router_phase33_step14_b3_rcwsb_monotone_v1/`）  
   - 在 `B2` 上对 feasible boundary 做 ordered / monotone smoothing；  
   - 结果与 `B2` 基本重合，没有形成实质收益；  
   - 结论：**当前 monotone smoothing 只稳定了边界，没有带来有效增益**。  
4. **B1 / RCWS-B-Direct（高容量定向 follow-up）**（`outputs/router_phase33_step14_b1_rcwsb_direct_fup_v1/`）  
   - 又对最强的 `B1` 做了更大容量搜索（更高 depth / iteration、更宽超参数范围）；  
   - 该 follow-up 把结构非退化性提升到通过门槛：使用了 `wa_w120 / wa_w125 / wa_w135` 三臂，`nonconstant_seed_count = 5`；  
   - 但 pooled head-to-head 仍只达到 `M/N/O ≈ -0.00147 / -0.00182 / +0.00162`，依然没有跨过 `M/N`；  
   - 与 `14-A / RCWS-Q` 相比，这一最终冲刺也没有实现更强的数值结果。  
5. **phase33 总判定**  
   - RCWS-B 这条最终冲刺主线已经完成了 `absolute curve -> residual curve -> monotone feasible boundary -> higher-capacity follow-up` 的完整一轮尝试；  
   - 当前最强版本是 `B1 / RCWS-B-Direct (follow-up)`，但它仍未满足“显著打赢 `M/N`”这一 Step 14 的硬门槛；  
   - 因而：**本轮 phase33 已可视为 Step 14 的最终一次主线冲刺，结论是“方法对象与理论接口进一步增强，但效果仍不足以支撑 NeurIPS/ICML 所需的新方法主体”**。

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
- 不要再把“继续细修纯 `RS-only` 根基线”当作当前主攻方向；
- 不要把时间主要花在文档润色或继续堆远邻 baseline；
- 资源应优先投入：`P0-CX -> P0-D -> P0-E -> P0-F/G/H -> Step 14/15/16/17/18`；
- 若 `P0-CX` 仍无法建立显著优势区间，则应尽早触发更大的 go/no-go 分流，而不是继续无边界消耗在单一最近邻强基线轴上。

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
