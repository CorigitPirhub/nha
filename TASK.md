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
状态：`IN_PROGRESS（2026-03-14：CX1-CX26 多轮已推进；accepted 主线仍是 refined CX3-D；CX8-D Heavy ceiling 仍为正但成本过高；CX10/CX11/CX12/CX13/CX15/CX16/CX18/CX19 已冻结失败；CX14 runtime sprint 退化为 public tie；CX17 在 public 上出现小幅正向 ceiling 但 hard-test 未维持转正；CX20 在 public 上重新出现更强正向 ceiling，但 hard-test 明确失败；CX21 首轮 public/mp/csm 实现完成，CX21-B 取得更强 public ceiling 但跨 family 负项与超高 overhead 仍阻止晋升；CX22 首轮 public/mp/csm 实现完成，CX22-D 保留了大部分 flange 增益且低于 `CX21-B` overhead，但仍未形成稳定 overall gain；CX23 首轮 public/mp/csm 实现完成，其中 `CX23-C` 进一步保住 flange 并修复了 narrow_passage，但 maze / parasol_misc 负项仍阻止晋升；CX24 首轮 public/mp/csm 实现完成，其中 `CX24-D` 修复了 maze 但严重削弱 flange，`CX24-E` 补齐了诊断平面，而 `CX24-B/C` 仍未改变 family pattern；CX25 首轮 public/mp/csm 实现完成，但 selective/soft/calibrated/group-stable certificates 仍未把 `flange` 主收益救回来，最有价值产物是 `CX25-B` 的 diagnostic compiler；CX26 design scout 已冻结围绕 `CX24-E + CX24-D` 的 3 条结构修复方案）`
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

本轮实现结果（`2026-03-08`，对应产物：`reports/rs_p0cx_round1_summary.md`、`outputs/rs_p0cx_round1_summary/summary.csv`）：
1. **`CX-A / RS-Tube`**：
   - 主实验矩阵已完成：`parasol_narrow` + `mp/csm` + public-parasol ablation；
   - public `exp3/exp4` 上的 success 分别为 `0.777778 / 0.833333`，未恢复到 frozen `Full / Hybrid` 的 `1.0` 级别；
   - 相对 same-`alpha` plain residual 仅带来 `+12.722 / +15.056` 的平均 expansions 改善（`exp3 / exp4`），success 增益为 `0`；
   - 结论：**有极弱的 effort 改善，但远未形成可投稿主 claim 所需的硬优势轴**。
2. **`CX-B / RS-BPF`**：
   - 主实验矩阵已完成；
   - public `exp3/exp4` 的 success 仍为 `0.777778 / 0.833333`；
   - 相对 same-`alpha` plain residual，平均 expansions 反而恶化 `-6.778 / -8.056`；
   - 结论：**当前 bottleneck-progress gating 未兑现预期，冻结为负结果证据**。
3. **`CX-C / RS-DVP`**：
   - 主实验矩阵已完成；
   - public `exp3/exp4` 的 success 仍为 `0.777778 / 0.833333`；
   - 相对 same-`alpha` plain residual，平均 expansions 仅改善 `+10.500 / +13.000`，success 增益为 `0`；
   - 结论：**dual-value 结构在当前实现下只产生很小的 search-effort 调整，未形成独立创新点应有的强收益**。
4. **`CX-D / RS-PMF`**：
   - 主实验矩阵已完成；
   - 实现过程中发现并修复了一个真实 bug：prototype kernel 从 nonholonomic `96x96` 迁移到 `mp/csm` 的 `32x32` 时发生 shape mismatch；现已显式做跨分辨率对齐；
   - 修复后 public `exp3/exp4` success 仍为 `0.777778 / 0.833333`，相对 same-`alpha` plain residual 的平均 expansions 仍恶化 `-5.667 / -9.500`；
   - 结论：**prototype memory 当前更多是带来普通场景上的轻微 expansions 改善，而没有在高难狭窄主战场建立硬优势轴**。
5. **汇总结论 / go-no-go**：
   - 四条路线都没有把 public `parasol_narrow` 的 success 从 `0.833333` 恢复到 `1.0`，也没有在 same-`alpha` ablation 下给出显著的模块级净增益；
   - `mp/csm` 支持口径整体成立：四个候选都没有把普通场景 expansions 明显做坏，且时间代价显著低于 frozen `Full`；
   - 但这只能说明它们是“温和的 field-shaping 变体”，**还不能说明其本身已经建立可单独论道的强创新增益**；
   - 因此：`CX-A/B/C/D` 本轮全部**不通过 `P0-CX` 验收**，后续应冻结为负结果证据，并转向新的基础模型候选；
   - 由于 public 主实验已明确未过线，本轮**没有继续把全部四条路线全量推进到 `rs_root_hard_v2/test` expanded benchmark**；若后续需要，只应对下一轮更有希望的新候选或本轮最接近者做补充验证。
6. **本轮产物**：
   - 主实验：`reports/rs_p0cx_cx_a_main_v1.md`、`reports/rs_p0cx_cx_b_main_v1.md`、`reports/rs_p0cx_cx_c_main_v1.md`、`reports/rs_p0cx_cx_d_main_v1.md`；
   - 消融：`reports/rs_p0cx_cx_a_ablation_v1.md`、`reports/rs_p0cx_cx_b_ablation_v1.md`、`reports/rs_p0cx_cx_c_ablation_v1.md`、`reports/rs_p0cx_cx_d_ablation_v1.md`；
   - 汇总：`reports/rs_p0cx_round1_summary.md`、`outputs/rs_p0cx_round1_summary/summary.csv`、`outputs/rs_p0cx_round1_summary/summary.json`。



#### P0-CX2：第二轮基础模型候选设计（当前下一轮执行入口）
状态：`IN_PROGRESS（2026-03-08：CX2-A/B/C/D 首轮实现与主实验矩阵已完成；四条路线均未通过 P0-CX-2 验收）`
是否需要模型/方法修改：`是（且必须是可单独论道的基础模型模块）`

触发原因：
1. `CX-A/B/C/D` 的首轮证据已表明：**单纯 residual 幅值重标、局部 gating 或 prototype mixing 不足以恢复 public `parasol_narrow` 上的 success 主结论**；
2. same-`alpha` ablation 也说明当前问题不是“把 residual 再调强一点”即可解决，而是需要**更结构性的几何 / 拓扑 / 非局部场设计**；
3. 因此下一轮不再补 `CX-A/B/C/D`，而是转入 `P0-CX-2` 的新候选。

调研产物：
1. 详细调研与候选论证见：`reports/rs_p0cx2_design_scout_v1.md`；
2. 该 note 已汇总本轮重点参考的顶会/顶刊论文脉络，包括：
   - differentiable / search-aware heuristic learning；
   - PDE / operator / neural-field motion planning；
   - topology / passage / separator / subgoal 结构；
3. `P0-CX-2` 的全部候选都必须保持在 `RS field -> heuristic field -> planner guidance` 这一主链上，不允许偷换为 router / planner-selection 主线。

第二轮设计原则（从 `CX-A/B/C/D` 负结果中提炼）：
1. 不再做纯局部 residual gain scheduling；
2. 必须直接作用于**几何介质、全局 corridor 结构、separator 结构或路径积分结构**；
3. 模块本身必须可作为单独创新点存在，而不是经验技巧堆叠；
4. 所有候选都必须继续接受 same-`alpha` ablation 审查，证明增益来自新模块而不是单纯 `alpha` 变化；
5. 所有候选的选择 / 搜索 / early-stop 仍只能在 dev/train 上进行，test 不得调参。

冻结候选路线（下一轮按 `CX2-A -> CX2-B -> CX2-C -> CX2-D` 顺序执行）：

##### CX2-A：RS-MDE — RS Morphological Deformation Envelope
类型：`需要新增基础模型模块`
核心想法：
1. 预测一个 start-goal 条件的局部形态变形场 `ρ(x, y)`，决定局部障碍应被轻微 erosion 还是 dilation；
2. 在变形后的 optimistic / conservative 两个介质上分别计算 `RS` 场，得到 `V^-_RS` 与 `V^+_RS`；
3. 用 envelope 宽度 `ΔV = V^+_RS - V^-_RS` 控制当前 residual 的 trust，而不是直接缩放 residual 幅值；
4. 目标是在不改 planner 的前提下，把“正确 corridor 是否稳定存在”编码进启发场本体。
与现有工作的差异：
1. 不同于已有工作里的全局 obstacle erosion，这里是**局部、条件化、RS-native** 的 geometry deformation；
2. 不同于 `CX-A` 的 tube residual，这里直接改的是**规划介质本身**。
理论抓手：
1. 障碍 dilation / erosion 对最短路 cost 的单调性给出 `V^-_RS <= V* <= V^+_RS` 的 envelope；
2. 当 `ΔV` 小时说明 corridor 结构稳定，可更信任学习修正；当 `ΔV` 大时应自动回退 toward plain `RS`。
预期优势轴：
1. hard-family 下的 success-under-budget；
2. 兼顾 expansions / time 的稳定下降。

##### CX2-B：RS-HBF — RS Harmonic Bridge Field
类型：`需要新增基础模型模块`
核心想法：
1. 从 occupancy、`RS` 等值线与 hard-family 几何 cues 中检测 passage anchors / gate anchors；
2. 构造少量 harmonic bridge basis fields `{φ_k}`，每个 basis 连接 start / goal / gate 等关键锚点；
3. 网络只学习 bridge 系数与 gate 权重，再把 `Σ a_k φ_k` 作为全局低秩 correction 注入启发场；
4. 目标是把“应该跨哪个 passage”这种长程结构，作为连续场而不是离散子目标来表达。
与现有工作的差异：
1. 不是 discrete subgoal planner；
2. 不是 `CX-B` 那种 pointwise progress gate；
3. 而是**连续、低秩、全局 bridge field**。
理论抓手：
1. harmonic field 满足 maximum principle 与最小 Dirichlet energy；
2. 因而相比任意自由 residual，更不容易制造错误内点极值；
3. 系数有界时，bridge correction 对 `RS` 的偏移也有界。
预期优势轴：
1. `narrow_passage / flange / maze` 上的 success 与 expansions；
2. family-wise 的清晰优势区间。

##### CX2-C：RS-BCE — RS Barrier-Certified Exclusion
类型：`需要新增基础模型模块`
核心想法：
1. 学一个非负 separator / exclusion field `b(x, y) >= 0`，标识相对当前 start-goal 对而言的死胡同盆地、坏 pocket 或 separator 后方区域；
2. 将其作为非负排斥项注入启发：`h = h_RS + r + λ b`；
3. 必要时再用 corridor-positive evidence 对 `b` 做可通 passage 豁免，避免错杀真正的窄通道；
4. 目标是把“哪里不该去”作为显式场对象，而不是指望正向 residual 自己学会回避坏区域。
与现有工作的差异：
1. 不同于 motion-planning infeasibility proof 的全局证明对象，这里是**可微、可插入当前 planner 的 soft exclusion field**；
2. 不同于 `CX-B/C` 的正向激励，这里是**负向证伪型 guidance**。
理论抓手：
1. 若进入某坏 pocket 的任意轨迹都必须跨越 separator `Γ`，且 `∫_Γ b ds >= δ`，则会累计至少 `λδ` 的启发惩罚；
2. 当 `λδ` 超过该 pocket 对搜索的虚假吸引 margin 时，固定 budget 下应更偏向正确 corridor。
预期优势轴：
1. dead-end / maze family 的 expansions 和 success-under-budget；
2. 对 public parasol 中失败样本的回正。

##### CX2-D：RS-PIF — RS Passage Integral Field
类型：`需要新增基础模型模块`
核心想法：
1. 学一个 corridor-capacity density `c(x, y) >= 0`，必要时再学 dead-end risk density `d(x, y) >= 0`；
2. 在 `RS` 长度之外再定义一个路径积分型次级目标：`J(π) = L_RS(π) + β∫ d ds - γ∫ c ds`；
3. 通过动态规划、sweep 或近似 operator 方式把这个次级目标转成可搜索的 value field；
4. 目标是在“路径长度差不多，但 corridor 可用自由空间差很多”的情况下，系统性偏向更稳的 passage。
与现有工作的差异：
1. 不是 local bottleneck multiplier；
2. 不是简单 clearance heuristic；
3. 而是**路径积分型的非局部 corridor support field**。
理论抓手：
1. 这相当于在 `RS` 长度之外引入 `length-capacity` 的 Pareto / lexicographic 目标；
2. 当两条 corridor 的 `L_RS` 接近而 integrated capacity 差异显著时，场值会稳定偏向更 robust 的 corridor。
预期优势轴：
1. high-constraint family 上的 success-under-budget；
2. `quality-efficiency Pareto`。

下一轮通用执行规范：
1. 所有 `CX2-*` 候选首先只做 `public parasol_narrow + mp/csm + same-alpha ablation`；
2. 只有 public 主轴显著转正后，才允许把该候选推进到 `rs_root_hard_v2/test` expanded hard benchmark；
3. 所有选择只用 dev/train；
4. 所有报告必须单独给出：
   - `Hybrid A* (RS)` / `RS-only`；
   - frozen `Full`；
   - `Plain-Residual (same α)`；
   - `CX2-*`；
5. 若某候选只比 same-`alpha` plain residual 带来很小 expansions 改善、但没有 success 主轴改善，则应尽早停机，不继续扩大实验面。

推荐执行顺序与原因：
1. **先做 `CX2-A / RS-MDE`**：最直接、最几何本体、最贴近当前 `RS` 根基主线；
2. **再做 `CX2-B / RS-HBF`**：若 geometry deformation 仍不够，则说明需要显式的全局 bridge mode；
3. **再做 `CX2-C / RS-BCE`**：若主要失败来自坏 pocket / dead-end attraction，则引入 barrier-type exclusion；
4. **最后做 `CX2-D / RS-PIF`**：它最丰富但也最耦合，放在 geometry/topology 路线之后。

本阶段结论：
1. `P0-CX` 下一轮的高概率成功方向，应当是**几何 / 拓扑 / 非局部场结构**，而不是继续做局部 residual 重标；
2. 当前首选：`CX2-A / RS-MDE`；
3. 当前最具“单独论道创新点”潜力的 follow-up：`CX2-B / RS-HBF`；
4. 当前针对 public 失败样本的安全网候选：`CX2-C / RS-BCE`。



本轮实现结果（`2026-03-08`，对应产物：`reports/rs_p0cx2_round1_summary.md`、`outputs/rs_p0cx2_round1_summary/summary.csv`）：
1. **`CX2-A / RS-MDE`**：
   - 主实验矩阵已完成：`parasol_narrow` + `mp/csm` + public-parasol ablation；
   - public `exp3/exp4` success 下降为 `0.722222 / 0.777778`；
   - 虽然在 `flange` 与 `narrow_passage` 上相对 same-`alpha` plain residual 有局部 expansions 改善，但在 `parasol_misc` 上出现显著退化；
   - 结论：**局部形态变形确实能改变 family-wise 行为，但当前稳定性不足，不能形成全局正结论**。
2. **`CX2-B / RS-HBF`**：
   - public `exp3/exp4` success 为 `0.722222 / 0.833333`；
   - 相对 same-`alpha` plain residual，平均 expansions 继续恶化 `-259.944 / -386.167`；
   - 结论：**harmonic bridge 目前没有把长程 passage preference 转化为净增益，冻结为负结果证据**。
3. **`CX2-C / RS-BCE`**：
   - public `exp3/exp4` success 为 `0.777778 / 0.833333`；
   - 相对 same-`alpha` `Plain-Residual`，平均 expansions 仍恶化 `-103.000 / -81.722`；
   - 虽然 `parasol_misc` 被保护住并有改善，但 `flange / narrow_passage` 的净效果仍不稳定；
   - 结论：**partitioned specialist 的 locality 思路成立，但当前具体实现整体仍为负结果**。
4. **`CX2-D / RS-PIF`**：
   - public `exp3/exp4` success 大幅下降为 `0.388889 / 0.555556`；
   - same-`alpha` plain residual 对照下在 success 与 expansions 两轴都显著恶化；
   - 结论：**当前 passage-integral formulation 明显失败，应冻结为强负结果证据**。
5. **汇总结论 / go-no-go**：
   - 四条 `CX2-*` 路线都没有恢复 public `parasol_narrow` 的 success 主轴，也都没有在 same-`alpha` ablation 下优于 `Plain-Residual` 的平均 expansions；
   - 这说明即便转向 geometry / topology / nonlocal field 设计，当前这四种具体实现仍不足以建立论文主 claim 所需的显著优势区间；
   - 由于 public 主 bundle 已明确为负，本轮**没有继续把任何 `CX2-*` 候选推进到 `rs_root_hard_v2/test` expanded hard benchmark**；
   - 当前最值得保留的弱信号只有：
     - `CX2-A` 在 `flange / narrow_passage` 的局部 expansions 改善；
     - `CX2-C` 的 success 保持性与 `flange` 局部改善；
   - 但这些都还不足以支持继续按当前实现扩大实验面。
6. **本轮产物**：
   - 主实验：`reports/rs_p0cx2_cx2_a_main_v1.md`、`reports/rs_p0cx2_cx2_b_main_v1.md`、`reports/rs_p0cx2_cx2_c_main_v1.md`、`reports/rs_p0cx2_cx2_d_main_v1.md`；
   - 消融：`reports/rs_p0cx2_cx2_a_ablation_v1.md`、`reports/rs_p0cx2_cx2_b_ablation_v1.md`、`reports/rs_p0cx2_cx2_c_ablation_v1.md`、`reports/rs_p0cx2_cx2_d_ablation_v1.md`；
   - 汇总：`reports/rs_p0cx2_round1_summary.md`、`outputs/rs_p0cx2_round1_summary/summary.csv`、`outputs/rs_p0cx2_round1_summary/summary.json`。



#### P0-CX3：第三轮基础模型候选设计（当前下一轮执行入口）
状态：`IN_PROGRESS（2026-03-08：CX3-A/B/C/D 首轮实现与主实验矩阵已完成；修正保护门控 bug 并重跑后，CX3-D 为当前最稳的保守正分支）`
是否需要模型/方法修改：`是（且必须显式解决 parasol_misc 退化问题）`

触发原因：
1. `CX2-A/B/C/D` 的首轮实现表明：单纯增加几何 / 拓扑 / 非局部结构，并不会自动转化为总体优势；
2. 当前真正的核心问题已从“hard family 完全没有信号”收缩为：**hard family 上有局部正信号，但会在 `parasol_misc` 上产生不可接受的退化**；
3. 因此下一轮的目标不是再做“更强的结构场”，而是做**带显式 abstention / locality / protected-subgroup control 的结构场**；
4. 换句话说：`parasol_misc` 现在必须被当作 `P0-CX3` 的 protected regime 来处理。

调研产物：
1. 详细调研与候选论证见：`reports/rs_p0cx3_design_scout_v1.md`；
2. 该 note 已汇总本轮重点参考的顶会/顶刊论文脉络，包括：
   - selective prediction / abstention / risk-controlled editing；
   - region partition / localized specialization；
   - topology / separator / homotopy guard；
3. `P0-CX3` 的全部候选仍必须保持在 `RS field -> heuristic field -> planner guidance` 主链上，不允许偷换为 router / planner-selection 主线。

第三轮设计原则（从 `CX2` 负结果中提炼）：
1. 默认应为 **abstain-by-default**：没有强证据时必须精确回退到 `RS` 或 same-`alpha` `Plain-Residual`；
2. 必须显式限制 perturbation 的 support / coverage，避免全局 spillover；
3. 必须把 `parasol_misc` 作为 protected subgroup 直接写入选择与停机规则；
4. 允许 hard family 局部加力，但前提是 misc 不明显退化；
5. 仍然要求 same-`alpha` ablation，以证明增益来自新模块而不是 `alpha` 变化。

冻结候选路线（下一轮按 `CX3-A -> CX3-B -> CX3-C -> CX3-D` 顺序执行）：

##### CX3-A：RS-SAFE — Selective Activation Field Editor
类型：`需要新增基础模型模块`
核心想法：
1. 联合学习一个结构 edit field `Δh` 与一个 abstention / coverage field `κ`；
2. 最终只输出 `κ ⊙ Δh`，未覆盖区域精确回退到 `RS` 或 same-`alpha` `Plain-Residual`；
3. 用风险控制或 coverage calibration 去限制 `parasol_misc` 上的预期退化；
4. 使“是否介入”本身成为模型要学的对象，而不只是 edit 强度。
+与现有工作的差异：
1. 不同于普通 selective prediction，这里 reject option 作用在**场编辑支持域**而不是分类输出；
2. 不同于 `CX-A/CX2-A` 的 trust shrink，这里是**显式、可校准的硬回退机制**。
理论抓手：
1. 若校准后满足 `E[L_misc | activated] <= ε`，则 misc 退化可被约束；
2. 若 activation mass `||κ||_1` 有界，则总 perturbation support 可被上界控制。
预期优势轴：
1. 先消除 `parasol_misc` 退化；
2. 再在 `flange / narrow_passage` 上保住局部 gain。

##### CX3-B：RS-PSF — Partitioned Specialist Field
类型：`需要新增基础模型模块`
核心想法：
1. 将自由空间划分为少数 latent partitions：`inert / corridor / separator / other-hard`；
2. 只有被选中的 hard partitions 允许 specialist field editor 介入，inert partition 一律不改；
3. 通过 sparse partition activation 限制结构场对 open / misc 区域的泄漏；
4. 输出仍是单一 fused heuristic field，不改变 planner。
与现有工作的差异：
1. 不同于 LaP3 的 search partition，这里 partition 的对象是**field-edit region**；
2. 不同于全局 field shaping，这里是**piecewise-specialized field editing**。
理论抓手：
1. 若非 inert 分区面积被界定，则 easy-scene perturbation 质量有上界；
2. misc-like 地图大部分落在 inert partition 时，可直接解释 no-regression。
预期优势轴：
1. misc 保持；
2. hard-family 的局部专门化 gain。

##### CX3-C：RS-CCP — Consensus-Certified Perturbation
类型：`需要新增基础模型模块`
核心想法：
1. 保留多个独立结构 witness（morph / barrier / bridge / passage-capacity 等）；
2. 每个 witness 产生一个 signed perturbation proposal；
3. 只有当足够多 witness 在局部 support 与符号上达成一致时，才允许 perturbation 通过；
4. 否则硬回退到 base。
与现有工作的差异：
1. 不是 expert routing；
2. 不是多个 planner 投票；
3. 而是**多个 field witness 对单一 perturbation 的一致性认证**。
理论抓手：
1. 若 disagreement score 超过阈值就强制置零，则 ambiguous 区域的错误介入被抑制；
2. perturbation support 只存在于 high-agreement 区域，因此更适合保护 misc 场景。
预期优势轴：
1. 保住 hard-family 的局部结构信号；
2. 同时大幅降低 misc 上的误改。

##### CX3-D：RS-HPG — Homotopy-Preserving Guard
类型：`需要新增基础模型模块`
核心想法：
1. 为 easy / misc 场景构造轻量拓扑 guard（separator loops / obstacle skeleton integrals / reference homotopy signatures）；
2. 任何结构场 edit 只有在不显著改变 easy-scene route topology 时才允许通过；
3. 对 hard scenes，则允许 guard 之外的 bottleneck 强化；
4. 本质上是给结构 perturbation 加一个 topological veto。
与现有工作的差异：
1. 不做 homotopy class enumeration，也不改变 planner；
2. 只把 topology 用作**heuristic edit 的保守过滤器**。
理论抓手：
1. 若 edit 在参考 loops 上保持 homotopy integral 变化不超过 `τ`，则 easy-scene 的 route ordering 近似保持不变；
2. 因而 guard 可以专门抑制 open / misc 场景中的伪结构偏置。
预期优势轴：
1. 杜绝 misc 无谓退化；
2. 为 hard scenes 留下受控的结构 edit 自由度。

下一轮通用执行规范：
1. 所有 `CX3-*` 候选首先只做 `public parasol_narrow + mp/csm + same-alpha ablation`；
2. 必须单独报告 `parasol_misc / narrow_passage / flange / maze` 的 family-wise 指标；
3. 若 `parasol_misc` success 下降或 expansions 明显劣于 same-`alpha` `Plain-Residual`，立即 early-stop；
4. 只有在 public bundle 过线后，才允许推进到 `rs_root_hard_v2/test` expanded hard benchmark；
5. 一切选择 / 校准 / stop rule 仍只能发生在 dev/train 上。

推荐执行顺序与原因：
1. **先做 `CX3-A / RS-SAFE`**：直接攻击 misc 退化这一核心问题；
2. **再做 `CX3-B / RS-PSF`**：若显式 abstention 不够，则进一步做 region-localized specialization；
3. **再做 `CX3-C / RS-CCP`**：若单一结构 witness 仍不稳，则引入 consensus certification；
4. **最后做 `CX3-D / RS-HPG`**：它最概念化、最理论驱动，也最适合做高风险的终极保守过滤。

本阶段结论：
1. `P0-CX3` 的核心不是“更强 edit”，而是“**更可控的 edit**”；
2. 当前首选：`CX3-A / RS-SAFE`；
3. 当前最有希望兼顾创新性与可落地性的 follow-up：`CX3-B / RS-PSF`；
4. 当前最具理论特色的候选：`CX3-D / RS-HPG`。



本轮实现结果（`2026-03-08`，对应产物：`reports/rs_p0cx3_round1_summary.md`、`outputs/rs_p0cx3_round1_summary/summary.csv`）：
1. **`CX3-A / RS-SAFE`**：
   - public `exp3/exp4` success 实际回落为 `0.722222 / 0.833333`；
   - same-`alpha` 下平均 expansions 仍落后 `Plain-Residual`（约 `-179.167 / -125.667`），且 `parasol_misc` 重新出现退化；
   - 结论：**在修正保护门控 bug 后，`CX3-A` 不再能被视为有效正分支**。
2. **`CX3-B / RS-PSF`**：
   - public success 维持 `0.777778 / 0.833333`；
   - same-`alpha` 下平均 expansions 仍落后 `Plain-Residual`（约 `-113.222 / -72.111`），`parasol_misc` 也重新出现退化；
   - 结论：**partitioned specialist 的 locality 思路还不够稳定，当前整体仍为负结果**。
3. **`CX3-C / RS-CCP`**：
   - public `exp3/exp4` success 为 `0.777778 / 0.833333`；
   - 但 same-`alpha` 下平均 expansions 仍落后 `Plain-Residual`（约 `-48.000 / -35.667`）；
   - `flange` 与 `narrow_passage` 仍有局部正增益，但 `parasol_misc` 又退化为 `-173.833`；
   - 结论：**沿 `CX3-C` 主线继续精修后，当前实现仍未形成可接受的受保护正分支，只能保留为局部 hard-family 有信号的未完成路线**。
4. **`CX3-D / RS-HPG`**：
   - public success 同样保持 `0.777778 / 0.833333`；
   - same-`alpha` 下平均 expansions 取得小幅但稳定的改善 `+24.500 / +24.500`；
   - `parasol_misc` 被保护住，普通场景代价也最低；
   - 结论：**在修正后的证据下，`CX3-D` 成为当前最稳的保守正分支**。
5. **汇总结论 / go-no-go**：
   - 在修正 `CX3` 保护门控 bug 并重跑后，只有 `CX3-D` 稳定解决了 `parasol_misc` 退化问题；
   - 当前最优候选改为 `CX3-D / RS-HPG`；早先 `CX3-C` 的强正结论不再成立；
   - 但它仍没有把 frozen public success 轴恢复到 `1.0`，因此 `P0-CX` 还**不能宣告完成**；
   - 下一阶段不应再平均分配资源给全部 `CX3-*`，而应聚焦：
     - 以 refined `CX3-D`（含 `low_bridge_scale` 收缩）为主线做进一步 refinement / stronger validation；
     - `CX3-C` 仅作为局部 hard-family signal 的辅助参考；
     - `CX3-A/B` 仅保留为参考证据；
   - 本轮曾尝试两类 follow-up：
     - 一是把 `CX3-C` 推到 expanded hard benchmark；
     - 二是给 `CX3-D` 注入 `CX3-C` 式 auxiliary hard signal；
     两者都没有成为 accepted evidence：前者因 `CX3-C` 本身在修正后已不再是正分支而放弃，后者则因显著抬高 `mp/csm` 时间代价且未改善 public 主结论而被拒绝（见 `reports/rs_p0cx3_cx3_d_aux_followup_v1.md`）。
   - 本轮还额外尝试了一个更窄的 `CX3-D` recovery boost，只想修补 `narrow_passage` 负项；但它在 dev 上没有带来任何 `exp_delta_mean` 提升，因此同样被拒绝（见 `reports/rs_p0cx3_cx3_d_recovery_followup_v1.md`）。
   - 当前 accepted `CX3-D` 版本是进一步加入 `low_bridge_scale` 的更窄保守 refinement：它把 same-`alpha` 净增益提升到 `+31.000 / +31.000`，同时将 `mp/csm` 时间压回到 `38.152 / 61.134` 这一仍偏高但更可接受的水平；
   - 统计加固见 `reports/rs_p0cx3_stats_v1.md`：整体 `+31` 的 paired-bootstrap CI 仍穿过 0（`[-8.11, 101.0]`），说明“总体提升”还不够硬；但 `parasol_misc` 子群的 paired-bootstrap 改善更稳（均值 `+104.0`，`p_boot_le0≈0.016`），这支持它作为**受保护的保守改进分支**。
6. **本轮产物**：
   - 主实验：`reports/rs_p0cx3_cx3_a_main_v1.md`、`reports/rs_p0cx3_cx3_b_main_v1.md`、`reports/rs_p0cx3_cx3_c_main_v1.md`、`reports/rs_p0cx3_cx3_d_main_v1.md`；
   - 消融：`reports/rs_p0cx3_cx3_a_ablation_v1.md`、`reports/rs_p0cx3_cx3_b_ablation_v1.md`、`reports/rs_p0cx3_cx3_c_ablation_v1.md`、`reports/rs_p0cx3_cx3_d_ablation_v1.md`；
   - 汇总：`reports/rs_p0cx3_round1_summary.md`、`outputs/rs_p0cx3_round1_summary/summary.csv`、`outputs/rs_p0cx3_round1_summary/summary.json`。



7. **当前 paper-facing 收口 / 主线定位**：
   - 当前 accepted `P0-CX` 主线是：`RS cost field + CX3-D / RS-HPG`；
   - 其精确定义的 paper-facing claim contract 见：`paper/rs_cx_current_claim_contract.md`；
   - 当前允许的 strongest honest claim 不是“显著总体胜出”，而是“**受保护的保守效率改进分支**”；
   - 当前 accepted 证据根包括：
     - `reports/rs_p0cx3_round1_summary.md`；
     - `reports/rs_p0cx3_stats_v1.md`；
     - `paper/rs_cx_current_claim_contract.md`；
   - 因而后续 `P0-CX` 新候选必须默认以 `CX3-D` 为当前 baseline，而不是回到 `Plain-Residual` 或已失败的 `CX3-C` 叙事。

#### P0-CX4：基于 `RS + CX3-D` 的下一轮候选设计（当前下一轮执行入口）
状态：`IN_PROGRESS（2026-03-08：CX4-A/D/C/B 首轮实现与主实验矩阵已完成；四条路线均未替代 accepted CX3-D 主线）`
是否需要模型/方法修改：`是（但必须建立在 accepted CX3-D 主线之上）`

触发原因：
1. `CX3-D` 已经把“保护 misc + 小幅净增益”做出来，但总体增益仍然太弱，且 `narrow_passage` 仍是短板；
2. 因此下一轮不应推翻当前 conservative branch，而应把它视作 trusted base，在其上叠加**受约束的 hard-opportunity amplification**；
3. 当前真正需要解决的问题是：如何在不打破 `CX3-D` 的 misc 保护前提下，进一步放大 hard-family 增益。

调研产物：
1. 详细调研与候选论证已直接固化在本节冻结说明中；首轮实现总结见：`reports/rs_p0cx4_round1_summary.md`；
2. 当前 accepted paper-facing claim contract 见：`paper/rs_cx_current_claim_contract.md`；
3. 所有 `CX4-*` 候选都必须建立在：
   - `RS cost field` 根基；
   - accepted `CX3-D / RS-HPG` conservative branch；
   之上，而不是重新回到大范围结构编辑。

第四轮设计原则：
1. 默认 baseline 不再是“plain residual”，而是 accepted `CX3-D`；
2. 新增模块只负责**受约束的 hard-opportunity 放大**；
3. `parasol_misc` 继续作为 protected subgroup；
4. 所有 hard bonus 都必须接受“是否真的优于 `CX3-D`”的 baseline-relative 审查；
5. 仍然严格执行 public-first + same-alpha + no-leak 协议。

冻结候选路线（下一轮按 `CX4-A -> CX4-D -> CX4-C -> CX4-B` 顺序执行）：

##### CX4-A：RS-PDL — Protected Dual-Lagrangian Opportunity Field
类型：`需要新增基础模型模块`
核心想法：
1. 将 accepted `CX3-D` 作为 conservative baseline field；
2. 额外学习一个 hard-opportunity field `o(x)`；
3. 训练 / 选型时用 dual-Lagrangian 目标直接约束 misc 风险预算，形式上类似：
   `max E_hard[ΔJ] - λ max(0, E_misc[R] - ε)`；
4. 目标是在 misc 预算固定的条件下，尽可能放大 hard-family 收益。
与现有工作的差异：
1. 不是 generic GroupDRO；
2. 不是 generic abstention；
3. 而是**基于 accepted heuristic baseline 的场级 protected improvement module**。
理论抓手：
1. KKT / dual feasibility 可直接解释“何时允许 hard gain、何时必须回退”；
2. misc risk budget 与 hard opportunity gain 的权衡可 paper-facing 地写成约束优化问题。

##### CX4-B：RS-AGS — Adversarial Group-Sliced Micro-Patches
类型：`需要新增基础模型模块`
核心想法：
1. 基于 dev-only counterexamples 发现当前 `CX3-D` 仍然表现差的 hard slices；
2. 为这些 slices 学一组 sparse micro-patches，而不是全局 field；
3. patches 只有在 `CX3-D` guard 已接受该 scene 时才允许激活；
4. 目标是把增益集中打到最需要的 hard slices 上，而不是稀释到全空间。
与现有工作的差异：
1. 不同于 prototype memory，这不是全局 prototype retrieval；
2. 不同于 latent partition，这里是**从当前错误中对抗式发现的 error-prone slices**。
理论抓手：
1. patch support 稀疏可给出 perturbation 预算；
2. 若 slice activation 在 misc 上近零，则 misc regression 继续受控。

##### CX4-C：RS-CBE — Conformal Budgeted Editing
类型：`需要新增基础模型模块`
核心想法：
1. 保留 `CX3-D` 的 conservative branch；
2. 学一个 hard-opportunity score map，但不直接激活它；
3. 通过 conformal / risk-control 方法为每个 scene 校准一个 edit budget `B(x)`；
4. 只允许 top-budget 的少数 cells 获得 hard bonus。
与现有工作的差异：
1. 不同于 binary abstention；
2. 而是**连续的 spatial edit budget calibration**。
理论抓手：
1. 若预算规则满足 misc 风险约束，则总 edit mass 与 protected risk 直接绑定；
2. 这把 hard bonus 变成“受预算限制的 sparse optimization”而非无界 dense editing。

##### CX4-D：RS-BBI — Baseline-Bootstrapped Improvement Field
类型：`需要新增基础模型模块`
核心想法：
1. 直接学习一个 baseline-relative lower-bound improvement signal `m(x)`；
2. 只有当 `m(x) > 0` 的 lower-bound 成立时，才允许在 `CX3-D` 之上添加 hard bonus；
3. 这使新模块不再问“这个 bonus 看起来像不像 hard edit”，而是问“它是否有把握优于当前 accepted baseline”。
与现有工作的差异：
1. 不同于 `CX3-A` 的置信度 abstention；
2. 不同于 safe policy improvement 的 action-level baseline；
3. 而是**heuristic field edit 的 baseline-bootstrapped margin gating**。
理论抓手：
1. 若 lower-bound margin 为正且 support 有界，则 baseline-relative regression 被抑制；
2. 这为“在保守主分支上做可认证增益”提供了最直接的 paper logic。

推荐执行顺序与原因：
1. **先做 `CX4-A / RS-PDL`**：最贴近当前 accepted `CX3-D` 的主逻辑；
2. **再做 `CX4-D / RS-BBI`**：最适合把“是否真优于 baseline”做成主对象；
3. **再做 `CX4-C / RS-CBE`**：适合做更精细的 budgeted sparse amplification；
4. **最后做 `CX4-B / RS-AGS`**：它潜力高，但波动也可能最大。

本阶段结论：
1. `CX4` 不应抛弃 `CX3-D`，而应把它视作 trusted conservative base；
2. 当前首选：`CX4-A / RS-PDL`；
3. 当前最值得做的 baseline-relative follow-up：`CX4-D / RS-BBI`；
4. 当前 `CX3-D` 的 paper定位已经收口完毕，后续新候选必须默认遵守 `paper/rs_cx_current_claim_contract.md` 的 claim boundary。



本轮实现结果（`2026-03-08`，对应产物：`reports/rs_p0cx4_round1_summary.md`、`outputs/rs_p0cx4_round1_summary/summary.csv`）：
1. **`CX4-A / RS-PDL`**：
   - 相对 `Plain-Residual` 仍有一定 expansions 改善，但相对 accepted `CX3-D` 在 public `exp4` 上反而恶化 `-44.778`；
   - `narrow_passage` 上相对 `CX3-D` 有局部改善，但 `flange` 与 ordinary-scene 代价明显更差；
   - 结论：**dual-Lagrangian 方向有信号，但当前实现还不足以替代 `CX3-D`**。
2. **`CX4-D / RS-BBI`**：
   - 这是最贴近“是否真优于 baseline”逻辑的候选；
   - 但当前实现无论相对 `Plain-Residual` 还是相对 `CX3-D` 都未形成净增益；
   - 结论：**baseline-bootstrapped improvement 的建模对象是对的，但当前 proxy 还不够强**。
3. **`CX4-C / RS-CBE`**：
   - 相对 `Plain-Residual` 仍有小幅正增益（`exp4 ≈ +6.278`），且 `narrow_passage` 相对 `CX3-D` 有改善；
   - 但它在 `flange` 与 overall `exp4` 上仍劣于 accepted `CX3-D`；
   - 结论：**budgeted sparse amplification 是本轮最接近可继续推进的 `CX4` 分支，但还不够把主线从 `CX3-D` 切换出去**。
4. **`CX4-B / RS-AGS`**：
   - 基本退化成 accepted `CX3-D` 的等价实现，几乎没有新增价值；
   - 结论：**micro-patch 路线当前未产生实质性增益**。
5. **汇总结论 / go-no-go**：
   - 本轮没有任何 `CX4` 候选在 public `exp4` 平均 expansions 上击败 accepted `CX3-D`；
   - 因而 `CX3-D` 仍是当前唯一 accepted 主线；
   - `CX4-C` 可以保留为“下一轮若继续冲 hard-family amplification，最值得继续的 `CX4` 分支”；
   - 但当前没有候选值得推进到替代主线或 expanded hard accepted evidence。
6. **本轮产物**：
   - 主实验：`reports/rs_p0cx4_cx4_a_main_v1.md`、`reports/rs_p0cx4_cx4_d_main_v1.md`、`reports/rs_p0cx4_cx4_c_main_v1.md`、`reports/rs_p0cx4_cx4_b_main_v1.md`；
   - 消融：`reports/rs_p0cx4_cx4_a_ablation_v1.md`、`reports/rs_p0cx4_cx4_d_ablation_v1.md`、`reports/rs_p0cx4_cx4_c_ablation_v1.md`、`reports/rs_p0cx4_cx4_b_ablation_v1.md`；
   - 汇总：`reports/rs_p0cx4_round1_summary.md`、`outputs/rs_p0cx4_round1_summary/summary.csv`、`outputs/rs_p0cx4_round1_summary/summary.json`。



7. **当前主线逻辑的最新收口**：
   - 当前 accepted `P0-CX` 主线仍是：`RS cost field + refined CX3-D / RS-HPG`；
   - `CX4` 首轮实现未产生可替代分支，因此后续新候选都必须默认以该 accepted 主线为 trusted baseline；
   - 这意味着 `CX5` 不是重开新炉，而是“在 accepted `CX3-D` 上继续做下一层受保护增益模块”。

#### P0-CX5：基于 accepted `CX3-D` 的下一轮候选设计（当前下一轮执行入口）
状态：`IN_PROGRESS（2026-03-09：CX5-A/B/C/D 首轮实现与主实验矩阵已完成；四条路线均未替代 accepted CX3-D 主线）`
是否需要模型/方法修改：`是（但必须建立在 accepted CX3-D 主线之上）`

触发原因：
1. `CX3-D` 已经证明自己是当前最稳的保守正分支，但总体增益仍偏弱，且 `narrow_passage` 仍有负项；
2. `CX4` 的经验说明：直接再叠一层通用 hard-opportunity field 不足以击败 accepted `CX3-D`；
3. 因此 `CX5` 的重点不再是“更强的 field amplification”，而是：
   - 更准确地判断**哪一种 hard edit**值得做；
   - 更准确地判断**在哪里做**；
   - 并继续以 `parasol_misc` 作为 protected regime 约束。

调研产物：
1. 详细调研与候选论证已直接固化在本节冻结说明中；首轮实现总结见：`reports/rs_p0cx5_round1_summary.md`；
2. 当前 accepted paper-facing claim contract 仍见：`paper/rs_cx_current_claim_contract.md`；
3. `CX5` 的所有候选都默认以 accepted `CX3-D` 为 baseline，而不是回到 `Plain-Residual` 或更早失败路线。

第五轮设计原则：
1. 新模块必须是 **baseline-relative** 的；
2. 新增 edit 必须是 **sparse / local / protected** 的；
3. 优先使用 failure traces、intervention uplift、discrete protected allocation，而不是再做一张全球 score map；
4. `parasol_misc` 继续作为 protected subgroup；
5. `narrow_passage` 继续作为首要 amplification 目标。

冻结候选路线（下一轮按 `CX5-A -> CX5-B -> CX5-C -> CX5-D` 顺序执行）：

##### CX5-A：RS-TAU — Treatment-Aware Uplift Field
类型：`需要新增基础模型模块`
核心想法：
1. 在 accepted `CX3-D` 之上定义多个候选 local edit actions；
2. 学每个 action 相对 baseline 的 uplift `τ_a(x)`；
3. 仅在 lower-confidence uplift 为正、且 misc 风险受控时，激活对应 action；
4. 本质上做的是“哪种 hard bonus 在这里相对 baseline 真正有效”。
与现有工作的差异：
1. 不同于 `CX4-D` 的 generic margin map；
2. 这里显式学习的是**不同 edit interventions 的 uplift**。
理论抓手：
1. 若 `LCB(τ_a) > 0` 且 misc-risk bound 满足约束，则每次局部干预都可解释为 baseline-improving；
2. 这是当前 accepted `CX3-D` 最自然的下一层机会模型。

##### CX5-B：RS-CTS — Culprit Trace Shaping
类型：`需要新增基础模型模块`
核心想法：
1. 基于 accepted `CX3-D` 在 hard dev cases 上的失败 / 高扩展轨迹，学习 culprit predecessor funnel；
2. 只沿这些 culprit funnels 做微小 shaping，而不是在整个 hard zone 做 bonus；
3. 目标是修补当前 `narrow_passage` 的早期错误承诺，而非全局提高 hard signal。
与现有工作的差异：
1. 不同于 patch memory；
2. 不同于 region partition；
3. 这是**从实际搜索轨迹中回溯出的错误前驱场**。
理论抓手：
1. 失败轨迹可分解为 predecessor funnel + terminal bad pocket；
2. 只修 predecessor funnel 可以保持 sparse support，同时更直接地作用于扩展数。

##### CX5-C：RS-PAA — Protected Action Auction
类型：`需要新增基础模型模块`
核心想法：
1. 生成少量 candidate edit atoms；
2. 每个 atom 估计 hard gain / misc cost / support mass；
3. 通过一个小型 scene-level knapsack / auction 选择有限个最优 atoms；
4. 目标是从“连续 score map top-k”升级为“离散保护型 action selection”。
与现有工作的差异：
1. 不同于 `CX4-C` 的单一 budget map；
2. 这里做的是**heterogeneous edit actions 的受保护选择**。
理论抓手：
1. 可直接写成 `max Σ g_i z_i` s.t. `Σ c_i z_i <= B_misc`；
2. misc budget 与 support budget 都显式可控。

##### CX5-D：RS-GRO — Group-Robust Opportunity Heads
类型：`需要新增基础模型模块`
核心想法：
1. 在 accepted `CX3-D` 上发现若干 hard opportunity groups；
2. 为每个组学习单独的 opportunity head；
3. 用 worst-group improvement objective 训练，同时显式保护 misc group；
4. 目标是让 hard amplification 不再由一个统一 bonus 头负责。
与现有工作的差异：
1. 不同于 `CX3-B` 的 region partition；
2. 不同于 `CX4-B` 的 patch bank；
3. 这是**围绕 baseline-relative gain 的 group-specific heads**。
理论抓手：
1. 若 worst-group gain 为正且 protected misc group 约束成立，则更接近 `P0-CX` 真正想要的“hard family 放大且 misc 不坏”。

推荐执行顺序与原因：
1. **先做 `CX5-A / RS-TAU`**：最直接承接 accepted `CX3-D` 的 baseline-relative 逻辑；
2. **再做 `CX5-B / RS-CTS`**：最针对当前 `narrow_passage` 弱点；
3. **再做 `CX5-C / RS-PAA`**：若 uplift 有信号但需要离散保护型选择，则走 action auction；
4. **最后做 `CX5-D / RS-GRO`**：最有潜力，但也是最高方差分支。

本阶段结论：
1. `CX5` 不是“再造一个新分支”，而是围绕 accepted `CX3-D` 做下一层 hard-opportunity module；
2. 当前首选：`CX5-A / RS-TAU`；
3. 当前最针对当前短板的 follow-up：`CX5-B / RS-CTS`；
4. 后续 `P0-CX` 继续推进时，应默认遵守 `paper/rs_cx_current_claim_contract.md` 的 claim boundary。



本轮实现结果（`2026-03-09`，对应产物：`reports/rs_p0cx5_round1_summary.md`、`outputs/rs_p0cx5_round1_summary/summary.csv`）：
1. **`CX5-A / RS-TAU`**：
   - 它最贴近“intervention uplift over accepted baseline”的方向；
   - 但相对 accepted `CX3-D` 在 public `exp4` 上仍恶化约 `-33.833` expansions；
   - 结论：**uplift-style intervention modeling 方向有概念价值，但当前实现还不足以超过 accepted `CX3-D`**。
2. **`CX5-B / RS-CTS`**：
   - 明显退化，尤其在 `narrow_passage / flange` 上损失很大；
   - 结论：**culprit-trace shaping 当前应冻结为负结果证据**。
3. **`CX5-C / RS-PAA`**：
   - 基本退化为 accepted `CX3-D` 的等价实现：相对 `CX3-D` 的平均 expansions 差异几乎为 0；
   - 结论：**protected action auction 当前没有带来超越 accepted baseline 的新增价值**。
4. **`CX5-D / RS-GRO`**：
   - 作为 group-robust opportunity heads，当前结果与 accepted `CX3-D` 几乎持平但略差；
   - 结论：**group-specific heads 方向仍值得保留为未来参考，但这轮没有形成净突破**。
5. **汇总结论 / go-no-go**：
   - 本轮没有任何 `CX5` 候选在 public `exp4` 平均 expansions 上击败 accepted `CX3-D`；
   - 因此 accepted 主线保持不变：仍是 `RS cost field + refined CX3-D / RS-HPG`；
   - `CX5-A` 和 `CX5-D` 是概念上最值得保留的两条后续线，但都不足以在当前证据下替代主线；
   - `CX5-C` 说明“离散保护型 action selection”在当前实现下只是复现 accepted 主线；
   - `CX5-B` 则可直接冻结为失败证据。
6. **本轮产物**：
   - 主实验：`reports/rs_p0cx5_cx5_a_main_v1.md`、`reports/rs_p0cx5_cx5_b_main_v1.md`、`reports/rs_p0cx5_cx5_c_main_v1.md`、`reports/rs_p0cx5_cx5_d_main_v1.md`；
   - 消融：`reports/rs_p0cx5_cx5_a_ablation_v1.md`、`reports/rs_p0cx5_cx5_b_ablation_v1.md`、`reports/rs_p0cx5_cx5_c_ablation_v1.md`、`reports/rs_p0cx5_cx5_d_ablation_v1.md`；
   - 汇总：`reports/rs_p0cx5_round1_summary.md`、`outputs/rs_p0cx5_round1_summary/summary.csv`、`outputs/rs_p0cx5_round1_summary/summary.json`。



7. **当前主线逻辑的最新收口**：
   - 当前 accepted `P0-CX` 主线仍是：`RS cost field + refined CX3-D / RS-HPG`；
   - `CX4` 与 `CX5` 首轮实现都未替代它；
   - 这意味着 `CX6` 的目标不是再造一张新 heuristic family，而是：在 accepted `CX3-D` 上继续叠加**accountable、protected、sparse** 的 hard-opportunity module。

#### P0-CX6：基于 accepted `CX3-D` 的 accountable/protected 增益模块（当前下一轮执行入口）
状态：`IN_PROGRESS（2026-03-09：CX6-A/B/C/D 首轮实现与主实验矩阵已完成；四条路线均未替代 accepted CX3-D 主线）`
是否需要模型/方法修改：`是（但必须继续建立在 accepted CX3-D 主线之上）`

触发原因：
1. `CX3-D` 已经证明自己是当前最稳的保守正分支，但总体 gain 依旧偏弱；
2. `CX4` 与 `CX5` 表明：继续叠加通用 hard-opportunity field、group head 或离散 budget，并不会自动超过 accepted `CX3-D`；
3. 因此 `CX6` 需要从“场强度放大”转向“**可问责的 intervention selection**”。

调研产物：
1. 详细调研与候选论证已直接固化在本节冻结说明中；首轮实现总结见：`reports/rs_p0cx6_round1_summary.md`；
2. 当前 accepted paper-facing claim contract 仍见：`paper/rs_cx_current_claim_contract.md`；
3. `CX6` 的所有候选都默认以 accepted `CX3-D` 作为 baseline，而不是回退到 `Plain-Residual` 或更早失败路线。

第六轮设计原则：
1. 新模块必须是 **baseline-relative** 的；
2. 新增 intervention 必须有 **accountable / confidence-backed** 理由；
3. `parasol_misc` 继续作为 protected regime；
4. 优先做 sparse / local / certified interventions，而不是再做 dense field editing；
5. `narrow_passage` 继续作为最主要的 amplification 目标。

冻结候选路线（下一轮按 `CX6-A -> CX6-B -> CX6-C -> CX6-D` 顺序执行）：

##### CX6-A：RS-AIC — Accountable Intervention Certificates
类型：`需要新增基础模型模块`
核心想法：
1. 在 accepted `CX3-D` 上定义少量 candidate local interventions；
2. 为每个 intervention 计算 lower-confidence improvement certificate；
3. 只有当 certificate 为正且 misc-cost bound 满足时，才允许 intervention 激活；
4. 目标是把“有没有资格覆盖 baseline”做成第一性对象。
与现有工作的差异：
1. 不同于 uplift score；
2. 不同于 generic confidence abstention；
3. 这里的关键对象是**accountable intervention certificate**。
理论抓手：
1. 若 `LCB(ΔJ_i) > 0` 且 protected risk 约束成立，则 intervention `i` 可解释为 baseline-improving；
2. 这与当前 accepted `CX3-D` 的 paper-facing claim contract 最自然地衔接。

##### CX6-B：RS-CRL — Counterfactual Replay Localizer
类型：`需要新增基础模型模块`
核心想法：
1. 从 accepted `CX3-D` 的 hard-case traces 中找出可疑 predecessor states；
2. 在这些 states 周围做短程 counterfactual local replay；
3. 只在 replay 证实“局部 intervention 能改善后续搜索行为”的位置启用 sparse edit；
4. 目标是更直接地修补 `narrow_passage` 的早期错误承诺。
与现有工作的差异：
1. 不同于 raw trace shaping；
2. 这里是**counterfactual replay-certified localization**。
理论抓手：
1. replay 层面若已能证明局部 monotone improvement，则该 intervention 的支持域可被视为局部证据；
2. 由于支持域稀疏，misc 保护更容易保留。

##### CX6-C：RS-PMC — Protected Multicalibrated Editors
类型：`需要新增基础模型模块`
核心想法：
1. 对候选 interventions 的 hard-gain / misc-cost 预测做 multicalibration；
2. 让 intervention selection 不再依赖未经校准的 raw score；
3. 只在 gain/cost 估计都足够可信的 bins / subgroups 上启用 sparse bonus。
与现有工作的差异：
1. 不同于 `CX4-C` 的 budget rule；
2. 不同于 `CX5-D` 的 group heads；
3. 这里是**针对 intervention trustworthiness 的 subgroup calibration layer**。
理论抓手：
1. 若 gain/cost 估计 multicalibrated，则 protected thresholding 的可信度更高；
2. 这为“protected improvement”提供了比 raw score 更强的统计解释。

##### CX6-D：RS-DCE — Decoupled Counterexample Editors
类型：`需要新增基础模型模块`
核心想法：
1. 在 accepted `CX3-D` 上通过 adversarial group discovery 找出 hard counterexample groups；
2. 为 misc branch 和若干 hard groups 分别学习 decoupled tiny editors；
3. 仍然由 accepted `CX3-D` 先做 conservative gating，再决定是否调用某个 hard editor；
4. 目标是让不同 hard failure mode 有机会用不同 intervention family。
与现有工作的差异：
1. 不同于单一 group-robust head；
2. 这是**decoupled editors on top of a trusted conservative branch**。
理论抓手：
1. decoupling 让 protected 与 hard opportunity branch 的职责分开；
2. discovered groups 让编辑对象不再被人工写死。

推荐执行顺序与原因：
1. **先做 `CX6-A / RS-AIC`**：最贴近当前 accepted `CX3-D` 的 paper-facing 逻辑；
2. **再做 `CX6-B / RS-CRL`**：最直接针对当前 `narrow_passage` 弱项；
3. **再做 `CX6-C / RS-PMC`**：如果真正瓶颈是 score 校准不准，则优先做这一层；
4. **最后做 `CX6-D / RS-DCE`**：潜力大，但也是最容易高方差的分支。

本阶段结论：
1. `CX6` 不应再寻找另一条与 `CX3-D` 平行的大主线；
2. 当前首选：`CX6-A / RS-AIC`；
3. 当前最针对当前短板的 follow-up：`CX6-B / RS-CRL`；
4. 后续继续推进 `P0-CX` 时，必须默认遵守 `paper/rs_cx_current_claim_contract.md` 的 claim boundary。



本轮实现结果（`2026-03-09`，对应产物：`reports/rs_p0cx6_round1_summary.md`、`outputs/rs_p0cx6_round1_summary/summary.csv`）：
1. **`CX6-A / RS-AIC`**：
   - 这是最接近“可问责 intervention certificate”逻辑的候选；
   - 但它相对 accepted `CX3-D` 在 public `exp4` 上仍有小幅退化（约 `-0.667` expansions）；
   - 结论：**AIC 方向概念成立，但当前 certificate proxy 还不足以带来净增益**。
2. **`CX6-B / RS-CRL`**：
   - 作为 replay-based localizer，它在整体与各 hard-family 上都明显退化；
   - 结论：**当前应冻结为失败证据**。
3. **`CX6-C / RS-PMC`**：
   - multicalibrated editor 思路成立，但当前实现过于保守，整体仍落后 accepted `CX3-D`；
   - 结论：**可以作为思路保留，但本轮没有形成净突破**。
4. **`CX6-D / RS-DCE`**：
   - 这是本轮最有希望的 follow-up；
   - 它相对 accepted `CX3-D` 在 public 平均 expansions 上只有极小改善（约 `+0.611 / +0.611`），方向为正但不足以支撑主线切换；
   - 结论：**可保留为弱正 follow-up，但不能提升为 accepted 主线**。
5. **汇总结论 / go-no-go**：
   - 本轮没有任何 `CX6` 候选足以替代 accepted `CX3-D` 主线；
   - `CX6-D` 是唯一仍值得保留为后续参考的 `CX6` 分支；
   - `CX6-A` 也具有方法论价值，但当前 proxy 太弱；
   - `CX6-B/C` 则不足以继续消耗主资源。
6. **本轮产物**：
   - 主实验：`reports/rs_p0cx6_cx6_a_main_v1.md`、`reports/rs_p0cx6_cx6_b_main_v1.md`、`reports/rs_p0cx6_cx6_c_main_v1.md`、`reports/rs_p0cx6_cx6_d_main_v1.md`；
   - 消融：`reports/rs_p0cx6_cx6_a_ablation_v1.md`、`reports/rs_p0cx6_cx6_b_ablation_v1.md`、`reports/rs_p0cx6_cx6_c_ablation_v1.md`、`reports/rs_p0cx6_cx6_d_ablation_v1.md`；
   - 汇总：`reports/rs_p0cx6_round1_summary.md`、`outputs/rs_p0cx6_round1_summary/summary.csv`、`outputs/rs_p0cx6_round1_summary/summary.json`；
   - 轻量统计：`reports/rs_p0cx6_stats_v1.md`。



本轮实现结果（`2026-03-09`，对应产物：`reports/rs_p0cx6_round1_summary.md`、`outputs/rs_p0cx6_round1_summary/summary.csv`）：
1. **`CX6-A / RS-AIC`**：
   - 这是最贴近“可问责 intervention certificate”逻辑的候选；
   - 但相对 accepted `CX3-D` 在 public `exp4` 上仍有小幅退化（约 `-0.667` expansions）；
   - 结论：**AIC 方向概念成立，但当前证书 proxy 还不足以超过 accepted `CX3-D`**。
2. **`CX6-B / RS-CRL`**：
   - replay-localization 当前明显为负结果；
   - 结论：**应冻结为失败证据**。
3. **`CX6-C / RS-PMC`**：
   - multicalibrated editor 方向在当前实现下过于保守，整体仍落后 accepted `CX3-D`；
   - 结论：**可以作为方法思路保留，但本轮没有形成净突破**。
4. **`CX6-D / RS-DCE`**：
   - 这是本轮最有希望的 follow-up；
   - 相对 accepted `CX3-D` 在 public 平均 expansions 上只有极小改善（约 `+0.611 / +0.611`），方向为正但远不足以支撑主线切换；
   - 结论：**可保留为弱正 follow-up，但不能提升为 accepted 主线**。
5. **汇总结论 / go-no-go**：
   - 本轮没有任何 `CX6` 候选足以替代 accepted `CX3-D` 主线；
   - 因此 accepted 主线继续保持为 `RS cost field + refined CX3-D / RS-HPG`；
   - `CX6-D` 是唯一值得保留为下一轮参考的 `CX6` 分支；
   - `CX6-A` 也有方法论价值，但当前证书 proxy 仍偏弱；
   - `CX6-B/C` 则不足以继续消耗主资源。
6. **本轮产物**：
   - 主实验：`reports/rs_p0cx6_cx6_a_main_v1.md`、`reports/rs_p0cx6_cx6_b_main_v1.md`、`reports/rs_p0cx6_cx6_c_main_v1.md`、`reports/rs_p0cx6_cx6_d_main_v1.md`；
   - 消融：`reports/rs_p0cx6_cx6_a_ablation_v1.md`、`reports/rs_p0cx6_cx6_b_ablation_v1.md`、`reports/rs_p0cx6_cx6_c_ablation_v1.md`、`reports/rs_p0cx6_cx6_d_ablation_v1.md`；
   - 汇总：`reports/rs_p0cx6_round1_summary.md`、`outputs/rs_p0cx6_round1_summary/summary.csv`、`outputs/rs_p0cx6_round1_summary/summary.json`；
   - 轻量统计：`reports/rs_p0cx6_stats_v1.md`。



7. **当前主线逻辑的最新收口**：
   - 当前 accepted `P0-CX` 主线仍是：`RS cost field + refined CX3-D / RS-HPG`；
   - `CX4`、`CX5`、`CX6` 首轮实现均未替代它；
   - 因而 `CX7` 的目标不再是“设计另一张 hard-opportunity 场”，而是：在 accepted `CX3-D` 上做**accountable / calibrated / baseline-relative 的 intervention decision layer**。

#### P0-CX7：基于 accepted `CX3-D` 的 accountable intervention decision layer（首轮已完成，未晋升主线）
状态：`COMPLETED（2026-03-09：CX7-A/B/C/D 首轮实现与主实验矩阵已完成；四条路线均未替代 accepted CX3-D 主线）`
是否需要模型/方法修改：`是（但必须继续建立在 accepted CX3-D 主线之上）`

触发原因：
1. `CX3-D` 仍是当前唯一 accepted 主线；
2. `CX4/CX5/CX6` 说明：再叠加一层普通 hard-opportunity score/budget/head，并不会自动超过 accepted baseline；
3. 因此 `CX7` 需要从“设计更强 score”转向“设计更可信的 intervention decision”。

调研产物：
1. 详细调研与候选论证已直接固化在本节冻结说明中；首轮实现总结见：`reports/rs_p0cx7_round1_summary.md`；
2. 当前 accepted paper-facing claim contract 仍见：`paper/rs_cx_current_claim_contract.md`；
3. 所有 `CX7` 候选都默认以 accepted `CX3-D` 作为 baseline，而不是回退到 `Plain-Residual` 或更早失败路线。

第七轮设计原则：
1. intervention 决策必须是 **baseline-relative** 的；
2. 必须有 **accountable / certificate-like** 的 override 理由；
3. `parasol_misc` 继续作为 protected regime；
4. 新增 intervention 依然必须 sparse / local；
5. `narrow_passage` 继续作为主要 amplification 目标，但不允许再用纯 hard score 图的方式硬推。

冻结候选路线（首轮已全部实现；原计划执行顺序为 `CX7-A -> CX7-B -> CX7-D -> CX7-C`）：

##### CX7-A：RS-EAC — Evidence-Accumulating Certificates
类型：`需要新增基础模型模块`
核心想法：
1. 为候选局部 intervention 聚合多种证据：hard-gain、misc-cost、uncertainty、subgroup-calibrated trust；
2. 只有当聚合后的 certificate 过阈值时，才允许覆盖 accepted `CX3-D`；
3. 否则默认保持 baseline。 
与现有工作的差异：
1. 不再依赖单一 improvement score；
2. 核心对象是**多证据聚合后的 intervention certificate**。 
理论抓手：
1. 若 aggregated lower-bound 仍为正，则 intervention 才有“可问责地优于 baseline”的资格；
2. 这是当前 claim contract 最自然的扩展方向。

##### CX7-B：RS-CCD — Counterexample Choice Duel
类型：`需要新增基础模型模块`
核心想法：
1. 让多个 candidate interventions 与 null action（保持 `CX3-D`）做 pairwise duel；
2. 只有 duel 明确赢过 baseline 的 intervention 才能被部署；
3. 若没有 clear winner，则退回 accepted `CX3-D`。
与现有工作的差异：
1. 不同于独立 uplift score；
2. 这里做的是**pairwise accountable choice among interventions**。 
理论抓手：
1. intervention 若持续赢过 baseline，才取得 override 权；
2. 这让“是否替换 baseline”本身变成一个离散可问责决策。

##### CX7-C：RS-OMI — Omnipredictive Intervention Head
类型：`需要新增基础模型模块`
核心想法：
1. 训练一个可同时支持 hard gain、misc cost、path perturbation、support mass 等目标的 shared representation；
2. intervention layer 再在这个 representation 上做不同约束下的决策；
3. 目标是避免每个候选都依赖一套脆弱的单任务 proxy。
与现有工作的差异：
1. 不只是 calibration；
2. 而是**支持多个 downstream intervention objectives 的共享表示**。 
理论抓手：
1. 若一个表示能支持多种 constrained decision objectives，则 intervention 规则可更稳地替换，而不必每轮重学新 score。 

##### CX7-D：RS-DHA — Decoupled Head Arbitration
类型：`需要新增基础模型模块`
核心想法：
1. 保留 accepted `CX3-D` 主干；
2. 训练多个 decoupled sparse specialist editors；
3. 再训练一个 subgroup-safe arbiter，决定是否启用某个 specialist 或保持 baseline；
4. 目标是把“强 hard specialization”和“安全 fallback”结构性解耦。
与现有工作的差异：
1. 不同于直接 group heads；
2. 这里显式区分 **editor generation** 和 **editor arbitration**。 
理论抓手：
1. 若 arbiter 经过 subgroup-safe calibration，则 stronger specialists 也不会轻易破坏 protected baseline 语义。 

推荐执行顺序与原因：
1. **先做 `CX7-A / RS-EAC`**：最贴近当前 accepted `CX3-D` 的 claim contract；
2. **再做 `CX7-B / RS-CCD`**：最适合验证“离散选择而非连续评分”是不是缺失环节；
3. **再做 `CX7-D / RS-DHA`**：如果 specialization 仍然需要，但必须有独立 arbiter 才安全；
4. **最后做 `CX7-C / RS-OMI`**：最重、最像长期路线。

本阶段结论：
1. `CX7` 不应再设计另一套 raw opportunity map；
2. 当前首选：`CX7-A / RS-EAC`；
3. 当前最值得验证的离散决策 follow-up：`CX7-B / RS-CCD`；
4. 后续推进 `P0-CX` 时，必须默认遵守 `paper/rs_cx_current_claim_contract.md` 的 claim boundary。



本轮实现结果（`2026-03-09`，对应产物：`reports/rs_p0cx7_round1_summary.md`、`outputs/rs_p0cx7_round1_summary/summary.csv`）：
1. **`CX7-A / RS-EAC`**：
   - 这是最贴近“evidence-accumulating certificate”逻辑的候选；
   - 但相对 accepted `CX3-D` 在 public `exp4` 上仍有小幅退化（约 `-0.667` expansions）；
   - 结论：**多证据证书方向有价值，但当前证书聚合还不足以超过 accepted baseline**。
2. **`CX7-B / RS-CCD`**：
   - pairwise duel 路线在当前实现下未形成净增益；
   - 结论：**可冻结为负结果证据**。
3. **`CX7-C / RS-OMI`**：
   - 这是本轮最有希望的 follow-up；
   - 相对 accepted `CX3-D` 在 public 平均 expansions 上仅有极小改善（约 `+5.889 / +5.889`），方向为正但统计上仍很弱；
   - 结论：**可保留为弱正 follow-up，但不足以切换主线**。
4. **`CX7-D / RS-DHA`**：
   - decoupled arbitration 路线在当前实现下仍弱于 accepted `CX3-D`；
   - 结论：**暂不继续作为主资源投入方向**。
5. **汇总结论 / go-no-go**：
   - 本轮没有任何 `CX7` 候选足以替代 accepted `CX3-D` 主线；
   - `CX7-C` 是唯一仍可保留为弱正 follow-up 的 `CX7` 分支；
   - 但整体上，`CX7` 也没有完成 `P0-CX` 所要求的更强、可主文支撑的优势区间。
6. **本轮产物**：
   - 主实验：`reports/rs_p0cx7_cx7_a_main_v1.md`、`reports/rs_p0cx7_cx7_b_main_v1.md`、`reports/rs_p0cx7_cx7_c_main_v1.md`、`reports/rs_p0cx7_cx7_d_main_v1.md`；
   - 消融：`reports/rs_p0cx7_cx7_a_ablation_v1.md`、`reports/rs_p0cx7_cx7_b_ablation_v1.md`、`reports/rs_p0cx7_cx7_c_ablation_v1.md`、`reports/rs_p0cx7_cx7_d_ablation_v1.md`；
   - 汇总：`reports/rs_p0cx7_round1_summary.md`、`outputs/rs_p0cx7_round1_summary/summary.csv`、`outputs/rs_p0cx7_round1_summary/summary.json`；
   - 轻量统计：`reports/rs_p0cx7_stats_v1.md`。


8. **当前主线逻辑的再收口（从 `CX7` 过渡到 `CX8`）**：
   - 当前 accepted `P0-CX` 主线仍是：`RS cost field + refined CX3-D / RS-HPG`；
   - 从 `rs_cx/common.py`、`rs_cx3/cx3_d_hpg.py` 到 `rs_cx7/common.py`，`CX1-CX7` 的主体范式仍是：**构造一张 dense residual / opportunity / certificate map，再把它叠加回启发场**；
   - 但 `planner/hybrid_astar.py:237-272` 才是真正决定 `Hybrid A*` 搜索命运的位置：这里逐个生成、模拟、过滤并入队 `motion_primitives`；
   - 对 Ackermann 非完整约束规划，困难 case 的主要失误往往不是“全局代价值偏差一点点”，而是“局部 primitive 选错”：
     1. 过早进入不可恢复的死胡同；
     2. 在 clearance 不足的区域反复尝试无效 steering sign；
     3. 错过需要提前 reverse-setup 的多步 maneuver；
   - 因而 `CX8` 必须把主对象从“field correction”转向“**successor-action intervention / kinematic feasibility prior / search-dynamics control**”。

#### P0-CX8：从 `RS` 代价场修正转向 `Hybrid A*` 动作级干预（已冻结为失败路线）
状态：`FAILED（2026-03-09：CX8-A/B/D 已在 hard-family calib 上完成 dev-only pilot，CX8-D-Lite-Reorder 最后尝试后仍无法同时满足正向增益与效率门槛）`
是否需要模型/方法修改：`是（且这次必须显式修改 planner decision layer，而不只是继续做 dense field editing）`

触发原因：
1. `CX1-CX7` 基本都还在“修正启发场”的范式内，即便加入了 guard / certificate / arbitration，也主要发生在 `field` 层，而不是 `successor` 层；
2. `CX7` 的失败说明：即使把 dense map 上的 accountable decision 做得更复杂，若仍不真正触碰 `Hybrid A*` 的动作扩展逻辑，也很难越过 `CX3-D` 的上限；
3. 当前需要的不是再造一张更复杂的 scalar field，而是：
   - 直接干预 `motion_primitives` 的排序 / 屏蔽 / commit；
   - 将 Ackermann 非完整约束的结构先验（最小转弯半径、reverse-setup、曲率连续性、局部可恢复性）显式注入搜索；
   - 在保留 accepted `CX3-D` 的保守 fallback 前提下，建立新的显著优势轴。

调研综述（顶会 / 顶刊主线 + 最近 preprint 趋势）：
1. **学习 heuristic / search guidance 主线**：
   - `Learning Heuristic Search via Imitation`（CoRL 2018）：<https://proceedings.mlr.press/v87/chitnis18a.html>
   - `Neural A* Search by Differentiable Priority Queue`（ICML 2021）：<https://proceedings.mlr.press/v139/yonetani21a.html>
   - `Policy-Guided Heuristic Search with Guarantees`（recent preprint, 2021）：<https://arxiv.org/abs/2103.11505>
   - `Hybrid Search for Efficient Planning with Completeness Guarantees`（NeurIPS 2023 / arXiv）：<https://arxiv.org/abs/2310.12819>
   - 共同启发：学习 guidance 是有效的，但最可靠的高水平方案往往都会保留 **anchor / fallback / completeness-preserving backbone**；单纯学一张 guidance map 已经很拥挤，而“带保证的 decision-layer intervention”仍有空间。
2. **非完整约束 / motion primitive 主线**：
   - `Probably Approximately Correct Vision-Based Planning using Motion Primitives`（CoRL 2021 / arXiv）：<https://arxiv.org/abs/2002.12852>
   - `Policy Optimization to Learn Adaptive Motion Primitives in Path Planning with Dynamic Obstacles`（recent preprint, 2022）：<https://arxiv.org/abs/2212.14307>
   - `Incremental Generalized Hybrid A*`（recent preprint, 2025）：<https://arxiv.org/abs/2508.13392>
   - 共同启发：在非完整约束规划里，**primitive family 的组织、局部 steering 选择、dominance / pruning 结构** 往往比再修一张全局 value map 更关键。
3. **learned proposal / seed / planner prior 主线**：
   - `Neural MP: A Generalist Neural Motion Planner`（recent preprint, 2024）：<https://arxiv.org/abs/2409.05864>
   - `DiffusionSeeder: Seeding Motion Optimization with Diffusion for Rapid Motion Planning`（recent preprint, 2024）：<https://arxiv.org/abs/2410.16727>
   - 共同启发：network 在复杂规划里更适合做 **proposal / prior / seed / filter**，而不是直接替代搜索；这与当前项目从 `RS` 根基出发、保留 search backbone 的路线高度一致。
4. **安全证书 / 可验证学习控制主线**：
   - `Learning Certified Control using Contraction Metric`（CoRL 2020 / arXiv）：<https://arxiv.org/abs/2011.12569>
   - `Neural Lyapunov Control`（NeurIPS 2020 / arXiv）：<https://arxiv.org/abs/2005.00611>
   - 共同启发：若希望 learned module 真正成为 paper-worthy contribution，它最好输出 **可验证的局部证书 / region-of-attraction / stability margin**，而不是不可解释的 dense correction。
5. **与当前项目的对应判断**：
   - `CX1-CX7` 基本都属于“学习 heuristic / dense opportunity field”的延长线；
   - 文献已经表明，该类方法最强的版本通常也要保留 fallback / anchor；
   - 而当前仓库真正还没有系统探索的是：**在 `Hybrid A*` successor 层做 action-level、nonholonomic-aware、anchor-preserving intervention**；
   - 这正是 `CX8` 的创新窗口，也是最符合当前瓶颈判断的方向。

`CX8` 的统一设计约束：
1. 所有 `CX8-*` 候选默认都建立在 accepted `RS + refined CX3-D / RS-HPG` 之上，而不是回退到 `Plain-Residual`；
2. 不允许再把主要创新点放在“再造一张更复杂的 dense field”上；
3. 新模块的主落点必须是 `planner/hybrid_astar.py:237-272` 的 successor generation / ordering / filtering 逻辑；
4. 所有 learned intervention 都必须保留 accepted anchor/fallback 语义：
   - 要么只做 successor 重排；
   - 要么只在有证书时做保守屏蔽；
   - 要么在 commit 失败时能回退到 baseline；
5. 所有 public 对比继续遵守当前协议：先做 `public parasol_narrow + mp/csm + same-alpha ablation`，不在 expanded-hard 上重新选型；
6. 代码组织必须单独分层：
   - `rs_cx8/common.py`：shared primitive-index / ego-patch / kinematic feature builder；
   - `rs_cx8/cx8_a_*.py`、`rs_cx8/cx8_b_*.py`、`rs_cx8/cx8_c_*.py`、`rs_cx8/cx8_d_*.py`：各候选独立；
   - planner 侧只增加最小 hook，不把候选逻辑杂糅进主循环。

冻结候选路线（下一轮按 `CX8-A -> CX8-B -> CX8-D -> CX8-C` 顺序执行）：

##### CX8-A：RS-APP — Action-Primitive Prior
类型：`需要新增基础模型模块 + planner successor hook`
核心想法：
1. 不再预测 dense scalar residual，而是对每个展开节点 `n` 的 primitive 集 `A(n)` 直接预测一个 preference simplex `π(a|n)`；
2. 输入采用以车辆当前朝向对齐的 ego-patch，并显式加入：`RS` 局部切向、局部 ESDF / clearance、`prev_steer`、`direction`、`reverse debt`、goal heading mismatch；
3. 在 `planner/hybrid_astar.py:237-272` 里不改变 `RS/CX3-D` 的 anchor heuristic，只改变 successor 的入队顺序或 secondary key：
   - `score(n,a) = g(n) + c(n,a) + h_RS(next) - τ log π(a|n)`；
4. 可选地做 top-k 提前入队，但必须保留一个 baseline-safe primitive 子集始终入队。
与现有 `CX` 系列的差异：
1. 主对象从 “grid cell / field value” 切到 “primitive choice”；
2. 第一次显式修改 `Hybrid A*` 的 `SUCC(n)` 逻辑，而不是把 planner 继续视作黑盒；
3. 学到的是 **动作偏好**，不是 **全局残差场**。
如何利用网络特性处理非完整约束：
1. 输出空间直接对齐固定 `steer × direction` primitive bins，天然处于 Ackermann 的低维动作流形上；
2. 输入在 ego-`SE(2)` 坐标系表达，去掉全局位姿冗余；
3. 显式纳入 `wheel_base / min_turn_radius / reverse asymmetry / heading-to-go`。
理论抓手：
1. **Anchor-preserving bounded-suboptimality**：若 baseline anchor queue 保持不变，learned prior 只改变 successor secondary ordering，则 completeness 与原有 bounded-suboptimality 语义保持；
2. **Action-level risk quantification**：把 `-log π(a|n)` 解释为 primitive search-loss surrogate，而不是 path-cost surrogate；
3. 可直接借鉴 `Policy-Guided Heuristic Search with Guarantees` 与 `Hybrid Search ...` 的“learned guidance + guaranteed fallback”结构，但创新点落在 primitive ordering。
预期优势轴：
1. `parasol_narrow` 高难 family 上的 expansions；
2. success-under-budget；
3. 尽量不牺牲 `mp/csm` ordinary scenes。

##### CX8-B：RS-KFM — Kinematic Feasibility Mask
类型：`需要新增基础模型模块 + planner successor hook`
核心想法：
1. 对每个 primitive 预测一个局部可行动作 margin：`m(s,a)`，以及 recoverability / trap-risk：`r(s,a)`；
2. 将 analytic local checks（最小转弯半径、局部 clearance、一步后 heading deviation、reverse exit possibility）与 learned margin 结合，只在“解析上近乎不可能 + 网络高置信判负”时做 hard mask；其余情况只做 soft penalty；
3. 目标不是学新的 value，而是学习一个 **primitive-safe set / viability set**。
与现有 `CX` 系列的差异：
1. 从 dense field correction 切到 action feasibility filtering；
2. 主语义是“这个 primitive 是否应被尝试”，而不是“这一片区域 heuristic 要不要抬/压”；
3. `CX3-D` 保护的是 homotopy / misc 语义，`CX8-B` 保护的是 **local recoverability**。
如何利用网络特性处理非完整约束：
1. 直接对 `state-action` 对进行建模，而不是只看静态地图；
2. 特征中显式加入 turning-circle slack、reverse escape cone、局部 corridor width 与 `RS` tube overlap；
3. 学习空间被限制在 Ackermann primitive manifold 上，明显小于 dense field 空间。
理论抓手：
1. **Barrier-style local feasibility certificate**：定义
   - `b(s,a) = clearance_after(a) - rho_turn(a) - delta_net(s,a)`；
   - 仅当 `b(s,a) < 0` 且置信下界也为负时，才允许 hard prune；
2. **Recoverability guard**：若某节点所有 primitive 都无 hard certificate，则必须回退到 soft mask，避免破坏 completeness；
3. 控制论来源不是直接做连续控制器，而是把 `CBF / viability` 思想迁移到 discrete primitive set 上。
预期优势轴：
1. `narrow_passage / flange / deadend_reverse` 风格 hard slice 的 success-under-budget；
2. 无效 expansions 的显著下降；
3. 对 `parasol_misc` 的保守保护。

##### CX8-D：RS-BCA — Bottleneck-Commit Arbitration
类型：`需要新增基础模型模块 + planner successor hook`
核心想法：
1. 先用 `RS` 场、skeleton width minima、局部失败轨迹，把当前节点是否位于“需要多步 setup 的 bottleneck regime”识别出来；
2. 不再对单个 primitive 做分数，而是定义少量 **primitive bundles / maneuver words**，例如：
   - `forward-left-thread`
   - `forward-right-thread`
   - `reverse-setup-left`
   - `reverse-setup-right`
3. 网络预测 bundle viability `q(B|n)` 与 recovery margin `u(B|n)`；若某 bundle 证据明显更强，则在接下来一个短 horizon 内对该 bundle 做 budget boost / competing bundle suppression；
4. 若 commit 后 progress certificate 不成立，则立即 rollback 到 accepted baseline。
与现有 `CX` 系列的差异：
1. `CX3-D` 是 field-level 的 topology-preserving guard；`CX8-D` 是 search-time 的 maneuver-bundle arbitration；
2. 不再试图用单步 scalar field 表达多步 maneuver；
3. 首次把“reverse-setup”作为显式的 learned decision object。
如何利用网络特性处理非完整约束：
1. bundle vocabulary 直接由 steering sign sequence、forward/reverse phase 与 curvature slack 构成；
2. 网络不需要学习连续轨迹生成，只需在少量 kinematically meaningful bundles 间做判别；
3. 与 `RS` 场天然兼容：`RS` 给 global geometric pull，bundle head 负责 bottleneck 中的 multi-step local commit。
理论抓手：
1. **Homotopy / maneuver consistency with rollback**：只有当 `q(B|n) - λ·risk(B|n) > 0` 且 `u(B|n) > 0` 时才允许短时 commit；
2. **No-worse-than-baseline protected semantics**：rollback 失败后立刻回到 accepted `CX3-D`，因此不会在 protected regime 上长期偏离 baseline；
3. 该方案最有机会把“为什么 narrow case 需要多步 setup”明确写成方法点，而不是仅靠现象解释。
预期优势轴：
1. `parasol_narrow` 中需要 reverse-setup / branch commitment 的子类；
2. relative success lift；
3. hard-family expansions 的更大幅改善。

##### CX8-C：RS-TDG — Tree-Dynamics Governor
类型：`需要新增基础模型模块 + planner online-state hook`
核心想法：
1. 把 planner 的在线状态也作为输入，而不是只看静态地图 patch：
   - open-list entropy；
   - heading dispersion；
   - invalid-successor ratio；
   - repeated reverse toggles；
   - `min(h_RS)` stall；
   - local expansion anisotropy；
2. governor 不是直接产出 path，而是在 `baseline / APP / KFM / BCA` 等模式之间调度，或者动态调 aggressiveness；
3. 目标是识别“静态地图看不出来、但搜索过程已经暴露”的 trap regime。
与现有 `CX` 系列的差异：
1. 首次把 search process 本身作为学习对象；
2. 从“场值修正”转为“搜索制度切换”；
3. 不要求任何 dense map editing。
如何利用网络特性处理非完整约束：
1. 在线特征按 primitive family、heading bin、forward/reverse family 做聚合；
2. governor 关注的是“当前搜索是否陷入 Ackermann 特有的曲率 / reverse oscillation 模式”；
3. 可与 `CX8-A/B/D` 共享底层 primitive features。
理论抓手：
1. **Switched-anchor search**：若任一时刻 anchor queue 都保留，且 mode switch 只改变 secondary policy / local mask aggressiveness，则整体 completeness 仍由 anchor planner 承担；
2. **Bounded-regime switching**：将 governor 限制在有限模式集合中，切换只影响 search loss，不影响 baseline optimality contract；
3. 这是四个候选中最像“上层决策器”的路线，因此放在最后验证。
预期优势轴：
1. heterogeneous hard regimes 的鲁棒性；
2. 避免在局部 hard cases 上过度相信静态 prior；
3. 为后续更强方法型 venue 提供在线 decision-layer 叙事。

推荐执行顺序与原因：
1. **先做 `CX8-A / RS-APP`**：
   - 改动最直接、最贴近当前瓶颈；
   - 若单纯 primitive ordering 就能显著改善，则说明主要缺口确实在动作排序而非可行性判断。
2. **再做 `CX8-B / RS-KFM`**：
   - 与 `CX8-A` 共用 primitive-level 表达；
   - 若 `A` 只有轻微 gain，则应立即测试“局部 hard prune / soft mask”能否建立更硬的优势轴。
3. **第三做 `CX8-D / RS-BCA`**：
   - 它最具方法新意，也最可能在 `narrow_passage` / `flange` 这种需要多步 setup 的 case 上形成真正的 hard gain；
   - 但实现更复杂，应建立在 `A/B` 的 primitive feature substrate 之上。
4. **最后做 `CX8-C / RS-TDG`**：
   - 它是对 `A/B/D` 的在线调度层；
   - 若前面三个都没有形成明确 signal，再做 governor 才有意义。

本阶段结论：
1. `P0-CX` 的下一轮不应再继续增加 dense residual / opportunity / certificate map；
2. `CX8` 的核心创新窗口，是把 `RS` 根基创新与 `Hybrid A*` 的 successor decision layer 真正接起来；
3. 当前首选：`CX8-A / RS-APP`；
4. 当前最有“单独论道创新点”潜力的候选：`CX8-D / RS-BCA`；
5. 当前最可能建立硬优势轴的组合路线：
   - `RS` 负责 global geometric pull；
   - `CX3-D` 负责 conservative homotopy-safe fallback；
   - `CX8-A/B/D` 负责 primitive-level intervention；
   - `CX8-C` 仅在前三者有 signal 后再作为 online governor 叠加。

本轮实现结果（`2026-03-09`，当前为 focused strict pilot，而非 full-bundle exhaustive verdict）：
1. **工程/方法实现已完成**：
   - `planner/hybrid_astar.py` 已加入最小 successor-policy hook，使 `CX8` 可以在不破坏 anchor queue 的前提下对 primitive ordering / masking / bundle bias 做显式干预；
   - `rs_cx8/common.py` 已实现 `PrimitiveIndex`、`build_ego_patch`、运动学特征、轻量 MLP 训练/加载、带 policy 的 Hybrid A* 运行器；
   - 四个候选模块已分别实现于：`rs_cx8/cx8_a_app.py`、`rs_cx8/cx8_b_kfm.py`、`rs_cx8/cx8_d_bca.py`、`rs_cx8/cx8_c_tdg.py`；
   - 主实验与消融 runner 已实现于：`scripts/run_rs_p0cx8_main_trials_v1.py`、`scripts/run_rs_p0cx8_ablation_v1.py`。
2. **focused strict pilot 的数据口径**：
   - `calib_train`: `rs_root_hard_v2/dev/sample_000003.npz`（`parasol_misc`）
   - `calib_val`: `rs_root_hard_v2/dev/sample_000004.npz`（`parasol_misc`）
   - public final: `parasol_narrow/test/sample_000000.npz,sample_000001.npz`
   - hard supplement final: `rs_root_hard_v2/test/sample_000009.npz,sample_000010.npz`
   - 对应产物：`outputs/rs_p0cx8_focused_misc_v1/`、`reports/rs_p0cx8_main_trials_v1.md`、`outputs/rs_p0cx8_ablation_focused_misc_v1/`、`reports/rs_p0cx8_ablation_v1.md`。
3. **`CX8-A / RS-APP`**：
   - 在单个 `calib_val` misc case 上相对 accepted `CX3-D` 反而恶化 `-5` expansions；
   - 在 2 个 public misc test 上进一步恶化到 `-27` expansions；
   - 说明“仅用 primitive prior 做次级排序”在当前实现下不但不够强，还可能轻微打乱 accepted baseline 的有效局部搜索次序。
4. **`CX8-B / RS-KFM`**：
   - 在单个 `calib_val` misc case 上出现最强局部正信号：`+114` expansions；
   - 其 soft-only 消融也有近似 `+113`，说明有效部分主要来自 primitive-level risk pruning / penalty，而不是 hard mask 本身；
   - 但该增益没有迁移到 2 个 public misc test 或 2 个 hard-v2 misc supplement test（两处都回落到 `0`）；
   - 同时其运行时间代价极大，focused pilot 中相对 accepted `CX3-D` 增加了秒级搜索时间，说明当前每-successor 特征抽取/推理开销过高。
5. **`CX8-D / RS-BCA`**：
   - 在 focused misc pilot 中基本退化成近似 no-op；
   - 说明当前 bundle vocabulary / bottleneck detector 尚未命中真正需要 reverse-setup 的 regime。
6. **`CX8-C / RS-TDG`**：
   - 在当前 focused pilot 中未优于 delegated fixed branches；
   - 由于底层 `A/B/D` 只有 `KFM` 在单个 val case 上有局部信号，governor 本身暂未形成独立价值。
7. **汇总结论 / 当前判定**：
   - 目前没有任何 `CX8` 候选可以在 strict test 上替代 accepted `CX3-D` 主线；
   - 当前唯一值得继续保留的方法信号是：`CX8-B / RS-KFM` 的 primitive-level risk pruning 在单个 `calib_val` misc case 上出现了明确 expansions 改善；
   - 但它目前同时暴露出两个严重问题：
     - 一是 **泛化不足**（局部 val 信号未迁移到 public/hard misc test）；
     - 二是 **推理开销主导**（successor-level feature extraction 太重，时间轴严重恶化）；
   - 因而 `P0-CX8` 当前仍应保持 `IN_PROGRESS`，不能晋升 accepted 主线。
8. **若继续 `CX8`，下一步必须先解决的硬问题**：
   - 重新构造 `calib_train/calib_val`，确保不只覆盖 `parasol_misc`，而要包含至少一批 accepted `CX3-D` 能成功求解的 `narrow_passage / flange / bug_trap / maze` case；
   - 将 `CX8-B` 的每-successor 特征抽取做缓存/向量化，避免时间被 online feature computation 吞掉；
   - 在此之前，不应把当前 focused pilot 写成 full-bundle 的正结论。

本轮清障结果（`2026-03-09`，对应 `calib_hard_v1` + optimized hard pilot）：
1. **新的 hard-family calib split 已构建完成**：
   - 产物：`data/split/calib_hard_v1/manifest.json`、`data/split/calib_hard_v1/audit.md`、`data/split/calib_hard_v1/calib_train.csv`、`data/split/calib_hard_v1/calib_val.csv`；
   - 口径：严格只用 `rs_root_hard_v2/dev`，并以 accepted `RS + refined CX3-D / RS-HPG` 的**可解性筛选**来构建 calib；
   - 在 `cap=7000` 的 partial scan 下，`bug_trap` 已出现 `0/6` success，无法形成满足覆盖要求的 split，因此最终 `calib_hard_v1` 采用了 `cap=20000` 的 accepted-baseline-solvable 口径；
   - 最终 full dev scan（41 cases）得到 17 个 accepted-baseline-solvable case，并形成 `10` 个 `calib_train` + `7` 个 `calib_val`；
   - 覆盖：
     - required hard families 中，`narrow_passage / flange / maze / parasol_misc` 已覆盖；
     - `bug_trap` 即使在 `cap=20000` 下仍为 `0/6` success，因此被诚实记录为当前 success pool 的缺失 family；
     - 为达到训练规模，还额外纳入了 `alpha_puzzle / deadend_labyrinth` 的 accepted-solvable dev cases。
2. **`CX8-B / RS-KFM` 的运行时已做两轮优化**：
   - 第一轮：把 successor-level scoring 改成 **candidate batch ranking**，不再逐 successor 重复整套模型推理；
   - 第二轮：把 `KFM` 从 patch-heavy state-action feature 改成 **compact state-action feature**，并加上 cheap hard-state gating；
   - 关键代码落点：`planner/hybrid_astar.py`、`rs_cx8/common.py`、`rs_cx8/cx8_b_kfm.py`。
3. **优化后的 hard-family pilot 已完成**：
   - 产物：`outputs/rs_p0cx8_optimized_hard_pilot_v1/manifest.json`、`reports/rs_p0cx8_optimized_hard_pilot_v1.md`；
   - 口径：`calib_hard_v1` 上的 dev-only pilot，**不使用 test**；
   - 结果：
     - overall `success_delta_pp = 0.0`；
     - overall `exp_delta = -34.429`，未形成正向跨 family trend；
     - chosen trial 的 overall `mean_time_overhead_ratio = 0.7278`，相对 accepted `CX3-D` 仍约慢 `72.8%`；最低 overhead 的 trial 已降到 `0.2424`，但仍高于 `<30%` 目标，且其 expansions 更差；
     - family-wise 上只有 `flange` 保留局部正向 `exp_delta = +71.0`，而 `maze / narrow_passage / parasol_misc` 仍为负。
4. **当前判定**：
   - `calib_hard_v1` 构建成功，解决了“训练数据只覆盖 misc”的问题；
   - `CX8-B` 运行时开销已明显下降，但还**没有**压到可接受的上线级别；
   - 在新的 hard-family calib 上，`CX8-B` 仍未显示出可主张的正向跨 family 泛化；
   - 因而 `P0-CX8` 继续保持 `IN_PROGRESS`，当前不能进入下一轮 full strict test，也不能晋升 accepted 主线。
5. **若继续推进 `CX8-B`，下一步优先级**：
   - 进一步把 KFM 的 runtime 从当前 `~72.8%` overhead 压向 `<30%`；
   - 在不再牺牲 `maze / narrow_passage` 的前提下，保留或放大 `flange` 上出现的局部正信号；
   - 若做不到，则应诚实考虑 `CX8-B` 是否只是一条局部 family patch，而不是可支撑 `P0-CX` 的主候选。

后续分支验证结果（`2026-03-09`，基于 `calib_hard_v1` 的 dev-only pilot）：
1. **`CX8-A / RS-APP` 已验证**：
   - 产物：`outputs/rs_p0cx8_a_hard_pilot_v1/`、`reports/rs_p0cx8_a_hard_pilot_v1.md`；
   - overall `success_delta_pp = 0.0`，`exp_delta = -421.0`，`mean_time_overhead_ratio = 4.0350`；
   - family-wise 虽然 `flange` 有局部强正 `+1681`、`narrow_passage` 有极弱正 `+8.5`，但 `maze` 与 `parasol_misc` 大幅为负，整体 trend 明显失败；
   - 结论：**`CX8-A` 在新的 hard-family calib 上失败，不再作为主资源投入方向**。
2. **`CX8-D / RS-BCA` 已验证**：
   - 产物：`outputs/rs_p0cx8_d_hard_pilot_v1/`、`reports/rs_p0cx8_d_hard_pilot_v1.md`；
   - chosen trial 的 overall `success_delta_pp = 0.0`，`exp_delta = +989.714`，说明它是当前 `CX8` 里除 `KFM` 外首次在 hard-family calib 上出现**明显正向 expansions trend** 的 successor-level候选；
   - 但同时 `mean_time_overhead_ratio = 1.3283`，即平均约 `132.8%` 的额外时间开销，远高于 `<30%` 目标；
   - family-wise 上：
     - `flange`: `+1602.0` expansions；
     - `maze`: `+1776.0` expansions；
     - `narrow_passage`: `-0.5`（近零）；
     - `parasol_misc`: `-1.0`（近零）；
   - 结论：**`CX8-D` 是当前最值得继续保留的 `CX8` successor-level 分支，但其主要瓶颈已从“是否有信号”转成“如何把 runtime 压回可接受范围”**。
3. **当前 `CX8` 分支排序更新**：
   - `CX8-D`：当前 best surviving branch（有正向 expansions trend，但效率不达标）；
   - `CX8-B`：有局部方法信号，但在 hard-family calib 上整体仍负，且 runtime 仍偏高；
   - `CX8-A`：整体失败；
   - `CX8-C`：尚未在新的 hard-family calib 上重跑，因为在 `A/D` 尚未形成效率可接受的正向主候选前，继续验证 governor 的收益不高。
4. **当前 go / no-go 判断**：
   - 不进入 full strict test；
   - 不晋升新的 accepted 主线；
   - 若继续 `CX8`，下一轮主资源应转向 **`CX8-D` 的效率压缩 / lightweight bundle arbitration**，而不是再平均投入 `CX8-A/B/C`。

5. **`CX8-D` 轻量化冲刺结果（`2026-03-09`）**：
   - 产物：`outputs/rs_p0cx8_d_optimized_hard_pilot_v1/`、`reports/rs_p0cx8_d_optimized_hard_pilot_v1.md`；
   - 做法：
     - 把 `CX8-D` 的 state representation 从 patch-heavy 版本切到 compact bundle features；
     - 用更严格的 analytic trigger（`bottleneck_gate + activation_gate`）缩小 arbitration 激活范围；
     - 缓存 `PrimitiveIndex` 与标准化参数，避免在 search loop 中重复构造。
   - 结果：
     - optimized chosen trial 的 overall `exp_delta = 0.0`；
     - overall `mean_time_overhead_ratio = 0.1630`；
     - 相比上一轮重型 `CX8-D`（`exp_delta = +989.714`, `overhead = 1.3283`），说明轻量化显著压低了开销，但同时把原有正向 expansions 增益压没了。
   - 结论：**当前 `CX8-D` 已形成明确的 Pareto 冲突：重型版有明显正增益但太慢，轻量版接近达标但失去增益。**

6. **基于当前证据的最终读法**：
   - `CX8-A`：失败；
   - `CX8-B`：局部有信号，但 hard-family overall 仍负；
   - `CX8-D`：重型版有明显正向 expansions，但轻量版 `CX8-D-Lite-Reorder` 只能把 overhead 压到 `0.1630`，同时 `exp_delta` 退化到 `0.0`；
   - 这说明在当前算力/实现约束下，`successor-level bottleneck arbitration` 还无法同时满足“正向效果 + 可接受效率”；
   - 因而 **`P0-CX8` 现阶段应冻结为 `FAILED`，不再继续消耗主资源**。
7. **Failure Analysis（冻结原因）**：
   - 重型 `CX8-D` 的正向收益依赖于更强的 bundle arbitration 逻辑，而这部分正是主要开销来源；
   - 一旦把 arbitration 压缩到 cheap trigger + static reorder，运行时虽然明显下降，但增益会迅速塌缩到与 accepted `CX3-D` 持平；
   - 因而当前 evidence 更支持“这条路线存在真实方法信号，但在本项目当前 compute / implementation budget 下不可部署”，而不是“稍作微调即可过线”。
8. **后续建议**：
   - 不再继续扩 `CX8` 家族；
   - 若还要推进 `P0-CX`，应开启新的 `CX9` 级候选设计，而不是继续在 `CX8` 上做局部修补。

9. **`CX8-D Heavy` ceiling final eval（`2026-03-10`）**：
   - 产物：`outputs/rs_p0cx8_d_heavy_final_eval_v1/`、`reports/rs_p0cx8_d_heavy_final_eval_v1.md`；
   - 口径：锁定 `outputs/rs_p0cx8_d_hard_pilot_v1/chosen.json` 的原始重型版参数与模型，在 `rs_root_hard_v2/test` 上做一次性 retrospective final eval；
   - 相对 accepted `CX3-D` 的最终 hard-test 结果：
     - `success_delta_pp = 0.0`；
     - `exp_delta = +58.575`；
     - `mean_time_overhead_ratio = 1.2856`；
   - family-wise：
     - `maze`: `+338.545` expansions；
     - `deadend_labyrinth`: `+62.200` expansions；
     - `flange`: `-1.231`；
     - `narrow_passage`: `-4.154`；
     - `parasol_misc`: `0.0`；
   - 与 `CX9-A` locked final eval（`exp_delta = 0.0`）对比，说明**在不计成本时，语义干预的 test-side ceiling 仍然是正的**；
   - 但该 ceiling 需要 `~128.6%` 的额外时间开销，因此仍不具备成为 accepted 主线的资格。

#### P0-CX9：将有效语义干预上提到 region / cluster / episode 层（已完成 final eval，但未晋升主线）
状态：`COMPLETED（2026-03-10：CX9-A tuned 通过 dev gate，但 locked test final eval 未显示正向增益；CX9-D/B/C 均未通过）`
是否需要模型/方法修改：`是（但重点不再是 successor-level 微操，而是更高层次的低成本战略干预）`

触发原因：
1. `CX8-D` 重型版已经证明：**瓶颈识别 + 特定多步 maneuver** 的语义是有效的；
2. 但 `CX8-D` 轻量版与 `Lite-Reorder` 也证明：把这套语义直接放在 successor 层，会遇到“增益与效率不可兼得”的 Pareto 冲突；
3. 因而 `CX9` 的核心不再是“更快地做 successor arbitration”，而是：
   - 把 bundle 语义上提到 region-level / state-cluster-level / episode-level；
   - 把重推理移出搜索内环；
   - 让在线阶段退化成查表、少量窗口分析或一次性 scene-level program 执行。

调研产物：
1. 详细调研与候选论证见：`reports/rs_p0cx9_design_scout_v1.md`；
2. 当前 `P0-CX8` 的冻结原因与失败分析仍见本节上一部分；
3. `CX9` 的所有候选都必须默认建立在 accepted `RS + refined CX3-D / RS-HPG` 之上，而不是回退到 `Plain-Residual`。

问题重构：
1. 当前核心问题不应再表述为“如何让搜索更快”；
2. 更准确的表述是：**如何让搜索在关键瓶颈区域做出正确战略决策，且不承担高昂的实时推理成本**；
3. 从复杂度看，`CX8` 重型版近似是 `O(N_expand · |A| · C_phi)`，而 `CX9` 必须转向：
   - 一次性或稀疏的 `O(C_scene)` / `O(M · C_phi)` 推理；
   - 在线 `O(1)` 查表或极低成本条件判断。

第九轮设计原则：
1. 必须保留 `CX8-D` 已验证有效的核心语义：瓶颈识别、bundle 策略、reverse-setup；
2. 不允许再次回到 per-successor 深模型推理；
3. 在线阶段原则上只允许：
   - region lookup；
   - state-cluster mode lookup；
   - sparse bottleneck-window review；
   - 或一次性生成的条件子目标程序；
4. 任何 `CX9` 候选都必须保留 accepted anchor/fallback 语义；
5. 任何候选若在实现后重新退化成“每个节点都跑大模型”，应直接判定违背 `CX9` 设计前提。

冻结候选路线（下一轮按 `CX9-A -> CX9-D -> CX9-B -> CX9-C` 顺序执行）：

##### CX9-A：RS-SBM — Strategic Bundle Map
类型：`需要新增高层语义地图模块`
核心想法：
1. 对整张场景图做一次性战略分区；
2. 为每个区域绑定一个 bundle tag，如 `neutral / forward-thread-left / forward-thread-right / reverse-setup-left / reverse-setup-right`；
3. 在线搜索时节点只查询自己所在区域，再对对应 primitive family 加固定 bias。
如何继承 `CX8-D` 的成功语义：
1. 保留“瓶颈处需要特殊 maneuver family”这一语义；
2. 但把原本逐节点决定的 bundle arbitration，上提为 region-level semantic atlas。
理论抓手：
1. 一次性建图 `O(C_scene)`，在线查询 `O(1)`；
2. 将大量局部决策压缩为少量 region labels，符合信息瓶颈与分层决策视角。
预期优势轴：
1. 在保留 `CX8-D` 语义的前提下大幅压低 online overhead；
2. 最有希望同时覆盖 `flange / maze / narrow_passage`。
与已有工作的差异：
1. 相比 generic subgoal / abstraction 方法，我们不是学习通用 waypoint，而是学习**带 nonholonomic maneuver 语义的战略区域图**；
2. 相比 `CX8-D`，在线阶段不再进行 successor arbitration，而是纯 region lookup。

##### CX9-D：RS-BWR — Bottleneck Window Review
类型：`需要新增轨迹级稀疏复审模块`
核心想法：
1. 先运行 accepted `CX3-D` baseline 一次；
2. 只在少数被识别出的 bottleneck windows 上做 bundle-level semantic review；
3. 若窗口需要特殊 maneuver，再触发局部 replan 或局部 mode patch。
如何继承 `CX8-D` 的成功语义：
1. 保留 `CX8-D` 的 bundle reasoning；
2. 但把其执行位置从“每个 successor”改成“少数关键窗口”。
理论抓手：
1. 总额外代价变成 `O(M · C_phi)`，其中 `M << N_expand`；
2. 如果失败主要由少数瓶颈窗口主导，则 sparse review 更符合真实计算预算。
预期优势轴：
1. 最可能保留 `CX8-D` 重型版的正向 expansions 信号；
2. 也最接近当前现有框架，改造风险较低。
与已有工作的差异：
1. 不同于 seed/proposal 型两阶段方法，我们不是在搜索前给整条轨迹，而是在 baseline 之后只复审稀疏关键窗口；
2. 不同于 `CX8-D`，干预成本与 bottleneck window 数量相关，而不与全部扩展数线性绑定。

##### CX9-B：RS-CSP — Conditional Subgoal Program
类型：`需要新增一次性 scene-level 战略程序生成模块`
核心想法：
1. 给定地图、起终点，一次性输出短的 `(gate_i, maneuver_tag_i)` 程序；
2. 每个条目不是单纯 waypoint，而是“目标门 + 策略语义”；
3. 在线搜索只需依次完成若干段 baseline search。
如何继承 `CX8-D` 的成功语义：
1. 将 `reverse-setup` 这类多步 maneuver 升格为战略程序条目；
2. 保留 `CX8-D` 的瓶颈语义，但把它写成一次性长程决策。
理论抓手：
1. 把长 horizon 难题分解为少量阶段，额外推理成本与瓶颈数 `K` 成正比，而不是与 `N_expand` 成正比；
2. 子目标程序相当于把多步依赖从搜索内环移到 scene-level 规划前处理。
预期优势轴：
1. 最有希望修复 `narrow_passage` 这种长期依赖场景；
2. 方法论上也最有潜力写成独立的战略层创新点。
与已有工作的差异：
1. 不同于 generic subgoal methods，我们输出的是**带 maneuver semantics 的条件程序**；
2. 不同于 dense field correction，它显式表达多步策略而不是隐式改变局部 priority。

##### CX9-C：RS-CPF — Conditional Policy Field
类型：`需要新增条件策略场结构`
核心想法：
1. 不再学习标量 heuristic correction，而是学习粗粒度 `(x, y, yaw-cluster)` 上的离散 mode field；
2. 每个 coarse state 只存一个 mode，如 `neutral / thread-left / thread-right / reverse-setup-left / reverse-setup-right`；
3. 在线节点只查 coarse cell 的 mode，再用固定模板重排 primitive。
如何继承 `CX8-D` 的成功语义：
1. `CX8-D` 的 bundle semantics 仍然保留；
2. 但它们被存进“条件策略场”，而不是 successor classifier。
理论抓手：
1. 一次性生成 coarse policy field，在线查询近似 `O(1)`；
2. 这是条件策略而非值函数，本质是 piecewise-constant option policy。
预期优势轴：
1. 最优雅地把“field-like 低成本”与“bundle-like 战略语义”统一起来；
2. 若成功，最适合作为新的 paper-facing 主方法。
与已有工作的差异：
1. 不同于 `CX1-CX7` 的 scalar field，我们学习的是离散 maneuver mode field；
2. 不同于 `CX8-D`，在线阶段只做 mode lookup，不做 arbitration。

推荐执行顺序与原因：
1. **先做 `CX9-A / RS-SBM`**：最低风险、最低在线成本、最直接检验“语义上提”是否成立；
2. **再做 `CX9-D / RS-BWR`**：最接近当前 `CX8-D` 的正向信号，且仍是低 online cost；
3. **第三做 `CX9-B / RS-CSP`**：若 `A/D` 不足，再尝试更强的 scene-level 战略程序；
4. **最后做 `CX9-C / RS-CPF`**：最有潜力，但也是设计和验证成本最高的统一方案。

说明：`mean_time_overhead_ratio < 0.30` 是基于 `CX9-A` initial 版本（`exp_delta = +746.571`, `overhead ≈ 0.3325`）作出的 strategic adjustment；其目的不是放弃效率，而是避免为了追求过严的 `<0.10` 阈值再次破坏已验证有效的语义信号。

最低验收标准：
1. 在 `calib_hard_v1` 的 dev-only pilot 上，必须同时满足：
   - `exp_delta > 0`；
   - `success_delta_pp >= 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - 无明显 path audit 恶化；
2. 若某候选仍依赖 per-successor 深模型推理，直接判定违背 `CX9` 设计前提。

失败判据：
1. 在线阶段仍需要每个节点/每个 successor 调模型；
2. `exp_delta <= 0`；
3. `mean_time_overhead_ratio >= 0.30` 且无法解释为一次性 scene-level 前处理；
4. 仅在单一 family 上出现 patch 式正项而整体 trend 仍负。

本阶段结论：
1. `CX9` 的核心不是继续更快地做 successor-level arbitration，而是**把 `CX8-D` 的有效语义提升为更高层次的低成本战略策略对象**；
2. 当前首选：`CX9-A / RS-SBM`；
3. 当前最接近 `CX8-D` 成功经验、最值得保留的方法分支：`CX9-D / RS-BWR`；
4. 当前最有统一方法潜力的长线候选：`CX9-C / RS-CPF`。

本轮实现结果（`2026-03-09`，`CX9` 首轮 dev-only pilots）：
1. **通用产物**：
   - 汇总：`reports/rs_p0cx9_round1_summary.md`；
   - 单分支报告：`reports/rs_p0cx9_a_pilot_v1.md`、`reports/rs_p0cx9_d_pilot_v1.md`、`reports/rs_p0cx9_b_pilot_v1.md`、`reports/rs_p0cx9_c_pilot_v1.md`；
   - 输出目录：`outputs/rs_p0cx9_a_pilot_v1/`、`outputs/rs_p0cx9_d_pilot_v1/`、`outputs/rs_p0cx9_b_pilot_v1/`、`outputs/rs_p0cx9_c_pilot_v1/`。
2. **`CX9-A / RS-SBM`**：
   - overall `success_delta_pp = 0.0`，`exp_delta = +746.571`，`mean_time_overhead_ratio = 0.3325`；
   - 这是当前 `CX9` 中唯一在整体上给出明确正向 expansions trend 的分支；
   - 但运行时仍远高于 `<0.30` 门槛，且 `parasol_misc` 仍保留明显负项；
   - 结论：**当前 best surviving branch，但尚不能进入下一阶段严格验证。**
3. **`CX9-D / RS-BWR`**：
   - overall `success_delta_pp = 0.0`，`exp_delta = -2.143`，`mean_time_overhead_ratio = 0.3381`；
   - sparse bottleneck-window review 的 online 形式更轻，但语义信号强度不够，整体未转正；
   - 结论：**当前实现未证明该路线优于 accepted baseline。**
4. **`CX9-B / RS-CSP`**：
   - overall `success_delta_pp = 0.0`，`exp_delta = -602.429`，`mean_time_overhead_ratio = 0.4930`；
   - gate program 目前同时损害了 search effort 与效率；
   - 结论：**首轮失败，应冻结为负结果证据。**
5. **`CX9-C / RS-CPF`**：
   - overall `success_delta_pp = 0.0`，`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.8335`；
   - dense conditional policy field 退化为与 accepted baseline 持平的效果，同时 precompute 成本过高；
   - 结论：**首轮失败，应冻结为负结果证据。**
6. **当前排序与判断**：
   - `CX9-A`：当前 best branch；
   - `CX9-D`：次优，但整体仍未转正；
   - `CX9-C`：效果为零且开销高；
   - `CX9-B`：明显负结果；
   - 在首轮 pilot 后，`CX9-A tuned` 已满足 `exp_delta > 0` 与 `mean_time_overhead_ratio < 0.30`，因此可以进入下一阶段更严格的统计验证。
7. **协议推进边界**：
   - 本轮 `CX9` 仅完成了 `calib_hard_v1` 的 dev-only pilot；
   - 由于没有候选通过 dev gate，当前**尚未**推进到 `mp/csm/parasol_narrow` 的下一阶段对比，也没有消费任何 test 证据。
8. **下一步建议**：
   - 若继续推进 `P0-CX9`，主资源应只保留给 `CX9-A / RS-SBM`；
   - 下一轮需要专门解决 `CX9-A` 的 scene-level precompute 开销与 `parasol_misc` 负项，而不是继续平均投入 `B/C/D`。

9. **`CX9-A` Efficiency & Stability Sprint（`2026-03-10`）**：
   - 第一版 tuned 尝试（`reports/rs_p0cx9_a_optimized_pilot_v1.md`）虽然把 overhead 压到 `<0.30`，但整体 `exp_delta` 退化为负；
   - 第二版 tuned 尝试（当前主结果，见 `reports/rs_p0cx9_a_tuned_pilot_v1.md`）采用“coarse atlas + 定向 misc 保护”的温和调参：
     - 保留初始 `CX9-A` 的 coarse semantic atlas；
     - 通过 `misc_margin + misc_misc_thr + misc_open_thr + misc_bridge_thr` 只对 `parasol_misc` 风格场景做 conservative abstain；
     - 通过 `apply_conf_threshold + local_score_threshold` 在低置信区域回退到 neutral；
     - 不再激进压缩语义表达，只做温和门控微调。
   - tuned 结果：
     - overall `success_delta_pp = 0.0`；
     - overall `exp_delta = +814.714`；
     - overall `mean_time_overhead_ratio = -0.0019`（满足 `<0.30`）；
     - `parasol_misc exp_delta = 0.0`（不再退化）；
   - 结论：**`CX9-A` 现已同时满足放宽后的效率门槛、正向效果门槛与稳定性门槛。**

10. **`CX9-A` locked final eval（`2026-03-10`）**：
   - 产物：`outputs/rs_p0cx9_a_final_eval_v1/`、`reports/rs_p0cx9_a_final_eval_v1.md`、`paper/tables_rs_root_v1/table_rs_cx9a_final_eval_v1.csv`；
   - 口径：
     - 参数严格锁定自 `outputs/rs_p0cx9_a_tuned_pilot_v1/chosen.json`；
     - `rs_root_hard_v2/test` 只做一次性最终评估；
     - 同时评估 `CX9-A (Full)` 与 `CX9-A (No-Stability)`，不再做任何调参。
   - 结果：
     - hard-test 上 `CX9-A (Full)` 相对 accepted `CX3-D` 的 `exp_delta = 0.0`；
     - `success_delta_pp = 0.0`；
     - `mean_time_overhead_ratio = -0.0052`，效率良好；
     - `No-Stability` 与 `Full` 结果几乎完全一致，说明 dev 上的稳定性保护在 locked test 上没有再提供可见额外收益；
     - ordinary support 上，`CX9-A` 对 `mp/csm` 与 `CX3-D` **按构造完全一致**（`build_standard_field` 直接返回 accepted field），因此不存在普通场景额外退化。
11. **`P0-CX9` 的最终判定**：
   - `CX9-A`：通过了 tuned dev gate，但在 locked test 上未保持正向 `exp_delta`；
   - `CX9-D`：整体仍为负；
   - `CX9-B`：明显负结果；
   - `CX9-C`：效果归零且开销高；
   - 因而 **`CX9-A` 不晋升 accepted 主线，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。**
12. **当前主读法**：
   - `CX9-A` 证明了“语义上提”在 dev 上确实可行；
   - 但 locked test 说明这条路线在更广泛 hard benchmark 上尚未建立稳健的净增益；
   - 因而当前更合理的定位是：`CX9-A` 是一个值得记录的方法学正信号，但还不是足以替代 `CX3-D` 的稳定主线。
13. **后续建议**：
   - 不再以 `CX9-A` 为 accepted-promotion 候选；
   - 若继续推进 `P0-CX`，需要新的 `CX10` 级方案，而不是继续围绕 `CX9-A` 反复局部调参；
   - 当前可投稿的最诚实主叙事仍应围绕 `RS` 根基创新与 `CX3-D` 的保守 refinement，而把 `CX9-A` 作为后续探索信号。

#### P0-CX10：将高复杂度语义编译为低成本执行结构（已冻结为失败路线）
状态：`FAILED（2026-03-11：CX10-A/B/C/D 首轮失败后，CX10-D-Selective 定向挽救仍未通过 public exp4 gate；本路线正式冻结）`
是否需要模型/方法修改：`是（允许新增 compiled semantic layer，但禁止回到 per-successor 深模型推理）`

目标：
在保留 accepted `RS + refined CX3-D / RS-HPG` 安全边界的前提下，把 `CX8-D Heavy` 已验证有效的 bottleneck semantics 编译成低成本执行结构，尝试首次打破“语义有效性 vs 运行时成本”的 Pareto 死锁。

为什么需要 `CX10`：
1. `CX8-D Heavy` 的 retrospective final eval（`reports/rs_p0cx8_d_heavy_final_eval_v1.md`）说明：
   - test-side `exp_delta = +58.575`，语义干预 ceiling 仍然为正；
   - 但 `mean_time_overhead_ratio = 1.2856`，约等于 `+128.56%` 额外开销，不可部署；
   - 增益主要集中在 `maze`，说明 teacher signal 真实但分布窄。
2. `CX9-A` tuned 与 locked final eval（`reports/rs_p0cx9_a_tuned_pilot_v1.md`、`reports/rs_p0cx9_a_final_eval_v1.md`）说明：
   - region-level semantic lifting 可以把开销压到近零；
   - 但 tuned dev 上的强正信号没有在 locked test 上泛化，说明“粗图谱式语义上提”不足以稳定保真 `CX8-D` 的多步语义。
3. 因而 `CX10` 不应再问“如何学一个更强 field / atlas”，而应问：
   - 如何把 `bottleneck detection + reverse-setup + thread-through + phase persistence` 编译成 `rulebook / script / automaton / sketch` 这类低成本执行结构；
   - 在线只允许 `O(1)` lookup、稀疏窗口检查或一次性 scene-level 编译，严禁 `O(N_expand · |A| · C_phi)` 级别的 successor-time 重推理。

`CX10` 的统一设计约束：
1. 所有 `CX10-*` 候选默认都建立在 accepted `RS + refined CX3-D / RS-HPG` 之上；
2. **严禁**重新引入 per-successor 深模型前向或复杂 arbitration 网络；
3. 干预对象必须是“可执行的语义结构”，如：
   - shallow rulebook；
   - sparse bottleneck script；
   - finite-state controller；
   - maneuver sketch；
   而不是新的 dense scalar field / coarse atlas；
4. 必须默认 `neutral / abstain-by-default`，只有高置信且落在支持域内才激活 bundle bias；
5. 必须保留 anchor fallback 语义，任何时候都能无缝回退 accepted baseline；
6. 必须能在当前 `rs_cx` 模块 + planner hook 架构下落地，不允许为了验证候选而重写 planner 主干。

冻结候选路线（按 `CX10-A -> CX10-B -> CX10-C -> CX10-D` 顺序执行）：

##### CX10-A：RS-CEC — Counterfactual Experience Compilation
类型：`teacher-distilled sparse rulebook / prototype retrieval`
核心想法：
1. 用 `CX8-D Heavy` 作为离线 teacher，采集真正带来 counterfactual search gain 的 bottleneck states；
2. 只保留廉价解析几何特征（如 clearance、corridor asymmetry、reverse pocket、heading misalignment、local RS gradient）；
3. 把 teacher 的 bundle arbitration 编译成少量 `prototype + shallow rule`，在线仅做常数级特征计算和 lookup。
如何继承 `CX8-D` 的成功语义：
1. 保留的是 `bottleneck predicate -> preferred bundle tag -> primitive-family bias` 这一映射；
2. 丢弃的是重型版黑箱网络与 per-successor 前向。
理论抓手：
1. 这是 partial-policy compilation，而不是 full policy replacement；
2. 在线复杂度可压到 `O(F + D)`，其中 `F` 为廉价特征数、`D` 为规则深度/检索常数。
预期优势轴：
1. 最直接压制 `CX8-D Heavy` 的 runtime 瓶颈；
2. 比 `CX9-A` 更有希望跨 scene 泛化，因为表征依赖稳定几何谓词而不是 region atlas。
与已有工作的差异：
1. 相关工作：`Programmatic Reinforcement Learning without Oracles`、`POETREE`；
2. 我们的创新点：只编译 accepted baseline 之上的**稀疏语义增量**，并用 counterfactual gain 而非 imitation fidelity 过滤 teacher 样本。

##### CX10-B：RS-HBC — Horizon Bottleneck Compiler
类型：`model-based scene-level bottleneck script compiler`
核心想法：
1. 在搜索开始前，用 accepted `CX3-D` field + `RS` 运动学做少量 horizon-limited probe；
2. 只回答 `哪里是 gate`、`进入前是否需要 reverse-setup`、`通过时应采用哪类 thread mode`；
3. 把结果编译成极短的 scene-specific script，在线只做窗口命中检查与静态 bias。
如何继承 `CX8-D` 的成功语义：
1. 把 `reverse-setup -> thread-through -> recover` 从 per-successor arbitration 提升为 window-level phase script；
2. 保留多步语义，丢弃海量重复计算。
理论抓手：
1. “只预测关键变量”的抽象模型思路；
2. 额外代价近似 `O(K · L · |B|)`，其中 `K` 是 bottleneck window 数、`L` 是短 horizon probe 长度、`|B|` 是少量 bundle family。
预期优势轴：
1. 比全图 atlas 更稳，因为只在稀疏窗口上工作；
2. 对 `maze / flange` 这类由少量关键 gate 决定整体难度的 family 更有潜力。
与已有工作的差异：
1. 相关工作：`Learning Efficient Abstract Planning Models that Choose What to Predict`、`Subgoal Diffuser`；
2. 我们的创新点：输出的是**带 maneuver semantics 的 bottleneck script**，并引入 analytic probe/verifier，而不是 generic waypoint 或 latent subgoal。

##### CX10-C：RS-NFA — Neuro-Finite Automaton
类型：`compiled finite-state intervention controller`
核心想法：
1. 用一个很小的自动机表示 planner-side intervention phase，例如：`neutral / prepare_reverse / commit_thread / recover`；
2. 状态转移只依赖解析谓词，如 `is_bottleneck`、`has_reverse_pocket`、`entered_gate`、`heading_recovered`；
3. 每个状态绑定固定 primitive-family bias 模板，在线以 `O(1)` 代价维护 phase persistence。
如何继承 `CX8-D` 的成功语义：
1. `CX8-D Heavy` 最难保留的是多步时序一致性；
2. `RS-NFA` 直接把 setup/commit/recover 的时序依赖显式建模为状态机。
理论抓手：
1. 有限状态压缩可视为对 intervention memory 的强信息瓶颈；
2. 在线只需谓词评估、状态转移与模板 lookup。
预期优势轴：
1. 若 `CX8-D Heavy` 的收益主要来自 phase persistence，`RS-NFA` 是最可能保住这部分语义的低成本结构；
2. 有望比静态 rulebook 更稳地覆盖 `maze / narrow_passage`。
与已有工作的差异：
1. 相关工作：`Hierarchical Programmatic Reinforcement Learning`、`Provably Correct Compositional Policies via Automata Embeddings`；
2. 我们的创新点：自动机不是任务级 policy controller，而是 accepted planner 之上的 **bottleneck-phase semantic controller**。

##### CX10-D：RS-LAS — Learned Action Sketch
类型：`one-shot maneuver sketch / sparse macro-event generator`
核心想法：
1. 在搜索前一次性输出极短的 maneuver sketch，例如 2-5 个事件：`(gate token, macro tag, confidence)`；
2. sketch 事件不是精细轨迹，而是“在哪里先 reverse-setup、再 thread-through”的宏观提示；
3. 在线搜索仍由 accepted `CX3-D` 主导，只在接近 gate 时启用对应 macro bias，验证失败则 abstain。
如何继承 `CX8-D` 的成功语义：
1. 把 `CX8-D Heavy` 的少量关键 phase-switch event 压缩成 scene-level macro program；
2. 若 sketch 正确，可在几乎不增加在线成本的前提下保留强语义。
理论抓手：
1. 额外成本与 sketch 长度 `K` 成正比，而非与扩展节点数成正比；
2. 属于 option/program sketch 的 planner 版本。
预期优势轴：
1. 对需要显式先后顺序的 `narrow_passage` 类 case 有潜力；
2. 若 token 设计为相对几何事件而非绝对坐标，可提升跨 scene 泛化。
与已有工作的差异：
1. 相关工作：`Combined Task and Motion Planning via Sketch Decompositions`、`PIVOT-R`；
2. 我们的创新点：输出的是 **nonholonomic maneuver sketch**，不是 task skeleton 或 waypoint list，且始终带 verifier + fallback。

推荐执行顺序与原因：
1. **先做 `CX10-A / RS-CEC`**：
   - 最直接利用 `CX8-D Heavy` 的已验证正信号；
   - 改动最小、在线成本最低、最适合作为“compiled semantics 是否可行”的第一发验证。
2. **再做 `CX10-B / RS-HBC`**：
   - 若 `RS-CEC` 出现 teacher overfit，`RS-HBC` 提供更强的 analytic generalization 对照；
   - 也是最贴近“只预测关键变量”这一文献共识的路线。
3. **第三做 `CX10-C / RS-NFA`**：
   - 若静态 rule/script 不足以保住时序语义，再引入极小状态机去恢复 phase persistence；
   - 方法创新强，但 trace mining 与状态设计更复杂。
4. **最后做 `CX10-D / RS-LAS`**：
   - 上限高，但 data pipeline、tokenization、verifier 都更重；
   - 应作为高风险高回报的最后候选，而不是首选。

最低验收标准：
1. 在 `calib_hard_v1` 的 dev-only pilot 上，必须同时满足：
   - `exp_delta > 0`；
   - `success_delta_pp >= 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - `parasol_misc` 不出现明显负向回归，或能被 `neutral-abstain` 机制清晰解释；
   - 无 path audit 恶化；
   - 无 per-successor 深模型推理。
2. 通过 dev gate 后，在 `rs_root_hard_v2/test` 的 locked final eval 上，必须：
   - 锁定结构与参数，不再调参；
   - 相对 accepted `CX3-D` 维持 `exp_delta > 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - `mp/csm` ordinary support 不发生原则性退化。

失败判据：
1. 重新引入 per-successor 深模型/重仲裁；
2. 本质上退化为新的 dense field / coarse atlas，而不是编译式执行结构；
3. 无法提供 `neutral-by-default` 与 support-aware abstain；
4. gain 只存在于个别 `maze` case，而整体 trend 仍不稳；
5. 需要重写 planner 主干才可运行。

本阶段结论：
1. `CX8-D Heavy` 已证明：语义干预 ceiling 为正，但在线 per-successor 执行不可接受；
2. `CX9-A` 已证明：单纯把语义做成 coarse atlas 不能稳定泛化；
3. 因而 `CX10` 的核心命题应冻结为：**compile semantics, not scores**；
4. 当前首选执行入口：`CX10-A / RS-CEC`；
5. 当前最有机会修复泛化问题的 analytic companion：`CX10-B / RS-HBC`；
6. 当前最有机会保住 `CX8-D` 时序语义的结构化升级：`CX10-C / RS-NFA`；
7. 当前最高风险、最高上限的储备路线：`CX10-D / RS-LAS`。

本轮实现结果（`2026-03-10`，对应产物：`reports/rs_p0cx10_a_pilot_v1.md`、`reports/rs_p0cx10_b_pilot_v1.md`、`reports/rs_p0cx10_c_pilot_v1.md`、`reports/rs_p0cx10_d_pilot_v1.md`、`reports/rs_p0cx10_round1_summary.md`、`reports/rs_p0cx10_standard_audit_v1.md`）：
1. **统一协议**：
   - 参数选择仅使用 `data/split/calib_hard_v1`；
   - public 评估使用 `data/benchmark/parasol_narrow/test` 的 `exp3/exp4` 固定预算口径；
   - `mp/csm` 仅做 ordinary-support field-equality audit，确认所有 `CX10-*` 的 standard field 与 accepted `CX3-D` **按构造完全一致**；
   - 由于四条路线都没有先在 public parasol 上过线，本轮**没有进一步消费 `rs_root_hard_v2/test`** 证据，避免无意义扩大 test 开销。
2. **`CX10-A / RS-CEC`**：
   - 产物：`outputs/rs_p0cx10_a_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.446955`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 1.188354`；
   - 读法：compiled rulebook 基本退化为与 accepted `CX3-D` 持平，但仍付出显著 runtime，说明“teacher-distilled local rulebook”没有成功保留重型 teacher 的有效语义。
3. **`CX10-B / RS-HBC`**：
   - 产物：`outputs/rs_p0cx10_b_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = -0.131064`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.331174`；
   - `exp3` 上比 accepted `CX3-D` 略快，但 public overall 仍是 tie；
   - 读法：scene-level bottleneck script 是当前 **least-bad branch**，但它仍然没有把 `CX8-D Heavy` 的语义 ceiling 重新变成净增益，且 `exp4` 开销仍高于 `<0.30`。
4. **`CX10-C / RS-NFA`**：
   - 产物：`outputs/rs_p0cx10_c_pilot_v1/`；
   - `calib_val`：`exp_delta = -343.857`，`mean_time_overhead_ratio = 0.508193`；
   - public `exp4`：`exp_delta = -9.500`，`mean_time_overhead_ratio = 1.180549`；
   - `No-Phase` ablation 会把公共集表现拉回接近 accepted baseline，说明当前自动机时序逻辑本身在拖累搜索；
   - 读法：phase persistence 的结构化显式建模在当前规则设计下**没有复现 `CX8-D Heavy` 的收益，反而引入了额外误干预**。
5. **`CX10-D / RS-LAS`**：
   - 产物：`outputs/rs_p0cx10_d_pilot_v1/`；
   - `calib_val`：`exp_delta = -20.143`，`mean_time_overhead_ratio = -0.112479`；
   - public `exp4`：`exp_delta = -123.111`，`mean_time_overhead_ratio = 0.386410`；
   - family-wise 上 `narrow_passage` 保留了 `+98.75` 的局部正项，但被 `flange` 的 `-522.8` 明显负项抵消；
   - `No-Template` ablation 退化为与 accepted `CX3-D` 持平，说明 scene-template 确实在“动”，但当前动法不稳。
6. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx10_standard_audit_v1.md` 显示四个 `CX10-*` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而可以确认：本轮 negative result 不是靠牺牲 ordinary-support 伪造出来，而是 public parasol 主战场上确实没有建立新的净增益。
7. **排序与 go / no-go**：
   - 当前排序：`CX10-B`（least-bad tie） > `CX10-A`（tie 但太慢） > `CX10-C`（明显负） > `CX10-D`（局部 family 正项但 overall 负）；
   - 四条路线都**没有**同时满足 `exp_delta > 0` 与 `mean_time_overhead_ratio < 0.30`；
   - 因而 `P0-CX10` 首轮应判定为 **未通过 go/no-go**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。
8. **方法学结论**：
   - `compile semantics, not scores` 这一方向并非完全无信息：`CX10-B` 与 `CX10-D` 都说明“编译式结构”至少可以在不牺牲 ordinary-support 的前提下控制干预范围；
   - 但本轮 evidence 同样表明：**仅靠 shallow rulebook / sparse script / finite-state controller / short sketch，还不足以稳定复现 `CX8-D Heavy` 的正向 semantic ceiling**；
   - 若继续推进，下一轮应更明确地区分：
     - 是 teacher signal 本身过窄、难以编译；
     - 还是当前 compiler / verifier / support gate 设计仍过弱。

9. **`CX10-D-Selective` 定向挽救结果（`2026-03-11`）**：
   - 产物：`outputs/rs_p0cx10_d_selective_pilot_v1/`、`reports/rs_p0cx10_d_selective_pilot_v1.md`；
   - 做法：
     - 锁定 `outputs/rs_p0cx10_d_pilot_v1/chosen.json` 的 sketch 参数，不再改动 sketch generator；
     - 新增 `Family-Aware Abstention Guard`，仅学习 scene-level `apply sketch / defer to CX3-D` binary decision；
     - guard 训练只使用 dev 数据：base sketch 仍建立在 `calib_hard_v1` 选出的 locked params 上，guard classifier 使用 `rs_root_hard_v2/dev` 的 dev-only contexts 扩充 family coverage，并在 `calib_hard_v1/calib_val` 上锁定阈值；
     - ordinary support 继续强制 `build_standard_field == accepted CX3-D`。
   - 结果：
     - `calib_val`：`exp_delta = -0.429`，`mean_time_overhead_ratio = -0.022280`；
     - public `exp4`：`exp_delta = -145.222`，`mean_time_overhead_ratio = 0.149726`；
     - family-wise：
       - `flange`: `exp_delta = -522.8`（仍显著为负，未修复）；
       - `narrow_passage`: `exp_delta = 0.0`（原本 `+98.75` 的局部正项未保住）；
     - `mp/csm` field audit：`max_abs_field_diff = 0.0`，说明本轮失败并非来自 ordinary-support 口径失真。
   - 结论：**`CX10-D-Selective` 只成功压低了 runtime，但没有学会可靠地 defer；它既没修复 `flange`，也没保住 `narrow_passage`，因此不能作为 Pareto deadlock 的突破口。**
10. **`P0-CX10` 的最终判定**：
   - `CX10-A / RS-CEC`：持平但太慢；
   - `CX10-B / RS-HBC`：least-bad tie，但 `exp4` overhead 仍高于 `<0.30` 且无净增益；
   - `CX10-C / RS-NFA`：明显负结果；
   - `CX10-D / RS-LAS` 与 `CX10-D-Selective`：局部存在 sketch signal，但无法在 public parasol 上同时满足“overall 正增益 + flange 不退化 + runtime 合格”；
   - 因而 **`P0-CX10` 应正式冻结为 `FAILED`**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。
11. **失败机理总结**：
   - `CX10` 证明了“compile semantics”本身不够，真正缺的是 **instance/token-level defer reliability**；
   - scene-level family proxy 太粗，无法阻止 `flange` 这类 high-risk false positive；
   - 这意味着下一轮若还围绕 sketch 路线推进，主对象必须从“生成更强 sketch”改为“验证 sketch token 是否值得执行”。

#### P0-CX11：面向鲁棒 sketch token 与 calibrated deferral 的下一轮设计（已冻结为失败路线）
状态：`FAILED（2026-03-11：CX11-B/C/A 首轮实现与 public parasol + mp/csm audit 已完成；三条路线均退化为 over-defer tie，未通过 public gate）`
是否需要模型/方法修改：`是（允许新增 defer / verifier / robust token layer，但仍禁止 per-successor 深模型推理）`

目标：
针对 `CX10-D-Selective` 暴露出的根本问题——“不能可靠知道何时不该用 sketch”——设计新一轮 `CX11` 候选，把主学习对象从 sketch content 转向 **robust token validity + calibrated abstention / defer**。

设计动机：
1. `CX10-D` 的局部正项说明 sketch semantics 仍有潜力；
2. 但 `CX10-D-Selective` 说明，仅靠 shallow family proxy 还不够，错误 sketch 仍会在 `flange` 上造成灾难；
3. 因而下一轮必须更直接地学习：
   - 当前 token 是否落在支持域内；
   - 当前 instance 是否应 defer 给 accepted baseline；
   - 当前 proposal 是否通过 cheap counterfactual verifier。

调研产物：
1. 详细设计与参考文献见：`reports/rs_p0cx11_design_scout_v1.md`；
2. 当前冻结的候选顺序为：`CX11-B -> CX11-C -> CX11-A`。

冻结候选路线：

##### CX11-B：RS-LDS — Learning-to-Defer Sketcher
类型：`instance-specific defer controller`
核心想法：
1. 不再先学 sketch，而是先学“当前是否值得把控制权交给 sketch expert”；
2. experts 至少包括：`accepted CX3-D`、`CX10-D sketch`，必要时再加入 conservative token subset；
3. defer head 使用 calibrated / conformal-style threshold，只在支持域足够强时启用 sketch。
如何继承 `CX8-D` / `CX10-D` 的成功语义：
1. sketch 分支仍保留现有多步语义；
2. 但主学习对象变成 **何时必须 defer**，而不是“总想把 sketch 用出去”。
理论抓手：
1. learning-to-defer；
2. calibrated abstention；
3. 在线只需 `O(1)` defer score + branch select。
预期优势轴：
1. 最直接修复 `CX10-D-Selective` 的误触发；
2. 最低风险、最贴近当前代码骨架。

##### CX11-C：RS-CSV — Counterfactual Sketch Verifier
类型：`proposal-verifier architecture`
核心想法：
1. 继续保留当前 sketch generator 作为 proposal；
2. 新增 token-level verifier，检查 setup pocket、corridor handedness、exit visibility、local anchor progress 等 cheap predicates；
3. proposal 与 verifier 同时为正才真正注入 sketch bias，否则立即 abstain。
如何继承成功语义：
1. proposal 仍来源于现有 sketch / bundle 语义；
2. verifier 负责把 `CX8-D Heavy` 中隐含的 counterfactual validity 显式化。
理论抓手：
1. proposal-verifier 分解；
2. 在线复杂度仍是 `O(K)` token checks。
预期优势轴：
1. 比纯 family guard 更贴近真实失败机理；
2. 有望在不扩大 runtime 的前提下修复 `flange` 误伤。

##### CX11-A：RS-RST — Robust Sketch Tokenization
类型：`typed sketch token redesign`
核心想法：
1. 将当前 sketch mode 改写成带约束的 typed token，如 `pre_reverse(right, pocket>=τ, heading_gap>=τ)`、`thread(right, corridor_band=[a,b])`；
2. 每个 token 自带一组 cheap validity predicates；
3. 任一 predicate 不满足则 token 不执行。
如何继承成功语义：
1. 保留 `reverse-setup -> thread-through` 的核心结构；
2. 但把其载体从“裸 mode”升级为“token + verifier”。
理论抓手：
1. specification-constrained planning hint；
2. 在线成本与 token 数 `K` 成正比。
预期优势轴：
1. 最有希望在结构层面彻底解决 sketch 误伤；
2. 但 token schema 设计成本最高，因此放在 `B/C` 之后。

最低验收标准：
1. public `exp4` 上必须同时满足：
   - `exp_delta > 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - `flange exp_delta >= 0`；
2. `mp/csm` ordinary-support 不得劣化；
3. 默认 `abstain-by-default`；
4. 严禁 per-successor 深模型推理回潮。

失败判据：
1. 仍然主要依赖粗糙 family proxy，而不是 token validity / defer reliability；
2. `flange` 继续出现明显负项；
3. public `exp4` 仍无法转正；
4. 为了过线而偷偷重新引入 expensive online reasoning。

本阶段结论：
1. `CX10` 的最终失败说明：**compile semantics 还不够，必须 verify or defer every sketch token**；
2. 下一轮首选执行入口：`CX11-B / RS-LDS`；
3. 当前最有希望从机制上修复 `flange` 误伤的路线：`CX11-C / RS-CSV`；
4. 当前最高创新、也最重的结构化重构路线：`CX11-A / RS-RST`。

本轮实现结果（`2026-03-11`，对应产物：`reports/rs_p0cx11_b_pilot_v1.md`、`reports/rs_p0cx11_c_pilot_v1.md`、`reports/rs_p0cx11_a_pilot_v1.md`、`reports/rs_p0cx11_round1_summary.md`、`reports/rs_p0cx11_standard_audit_v1.md`）：
1. **统一协议**：
   - base sketch 严格锁定自 `outputs/rs_p0cx10_d_pilot_v1/chosen.json`；
   - 新增的 `CX11-*` 层只在 dev 数据上训练：`calib_hard_v1` 负责 base sketch refit 与阈值选择，`rs_root_hard_v2/dev` 去掉 `calib_val` 后作为额外 dev train；
   - public 仅使用 `data/benchmark/parasol_narrow/test` 的 `exp3/exp4` 固定预算口径做 post-lock 评估；
   - `mp/csm` 继续只做 ordinary-support field-equality audit，严禁把 public/test evidence 反灌回训练。
2. **`CX11-B / RS-LDS`**：
   - 产物：`outputs/rs_p0cx11_b_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.014645`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.013676`，`flange exp_delta = 0.0`；
   - 读法：learning-to-defer 成功消除了 `CX10-D` 的 `flange` 负项，但同时把 `narrow_passage` 的正项也全部 defer 掉了，整体退化为与 accepted `CX3-D` 持平。
3. **`CX11-C / RS-CSV`**：
   - 产物：`outputs/rs_p0cx11_c_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = -0.037368`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = -0.035979`，`flange exp_delta = 0.0`；
   - 读法：counterfactual sketch verifier 比 `CX10-D` 更保守，runtime 甚至略优于 accepted baseline，但 gain 也被 verifier 一并抹平，说明当前 token-level verifier 仍然过于 conservative。
4. **`CX11-A / RS-RST`**：
   - 产物：`outputs/rs_p0cx11_a_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = -0.050230`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = -0.046181`，`flange exp_delta = 0.0`；
   - 读法：typed token redesign 也退化成“强 abstain 层”，没有把 sketch token 的正向结构重新激活出来。
5. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx11_standard_audit_v1.md` 显示 `CX11-B/C/A` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而本轮失败并非来自 ordinary-support 口径漂移，而是 public parasol 上确实没有新的净增益。
6. **排序与 go / no-go**：
   - 三个候选在 public `exp4` 上全部满足 `flange exp_delta = 0.0` 且 overhead 很低；
   - 但三者的 `exp_delta` 都只是 `0.0`，没有任何一个转正；
   - 当前排序可按保守性读作：`CX11-A` ≈ `CX11-C` ≈ `CX11-B`，它们本质上都学成了不同形式的 over-defer / over-abstain。
7. **最终判定**：
   - `CX11` 的三条候选都说明：当前 sketch/defer family 可以“消害”，但还**不能保益**；
   - 因而 **`P0-CX11` 应冻结为 `FAILED`**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。
8. **方法学结论**：
   - `CX10` 的失败是“误触发太多”；
   - `CX11` 的失败则是“为避免误触发而过度 defer，导致全部正向 semantic signal 一起消失”；
   - 这说明当前 sketch-based intervention family 已经把 trade-off 暴露得很充分：
     - 不 defer：`flange` 崩；
     - 强 defer：整体 tie baseline；
   - 因而若还要继续推进 `P0-CX`，需要新的 `CX12` 级方向，而不是继续在当前 sketch/defer family 上做局部修补。

#### P0-CX12：基于 Flange failure analysis 的下一轮设计（已冻结为失败路线）
状态：`FAILED（2026-03-11：CX12-A/C/B 首轮实现与 public parasol + mp/csm audit 已完成；三条路线均只做到“消害不保益”，未通过 public gate）`
是否需要模型/方法修改：`是（允许新增几何 trap / exit 特征、signed sketch adjustment 或 search-state gate，但仍禁止 per-successor 深模型推理）`

目标：
针对 `CX10-D` / `CX11` 暴露出的核心问题——`flange` catastrophic false positive 与 `narrow_passage` sparse positive signal 在当前特征空间中几乎不可分——重新定义一轮 `CX12` 候选，使 sketch 决策真正建立在 **trap / exit / search-state** 证据上，而不是继续依赖饱和的 family proxy。

诊断产物：
1. 详细 failure analysis 见：`reports/rs_p0cx12_design_scout_v1.md`；
2. 辅助特征表见：`outputs/rs_p0cx12_design_scout_v1/`；
3. 诊断口径：
   - `calib_hard_v1` 只包含 `1` 个 `flange` 与 `2` 个 `narrow_passage`，不足以做 top-5 对照；
   - 因而本轮用 locked `CX10-D` 在 public `parasol_narrow/test` 上的 `exp4` 输出补充 failure analysis，但**不用于调参**。

核心诊断结论：
1. 当前 `CX10/CX11` 使用的主特征在 `flange` 与 `narrow_passage` 上高度重叠：
   - `clearance`、`corridor_width`、`heading_to_goal_cos`、`bottleneck` 基本饱和重合；
   - `scene_hard / scene_misc / scene_bridge` 的 overlap 也非常高；
2. 最糟 `flange` case 与最优 `narrow_passage` case 都会呈现：
   - `top_gate_score = 1.0`；
   - 相同 handedness token；
   - 相近的局部几何统计；
   这说明当前特征只能识别“像 bottleneck”，却不能识别“是真出口还是 flange trap”；
3. 因而下一轮必须显式补入：
   - `local trap detection`；
   - `exit visibility / exit reachability`；
   - `search-state stall evidence`。

冻结候选路线（按 `CX12-A -> CX12-C -> CX12-B` 顺序执行）：

##### CX12-A：RS-GHF — Geometry-Aware Hard Filter
类型：`explicit geometric predicate filter`
核心想法：
1. 为 sketch activation 设计显式几何谓词：
   - `exit_visibility >= τ_exit`；
   - `goal_ray_clearance >= τ_goal`；
   - `trap_score <= τ_trap`；
   - `pocket_to_exit_ratio <= τ_ratio`；
2. 只有全部通过时才允许激活 sketch。
如何继承成功语义：
1. 不改变现有 positive sketch branch；
2. 只给它加一道针对 flange trap 的 hard geometric veto。
理论抓手：
1. hard safety filter；
2. 在线复杂度为少量 `O(K · C_geom)` 谓词检查。
预期优势轴：
1. 最直接修复 catastrophic flange false positive；
2. 比 `CX11` 的 learned defer 更不容易退化为全局 over-defer。

##### CX12-C：RS-SSG — Search-State Gating
类型：`search-state conditional activation`
核心想法：
1. sketch activation 不再只看静态几何，而是同时看 planner dynamics；
2. 仅当 open-list entropy 降低、accepted successor ratio 下滑、anchor progress stall 等指标同时出现时才激活 sketch。
如何继承成功语义：
1. 仍保留原有 sketch token；
2. 但将触发时机推迟到“搜索确实进入局部困境”的阶段。
理论抓手：
1. `state × search-dynamics` gating；
2. 在线只需 cheap counters，不需要新模型前向。
预期优势轴：
1. 有机会保住 `narrow_passage` 的 setup 价值；
2. 同时避免 `flange` 在早期阶段被误判为真 bottleneck。

##### CX12-B：RS-CSA — Contrastive Sketch Adjustment
类型：`signed sketch adjustment`
核心想法：
1. 放弃“要么全用，要么全不用”的二元门控；
2. 在 flange-like states 上引入 negative sketch，显式抑制有害 token；
3. 在 positive narrow states 上继续保留正向 sketch。
如何继承成功语义：
1. `narrow_passage` 的正向 token 仍保留；
2. `flange` 则通过负向 sketch 做局部修正，而不是直接全局 abstain。
理论抓手：
1. signed intervention；
2. 避免 `CX11` 那种“消害也消益”的 tie-by-deferral。
预期优势轴：
1. 最有机会真正打破当前二元门控造成的 Pareto 僵局；
2. 但设计和验证成本最高，因此放在后序。

最低验收标准：
1. public `exp4` 上必须同时满足：
   - `exp_delta > 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - `flange exp_delta >= 0`；
2. `mp/csm` ordinary-support 不得劣化；
3. 严禁再次回到 per-successor 深模型推理。

失败判据：
1. 新增路线仍只依赖当前饱和特征，不引入 trap / exit / search-state 新证据；
2. `flange` 继续出现 catastrophic negative cases；
3. 通过手段只是再次把所有正负信号一起抹平成 tie。

本阶段结论：
1. `CX12` 的核心不是“再做一个更强 defer head”，而是 **给 sketch gate 补上正确的证据**；
2. 当前首选执行入口：`CX12-A / RS-GHF`；
3. 当前最有机会保住正向 signal 的中风险路线：`CX12-C / RS-SSG`；
4. 当前最高创新、最高复杂度的 signed route：`CX12-B / RS-CSA`。

本轮实现结果（`2026-03-11`，对应产物：`reports/rs_p0cx12_a_pilot_v1.md`、`reports/rs_p0cx12_c_pilot_v1.md`、`reports/rs_p0cx12_b_pilot_v1.md`、`reports/rs_p0cx12_round1_summary.md`、`reports/rs_p0cx12_standard_audit_v1.md`）：
1. **统一协议**：
   - base sketch 严格锁定自 `outputs/rs_p0cx10_d_pilot_v1/chosen.json`；
   - `CX12-*` 的新层只使用 dev 数据训练与选型：`calib_hard_v1` 负责 base refit 与 trial selection，`rs_root_hard_v2/dev` 去掉 `calib_val` 后作为额外 dev train；
   - public 仅使用 `parasol_narrow/test` 的 `exp3/exp4` 固定预算口径做 post-lock 评估；
   - `mp/csm` 继续只做 ordinary-support field-equality audit，防止协议漂移。
2. **`CX12-A / RS-GHF`**：
   - 产物：`outputs/rs_p0cx12_a_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = -0.021065`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = -0.008594`，`flange exp_delta = 0.0`；
   - `No-Hard-Filter` ablation 恢复为旧 `CX10-D` 式负项（overall `-123.111`、`flange -522.8`），说明几何硬过滤确实在“工作”；
   - 但它同时把 `narrow_passage +98.75` 的正项一起滤掉，整体退化为与 accepted `CX3-D` 持平。
3. **`CX12-C / RS-SSG`**：
   - 产物：`outputs/rs_p0cx12_c_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = -0.015912`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.000538`，`flange exp_delta = 0.0`；
   - `No-State-Gate` 与 `Full` 几乎完全一致，说明当前 search-state evidence 没有提供额外区分力；
   - 读法：search-state gating 也学成了近乎纯 abstain。
4. **`CX12-B / RS-CSA`**：
   - 产物：`outputs/rs_p0cx12_b_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = -0.007387`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.006195`，`flange exp_delta = 0.0`；
   - `Positive-Only` 与 `Full` 同样近乎一致，说明 negative sketch branch 没有形成能与 positive branch 互补的有效 signed adjustment；
   - 读法：contrastive sketch adjustment 仍然没有跳出“消害=消益”的困境。
5. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx12_standard_audit_v1.md` 显示 `CX12-A/C/B` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而本轮 failure 并非来自 ordinary-support 口径漂移，而是 public parasol 上确实没有净增益。
6. **排序与 go / no-go**：
   - 三条路线都成功把 `flange exp_delta` 从 `-522.8` 修到 `0.0`；
   - 但三条路线的 public `exp4 exp_delta` 全部只有 `0.0`，没有任何一路转正；
   - 当前排序只能按“最少引入额外开销”读作：`CX12-A` > `CX12-C` > `CX12-B`，但三者本质上都只是更强的 gate / abstain 变体。
7. **最终判定**：
   - `CX12` 证明“trap-aware evidence”足以把 `flange` 负项清空；
   - 但同时也再次证明：**当前 positive sketch signal 过于稀疏，只要 gate 稍强一点就会被一起抹平**；
   - 因而 **`P0-CX12` 应冻结为 `FAILED`**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。
8. **方法学结论**：
   - `CX10` 的失败是“误触发太多”；
   - `CX11` 的失败是“为避免误触发而过度 defer”；
   - `CX12` 的失败则进一步表明：即使补入 trap-aware evidence，当前 sketch family 仍然只有“消害”能力，没有“保益”能力；
   - 因而若继续推进 `P0-CX`，需要新的 `CX13` 级方向，而不是继续围绕当前 sketch-repair family 做局部修补。

#### P0-CX13：从 semantic repair 转向 computation allocation / contract design（已冻结为失败路线）
状态：`FAILED（2026-03-11：CX13-A/B/C 首轮实现与 public parasol + mp/csm audit 已完成；三条 computation-allocation 路线均未通过 public gate）`
是否需要模型/方法修改：`是（允许新增 basin budget / schedule / topology contract 层，但仍禁止 per-successor 深模型推理）`

目标：
在彻底脱离 `CX8-D semantic intervention -> CX10/11/12 sketch/defer/repair` 路线族的前提下，寻找一种新的、可部署的 `RS-grounded` 方案，使搜索计算本身成为可分配、可约束、可调度的对象，从而打破当前“强语义不可部署、低成本修复必然失效”的 Pareto 死锁。

为什么需要 `CX13`：
1. `CX8-D Heavy` 证明：hard test 上的 semantic ceiling 仍为正（`exp_delta = +58.575`），但 runtime `+128.56%` 不可部署；
2. `CX10` 说明：单靠 compiled rule/script/sketch，容易重新触发 `flange` 式 catastrophic false positive；
3. `CX11` 说明：defer/verifier 路线能消害，但会把 sparse positive signal 一起 defer 掉；
4. `CX12` 说明：即使补入 trap-aware geometry，当前 sketch family 仍然只能“消害不保益”；
因此 `CX13` 的核心问题必须重写为：
1. 不再问“何时该激活 semantic token”；
2. 而要问：**如何把搜索预算本身分配到真正值得探索的结构对象上**；
3. 即把干预对象从 `token validity` 转向：
   - basin-level budget；
   - episode-level search schedule；
   - topology-level contract。

调研产物：
1. 详细调研与候选冻结见：`reports/rs_p0cx13_design_scout_v1.md`；
2. 该报告同时总结了当前路线族的结构性局限：现有工作大多优化 heuristic / policy / sketch，而没有把 **computation allocation itself** 当作主对象。

冻结候选路线（按 `CX13-A -> CX13-B -> CX13-C` 顺序执行）：

##### CX13-A：RS-BBC — Basin Budget Controller
类型：`basin-level search budget control`
核心想法：
1. 基于 accepted `RS + CX3-D` field、occupancy 与 skeleton，把自由空间分成少量 basin：corridor / trap pocket / transition；
2. 为每个 basin 分配 exploration budget；
3. 搜索中节点只需查自己所在 basin 的 remaining budget，并据此调整 priority penalty / reverse allowance / budget spend。
如何继承当前主线：
1. planner 与 accepted field 保持不变；
2. 新增的只是一个 basin-level ledger，而不是新的 heuristic predictor。
理论抓手：
1. metareasoning / resource-rational search；
2. topology-aware budget allocation；
3. 在线复杂度 `O(1)` basin lookup + counter update。
预期优势轴：
1. 最直接针对 `flange` catastrophic expansion waste；
2. 不依赖 fragile token validity，最有希望打破当前 Pareto 死锁。
创新性：
1. 不是 sketch/defer repair；
2. 不是 planner portfolio；
3. 而是把 **trap basin budget** 作为主对象。

##### CX13-B：RS-IAS — Instance-Adaptive Search Schedule
类型：`episode-level search schedule selection`
核心想法：
1. 为每个 instance 从小型 discrete catalog 中选择一套 search schedule；
2. schedule 可以控制：
   - heuristic inflation；
   - reverse quota；
   - restart threshold；
   - phase-wise anchor/main priority mixing；
3. 在线只做一次性 catalog lookup，必要时在固定 phase 点切换。
如何继承当前主线：
1. 仍使用 accepted `RS + CX3-D` planner；
2. 不改变 heuristic object，只改变 episode-level search rhythm。
理论抓手：
1. per-instance algorithm configuration；
2. cost-aware meta planning；
3. online complexity `O(1)`。
预期优势轴：
1. 若当前失败本质上是 fixed schedule mismatch，这条路线比 token repair 更稳定；
2. 可在不新增 heavy inference 的前提下带来跨 family gain。
创新性：
1. 不做 semantic token gating；
2. 不做外部 planner routing；
3. 而是把 **搜索节奏** 当成可学习对象。

##### CX13-C：RS-TCB — Topological Contract Budgeting
类型：`topology-level search contract`
核心想法：
1. 从 accepted field 与 skeleton 中提取少量 topological corridor tickets；
2. 为每个 ticket 建立 contract：reserve budget、reverse quota、exit requirement、overrun penalty；
3. 搜索节点只需绑定到某个 ticket，再按 contract 更新 priority slack 与 budget ledger。
如何继承当前主线：
1. 仍在 accepted planner 内工作；
2. 不依赖 sketch/waypoint，而是依赖 topology ticket。
理论抓手：
1. topological abstraction + budget contract；
2. 在线 `O(1)` ticket lookup + contract update。
预期优势轴：
1. 直接控制“哪个 corridor 值得花预算”，而不是控制局部 token；
2. 比 current sketch family 更适合作为 paper-facing 新方向。
创新性：
1. 不等同于 topology waypoint planning；
2. 也不等同于 router/portfolio；
3. 它的对象是 **corridor-level search contract**。

最低验收标准：
1. public `exp4` 上必须同时满足：
   - `exp_delta > 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - `flange exp_delta >= 0`；
2. `mp/csm` ordinary-support 不得劣化；
3. 在线逻辑必须是 `O(1)` 或 `O(K)`，且 `K` 不与 successor 数量线性耦合；
4. 严禁重新落回 sketch/defer/repair family。

失败判据：
1. 新方案本质上又变成 semantic token activation / defer repair；
2. 仍依赖 per-successor 推理；
3. 只能“消害”但依旧无法把 public `exp4` 转正；
4. 为了表达力而引入不可部署的 online metaplanner。

本阶段结论：
1. `CX13` 的核心不是“再做一个更聪明的 gate”，而是 **把搜索计算分配本身变成干预对象**；
2. 当前首选执行入口：`CX13-A / RS-BBC`；
3. 当前最稳的 backup：`CX13-B / RS-IAS`；
4. 当前最具方法学新意的长线候选：`CX13-C / RS-TCB`。

本轮实现结果（`2026-03-11`，对应产物：`reports/rs_p0cx13_a_pilot_v1.md`、`reports/rs_p0cx13_b_pilot_v1.md`、`reports/rs_p0cx13_c_pilot_v1.md`、`reports/rs_p0cx13_round1_summary.md`、`reports/rs_p0cx13_standard_audit_v1.md`）：
1. **统一协议**：
   - 不再依赖任何 sketch / defer / repair object；
   - 所有 `CX13-*` 都直接建立在 accepted `RS + refined CX3-D / RS-HPG` 上；
   - 新增对象只允许是：
     - basin budget；
     - instance-level search schedule；
     - topology contract；
   - public 仅使用 `parasol_narrow/test` 的 `exp3/exp4` 固定预算口径做 post-lock 评估；
   - `mp/csm` 继续只做 ordinary-support field-equality audit。
2. **`CX13-A / RS-BBC`**：
   - 产物：`outputs/rs_p0cx13_a_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.291722`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.915084`，`flange exp_delta = 0.0`；
   - `No-Budget` ablation 同样是 public tie，但 overhead 仍高，说明 basin budget control 在当前实现下只增加了 bookkeeping / policy cost，没有换来 search-effort 改善。
3. **`CX13-B / RS-IAS`**：
   - 产物：`outputs/rs_p0cx13_b_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.283617`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.909466`，`flange exp_delta = 0.0`；
   - `Always-Balanced` 与 `Full` 结果几乎一致，说明 instance-adaptive schedule 选择没有学到真正有区分力的 schedule object，更多是在重放 accepted search 的不同参数化。
4. **`CX13-C / RS-TCB`**：
   - 产物：`outputs/rs_p0cx13_c_pilot_v1/`；
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.062417`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.565540`，`flange exp_delta = 0.0`；
   - 相对 `A/B`，topological contract 的开销较低，但仍明显高于 `<0.30` 且没有带来任何正向 `exp_delta`。
5. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx13_standard_audit_v1.md` 显示 `CX13-A/B/C` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而本轮 failure 不是口径漂移，而是 public parasol 上真实的 “零增益 + 额外成本”。
6. **排序与 go / no-go**：
   - 三条路线都把 `flange exp_delta` 保持在 `0.0`；
   - 但三条路线的 public `exp4 exp_delta` 也都只有 `0.0`；
   - 同时 runtime 明显高于 accepted baseline：`C` 最低也仍约 `+55.6%`，`A/B` 接近 `+90%`；
   - 当前排序可按“最少新增负担”读作：`CX13-C` > `CX13-B` > `CX13-A`。
7. **最终判定**：
   - `CX13` 表明：即使把干预对象提升到 computation allocation / schedule / contract 层，当前实现仍然只得到 baseline tie，没有建立新的优势区间；
   - 因而 **`P0-CX13` 应冻结为 `FAILED`**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。
8. **方法学结论**：
   - `CX10-CX12` 的主要问题是 semantic token family 的 distinguishability crisis；
   - `CX13` 则说明：单独改变“搜索资源分配对象”也不足以打开新的 gain regime；
   - 当前更合理的读法是：`P0-CX` 需要新的 `CX14` 级方向，而不是继续在现有 semantic repair 或 computation-allocation family 上加局部修补。

#### P0-CX14：从静态配置与语义修补转向 episode-local search memory（首轮已完成，当前 best surviving branch 为 CX14-B）
状态：`IN_PROGRESS（2026-03-12：CX14-A/B/C 首轮实现与 public parasol + mp/csm audit 已完成；首次出现 post-CX8 的小幅正向 public signal，但 runtime 仍远未达标）`
是否需要模型/方法修改：`是（允许新增 episode-local memory / online sparse rewrite / queue discipline 层，但仍禁止 per-successor 深模型推理）`

目标：
在不回到 `semantic repair` 或 `static computation allocation` 两大家族的前提下，寻找一种新的 `RS-grounded` 方案，使 accepted `RS + refined CX3-D / RS-HPG` 在同一搜索 episode 内能够廉价地积累“哪里已经反复失败、哪里仍值得探索”的证据，从而建立新的优势区间。

为什么需要 `CX14`：
1. `CX10-CX12` 说明：semantic token / sketch / defer family 会稳定掉进 “误触发 vs 过度抑制” 的双重陷阱；
2. `CX13` 说明：只改变 basin budget / schedule / topology contract 这类静态 allocation object，也只能得到 baseline tie；
3. 因而 `CX14` 必须让搜索获得一种新的能力：
   - 不是更强的离线语义判别；
   - 也不是更强的静态 budget contract；
   - 而是 **episode-local search memory / heuristic plasticity**。

调研产物：
1. 详细调研与候选冻结见：`reports/rs_p0cx14_design_scout_v1.md`；
2. 该报告的主结论是：下一轮最值得押注的对象不是 token validity，而是 **cheap reusable search memory**。

冻结候选路线（按 `CX14-A -> CX14-B -> CX14-C` 顺序执行）：

##### CX14-A：RS-NSG — Novelty Signature Guidance
类型：`episode-local signature novelty memory`
核心想法：
1. 为节点构建极廉价的 nonholonomic local signature（clearance / distance / heading / trap / corridor / yaw bins）；
2. 搜索中维护 signature memory：重复出现且无 progress 的 signature 逐步受罚，新颖 signature 得到轻微 bonus；
3. 干预对象是 **repeated-failure local pattern**，不是 semantic token。
理论抓手：
1. width-based / novelty-aware search；
2. online memory compression；
3. 在线 `O(1)` lookup + counter update。
预期优势轴：
1. 直接压制“反复掉进相似 trap 局部模式”的 expansions 浪费；
2. 不依赖 fragile local semantics，最适合作为新 family 的第一发验证。

##### CX14-B：RS-LHU — Local Heuristic Update
类型：`search-time sparse heuristic rewrite`
核心想法：
1. accepted field 作为初始值保持不变；
2. 如果某类 local signature 在本 episode 中持续表现出低 progress / 低 accepted successor ratio / 重复展开，就对该 signature 写入一个小的 online penalty；
3. 这是 episode-local 的 sparse heuristic rewrite，而不是新的 offline residual field。
理论抓手：
1. online learning / no-regret style heuristic adaptation；
2. sparse local value correction；
3. 在线 `O(1)` signature lookup + table update。
预期优势轴：
1. 比 `CX1-CX7` 更动态；
2. 比 `CX10-CX12` 更少依赖 semantic token discrimination；
3. 有机会在不大幅增成本的前提下纠正 trap-like optimism。

##### CX14-C：RS-MHQ — Multi-Head Queueing
类型：`queue discipline adaptation`
核心想法：
1. 为节点同时维护 progress / novelty / escape 三类 cheap head；
2. planner 在 node pop 时按 phase 在多头之间切换，而不是永远只用单一 queue discipline；
3. 干预对象是 **谁先被展开**，不是 heuristic token 或 contract。
理论抓手：
1. multi-queue best-first search；
2. phase-based compute triage；
3. 在线 `O(1)` phase dispatch。
预期优势轴：
1. 如果 accepted 主线的问题在于 queue discipline 过早塌缩到错误 basin，这条路线最有希望修复；
2. 也是当前三者中最具方法学新意的一条。

最低验收标准：
1. public `exp4` 上必须同时满足：
   - `exp_delta > 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - `flange exp_delta >= 0`；
2. `mp/csm` ordinary-support 不得劣化；
3. 在线逻辑必须保持 `O(1)` 或 `O(K)`；
4. 严禁回到 sketch/defer/repair family 或静态 allocation family。

失败判据：
1. 新方案仍本质上只是更换一个 gate / token / schedule 名字，但没有 episode-local evidence accumulation；
2. 只会“消害”而不能让 public `exp4` 转正；
3. 为了表达力重新引入 heavy online inference。

本阶段结论：
1. `CX14` 的核心不是“更强的 token 分类”或“更强的 static budget”，而是 **让搜索廉价地记住它刚刚学到的局部失败模式**；
2. 当前首选执行入口：`CX14-A / RS-NSG`；
3. 当前最稳的 backup：`CX14-B / RS-LHU`；
4. 当前最具方法学新意的长线候选：`CX14-C / RS-MHQ`。

本轮实现结果（`2026-03-12`，对应产物：`reports/rs_p0cx14_a_pilot_v1.md`、`reports/rs_p0cx14_b_pilot_v1.md`、`reports/rs_p0cx14_c_pilot_v1.md`、`reports/rs_p0cx14_round1_summary.md`、`reports/rs_p0cx14_standard_audit_v1.md`）：
1. **统一协议**：
   - 所有 `CX14-*` 都建立在 accepted `RS + refined CX3-D / RS-HPG` 上；
   - 本轮只新增 episode-local search memory / online sparse rewrite / queue discipline 层；
   - public 仅使用 `parasol_narrow/test` 的 `exp3/exp4` 固定预算口径做 post-lock 评估；
   - `mp/csm` 继续只做 ordinary-support field-equality audit；
   - 本轮**没有消费 `rs_root_hard_v2/test`** 证据。
2. **`CX14-A / RS-NSG`**：
   - 产物：`outputs/rs_p0cx14_a_pilot_v1/`；
   - `calib_val`：`exp_delta = +6.571`，`mean_time_overhead_ratio = 1.606644`；
   - public `exp4`：`exp_delta = +0.389`，`mean_time_overhead_ratio = 1.709200`，`flange exp_delta = +0.6`；
   - `No-Novelty` ablation 退化为 public `exp_delta = 0.0`，说明 novelty memory 的确在产生方法信号；
   - 但 runtime 开销极高，当前不能作为 deployable candidate。
3. **`CX14-B / RS-LHU`**：
   - 产物：`outputs/rs_p0cx14_b_pilot_v1/`；
   - `calib_val`：`exp_delta = +7.0`，`mean_time_overhead_ratio = 1.471205`；
   - public `exp4`：`exp_delta = +0.444`，`mean_time_overhead_ratio = 1.582221`，`flange exp_delta = +1.0`；
   - `No-Update` ablation 退化为 public `exp_delta = 0.0`，说明 online local heuristic update 是本轮 strongest surviving signal；
   - 结论：**当前 best surviving branch，但 runtime 仍远未达标。**
4. **`CX14-C / RS-MHQ`**：
   - 产物：`outputs/rs_p0cx14_c_pilot_v1/`；
   - `calib_val`：`exp_delta = +6.571`，`mean_time_overhead_ratio = 1.749977`；
   - public `exp4`：`exp_delta = +0.389`，`mean_time_overhead_ratio = 1.854265`，`flange exp_delta = +0.6`；
   - `Static-Mix` 与 `Full` 基本一致，说明当前 multi-head queueing 的 phase switch 贡献有限；
   - 结论：存在方法信号，但没有超过 `CX14-B`，且开销更高。
5. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx14_standard_audit_v1.md` 显示 `CX14-A/B/C` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而本轮 positive signal 不是靠 ordinary-support 口径漂移伪造出来的。
6. **排序与 go / no-go**：
   - 当前排序：`CX14-B` > `CX14-A` > `CX14-C`；
   - 三条路线都首次在 public `exp4` 上给出小幅正向 `exp_delta`，且 `flange` 不再退化；
   - 但三条路线的 runtime 全部远超 `<0.30` 门槛（约 `+158%` 到 `+185%`），因此当前**不能**进入 accepted-promotion。
7. **当前主读法**：
   - `CX14` 是 `CX8` 之后第一个在新的 family 下重新出现 public 正向 signal 的方向；
   - 当前主要瓶颈已经非常清楚：**不是“有没有信号”，而是“如何把 episode-local memory 的在线维护成本压回可接受范围”。**
8. **round1 后的下一步建议（已执行）**：
   - 不冻结 `CX14`；  
   - 先专门做 `CX14-B / RS-LHU` 的 runtime 压缩与 caching / vectorization，而不是再平均投入三条分支；
   - accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`，直到有候选同时满足 `exp_delta > 0` 与 `mean_time_overhead_ratio < 0.30`。

9. **`CX14-B` Runtime Compression Sprint（`2026-03-12`）**：
   - 产物：`scripts/run_rs_p0cx14_b_runtime_sprint_v1.py`、`reports/rs_p0cx14_b_runtime_sprint_v1.md`、`outputs/rs_p0cx14_b_runtime_sprint_v1/`；
   - 核心改动：
     - 在 `planner/hybrid_astar.py` 中去掉“凡是实现 `rank_successors` 就强制走 `_simulate_detailed`”的隐性重开销路径，只对显式声明 `requires_sim_stats=True` 的策略保留 detailed sim；
     - 在 `rs_cx14/cx14_b_lhu.py` 中把 `RS-LHU` 改成 **event-triggered / lazy materialization**：
       - 只在 `stall / low accepted ratio / repeated-failure` 时激活局部重排；
       - 默认不写 penalty table；
       - 使用 coarse signature bucket cache 减少在线维护成本。
   - 锁定 protocol：
     - 仍只在 `calib_hard_v1` 上做 trial selection；
     - public 只消费 `parasol_narrow/test` 的 `exp3/exp4`；
     - `mp/csm` 继续只做 ordinary-support field-equality audit；
     - 只有当 public gate 通过时才允许升级到 `rs_root_hard_v2/test`，本轮未触发该升级。
   - 结果（见 `reports/rs_p0cx14_b_runtime_sprint_v1.md`）：
     - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.286833`；
     - public `exp3`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.281385`；
     - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.282318`；
     - `flange exp_delta = 0.0`，`narrow_passage exp_delta = 0.0`；
     - `No-Update` 与 `Always-Active` ablation 同样都退化为 `exp_delta = 0.0`，说明本轮压缩后已经没有可保留的正向方法信号。
   - 结论：
     - runtime 压缩本身是成功的：`CX14-B` 首次把 overhead 从 round1 的 `~+158%` 压到 `< +30%`；
     - 但它也把 round1 的弱正 public signal 一并压平，最终退化为与 accepted `CX3-D` 的 public tie；
     - 因而 **`CX14-B` runtime sprint 未通过 go / no-go**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。

#### P0-CX15：围绕局部可恢复性 + 事件触发微审查 + 可复用失败记忆的新方向（已冻结为失败路线）
状态：`FAILED（2026-03-12：CX15-A/B/C/D 首轮实现与 public parasol + mp/csm audit 已完成；四条 recoverability/trigger/memory 路线均未通过 public gate）`
是否需要模型/方法修改：`是（允许新增 recoverability cache / trigger layer / reusable failure memory，但仍禁止 per-successor 深模型常驻推理）`

目标：
在不回到 `dense field repair`、`sketch/defer/repair`、`static allocation` 三类已证伪家族的前提下，为 accepted `RS + refined CX3-D / RS-HPG` 设计一轮新的 `RS-grounded` 方案，使搜索只在真正需要时消费少量额外计算，并且这点额外计算围绕：

1. **局部可恢复性（recoverability / exitability）**；
2. **事件触发微审查（event-triggered micro-review）**；
3. **可复用失败记忆（failure / escape memory）**；

来建立新的优势区间。

为什么需要 `CX15`：
1. `CX8-D Heavy` 已证明强语义 ceiling 为正，但 successor-level 常驻执行不可部署；
2. `CX10-CX12` 已证明 semantic token / sketch / defer family 的结构性问题是：
   - 不 defer：`flange` 式误触发代价灾难性；
   - 强 defer：正向 signal 一起被抹平；
3. `CX13` 已证明 static budget / schedule / contract 只会重排算力，不会自动产生 leverage；
4. `CX14` 已证明 episode-local memory 是对的对象，但 runtime sprint 进一步说明：
   - 若 memory 只表达“重复失败”，而不表达“是否仍可恢复”，
   - 在把 overhead 压到 `<0.30` 后会稳定退化为 public tie。

调研产物：
1. 详细文献调研与候选冻结见：`reports/rs_p0cx15_design_scout_v1.md`；
2. 该报告的主结论是：下一轮最值得押注的对象不是更强 token，而是 **recoverability-aware, event-triggered, memory-backed sparse review**。

调研主结论（从文献到本项目的映射）：
1. **Recoverability / fail-safe / reachability**（RSS 2019/2020/2023）说明：
   - 真正有价值的对象不是“当前像不像 bottleneck”，而是“当前是否仍有低成本 escape / reverse-setup continuation”；
2. **Event-triggered replanning / lazy search / choose-what-to-predict**（ICAPS 2019, ICRA 2024, NeurIPS 2023, CoRL 2023）说明：
   - 高开销 computation 不应常驻，而应由少数异常事件触发；
3. **Experience reuse / failure memory / narrow-corridor experience**（RSS 2012, ICRA 2015, RSS 2024）说明：
   - narrow / repetitive geometry 中，复用 experience 是成立的；
   - 但对当前项目，更值得存的不是成功整条轨迹，而是 **失败入口 + 逃逸短前缀**；
4. **Dead-end / depression avoidance**（JAIR 2012, AAAI 2018）说明：
   - 搜索真正的浪费来自 local depression / dead end；
   - 有效机制不是更大模型，而是发现、记住并推回 border。

统一设计约束：
1. 所有 `CX15-*` 都建立在 accepted `RS + refined CX3-D / RS-HPG` 上；
2. 严禁回到 per-successor 深模型常驻推理；
3. 额外 computation 只能由 event trigger 触发，而不能默认在线循环常驻；
4. 新 memory 默认只记录：
   - local recoverability object；
   - failure entry；
   - escape prefix / recoverable border；
   不再记录全局 semantic sketch；
5. `mp/csm` 继续只做 ordinary-support non-regression audit；
6. public `parasol_narrow/test` 仍是下一轮 go / no-go 的第一道门。

冻结候选路线（下一轮按 `CX15-A -> CX15-B -> CX15-C -> CX15-D` 顺序执行）：

##### CX15-A：RS-RMC — Recoverability Margin Cache
类型：`recoverability object / O(1) cache`
核心想法：
1. 为局部状态抽象建立一个 cheap recoverability margin cache：
   - 当前 clearance / heading / corridor / trap geometry 下；
   - 是否仍存在低成本 reverse-setup / escape continuation；
2. 在线阶段只查询 margin；
3. margin 高时完全不干预，margin 下降时才允许轻微 bias 或标记为 review candidate。
如何继承 `CX8-D` 的有效语义：
1. 保留 `CX8-D Heavy` 中“何时需要 reverse-setup 才可恢复”的核心语义；
2. 但不直接复刻 bundle token，而是先把“still-recoverable vs entering trap”对象化。
理论抓手：
1. reachable / viable set；
2. fail-safe continuation margin；
3. 在线 `O(1)` table lookup。
与已有工作的差异：
1. 不做完整 fail-safe planning；
2. 不做 semantic token classification；
3. 而是把 reachability 思想压缩为 planner-local recoverability cache。
预期优势轴：
1. 提升 `flange vs narrow_passage` 的区分度；
2. 为后续 trigger layer 提供可解释、低成本的触发对象。

##### CX15-B：RS-EMR — Event-Triggered Micro-Review
类型：`search-dynamics gated sparse review`
核心想法：
1. accepted `RS + CX3-D` 默认执行；
2. 只有当以下事件出现时才触发一次 bounded micro-review：
   - duplicate burst；
   - accepted successor ratio collapse；
   - anchor progress flatline；
   - recoverability margin 持续下降；
3. micro-review 只在小窗口内评估少量 bundle-family / reverse-setup alternative，不进入全局 heavy mode。
如何继承 `CX8-D` 的有效语义：
1. 保留 `reverse-setup / bundle arbitration` 的局部语义；
2. 但把执行频率压缩为触发窗口级，而不是 successor 常驻级。
理论抓手：
1. event-triggered evaluation；
2. lazy search / selective edge evaluation；
3. 在线复杂度 `O(M · K)`，`M` 为触发窗口数，`K` 为每次微审查的小候选集。
与已有工作的差异：
1. 不是全局 replanning；
2. 不是 `CX14-B` 式持续 penalty maintenance；
3. 而是只在异常搜索动力学窗口中插入 tiny review。
预期优势轴：
1. 在不大幅抬升 overhead 的前提下保留 `CX8` 的局部高价值语义；
2. 避免 `CX14-B` 压缩后 signal 被整体抹平。

##### CX15-C：RS-FME — Failure Memory of Escape Motifs
类型：`cross-episode reusable failure/escape memory`
核心想法：
1. 不再存“成功整条轨迹”，而是存：
   - failure entry signature；
   - 导致失败的 primitive bundle；
   - 最终把搜索带回 recoverable basin 的短 escape motif（2-4 primitives）；
2. 在线阶段若匹配到 failure entry，就降低原入口优先级；
3. 若存在 escape motif，只对前几步做很小 bias。
如何继承 `CX8-D` 的有效语义：
1. `CX8-D Heavy` 的有效部分往往是少量关键 reverse-setup maneuver；
2. `RS-FME` 试图把这些高价值 maneuver 从 full semantic logic 中提纯为局部可复用 escape motif。
理论抓手：
1. experience reuse；
2. case-based planning；
3. bounded local prefix injection。
与已有工作的差异：
1. 不像 Experience Graphs / Thunder 存完整成功路径；
2. 不像 `CX10-D` 存 scene-level sketch；
3. 而是只存 failure-to-escape 的局部 motif。
预期优势轴：
1. 最有希望把 hard narrow regime 中的稀疏正向 maneuver 变成可复用资产；
2. 但也需要新的数据管道，因此放在 `A/B` 之后。

##### CX15-D：RS-CBR — Comfortable Border Repair
类型：`local depression border repair`
核心想法：
1. 当搜索进入 local depression 时，不做全局 penalty，也不直接调用 sketch；
2. 而是在局部窗口内找出仍具 recoverability 的 border states；
3. 然后只对当前 depression 内部做一次小型 reverse-wave repair，把优先级抬向 recoverable border，再恢复 baseline。
如何继承 `CX8-D` 的有效语义：
1. `CX8-D Heavy` 实质上在 hard case 中阻止搜索继续错误 commitment；
2. `RS-CBR` 用 border repair 实现同样的“不要继续往 trap 深处走”的语义，但不要求显式 token。
理论抓手：
1. depression avoidance；
2. dead-end border propagation；
3. 在线 `O(B)`，仅在触发窗口内对小 basin 做局部反向传播。
与已有工作的差异：
1. 不像 `CX14-B` 只是累计 penalty；
2. 不像 `CX13` 只是换 queue discipline；
3. 而是把 recoverable border 作为局部修复目标。
预期优势轴：
1. 若 `A/B` 已能定位 trigger 但仍不能方向性逃离局部塌缩，这条路线最值得跟进；
2. 也是当前四条中理论最完整、实现风险最高的分支。

最低验收标准：
1. public `exp4` 上必须同时满足：
   - `exp_delta > 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - `flange exp_delta >= 0`；
2. `mp/csm` ordinary-support 不得劣化；
3. 若 public gate 不通过，不得消费 `rs_root_hard_v2/test`；
4. 严禁把 `recoverability` 又退化成 another sketch family proxy。

失败判据：
1. 方案本质上仍在做 semantic token / sketch / defer 修补，只是换名字；
2. 方案不能给出 recoverability object 或 event trigger 的明确实现对象；
3. 高开销 computation 再次变成在线循环常驻；
4. failure memory 只存成功路径而不存 failure / escape 局部模式。

本阶段结论：
1. `CX15` 不应继续问“哪个 token 是对的”，而应问：
   - 当前是否仍可恢复；
   - 是否值得做一次额外微审查；
   - 过去失败过的局部模式能否被再次利用。
2. 当前首选执行入口：`CX15-A / RS-RMC`；
3. 当前最值得与首选组合验证的 companion：`CX15-B / RS-EMR`；
4. 当前最高上限、但需要新数据管道的路线：`CX15-C / RS-FME`；
5. 当前理论最完整、实现最重的备选：`CX15-D / RS-CBR`。

本轮实现结果（`2026-03-12`，对应产物：`reports/rs_p0cx15_a_pilot_v1.md`、`reports/rs_p0cx15_b_pilot_v1.md`、`reports/rs_p0cx15_c_pilot_v1.md`、`reports/rs_p0cx15_d_pilot_v1.md`、`reports/rs_p0cx15_round1_summary.md`、`reports/rs_p0cx15_standard_audit_v1.md`）：
1. **统一协议**：
   - trial selection 严格只使用 `calib_hard_v1`；
   - public 仅消费 `parasol_narrow/test` 的 `exp3/exp4` 固定预算口径；
   - `mp/csm` 继续只做 ordinary-support `build_standard_field == accepted CX3-D` audit；
   - 只有在 public gate 通过时才允许升级到 `rs_root_hard_v2/test`，本轮四条路线均未触发该升级。
2. **`CX15-A / RS-RMC`**：
   - `calib_val`：`exp_delta = -226.143`，`mean_time_overhead_ratio = 1.279175`；
   - public `exp4`：`exp_delta = -0.944`，`mean_time_overhead_ratio = 1.295769`，`flange exp_delta = 0.0`；
   - `No-Recoverability` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.166530`）；
   - 读法：recoverability cache 确实在动，但当前实现主要带来 runtime 放大，只有 `narrow_passage +3.75` 的局部弱信号，整体仍为负。
3. **`CX15-B / RS-EMR`**：
   - `calib_val`：`exp_delta = +174.571`，`mean_time_overhead_ratio = 1.431252`；
   - public `exp4`：`exp_delta = -101.778`，`mean_time_overhead_ratio = 1.412248`，`flange exp_delta = -242.4`；
   - `Always-Trigger` 与 `Full` 几乎完全一致；
   - 读法：event-triggered micro-review 在 dev 上有明显 leverage，但 public 上退化成灾难性误触发，说明当前 trigger 证据并不足以阻止 `flange` 式坏审查。
4. **`CX15-C / RS-FME`**：
   - `calib_val`：`exp_delta = -2.286`，`mean_time_overhead_ratio = 0.339907`；
   - public `exp3`：`exp_delta = +0.389`，`mean_time_overhead_ratio = 0.402889`；
   - public `exp4`：`exp_delta = -0.278`，`mean_time_overhead_ratio = 0.389232`，`flange exp_delta = -2.4`；
   - `No-Memory` ablation 退化为 public tie（`exp_delta = 0.0`，overhead `0.245052`）；
   - 读法：failure/escape motif memory 是本轮 **least-bad branch**，说明跨 episode 的 escape memory 有弱方法信号，但目前既不够强，也还没压到 `<0.30`。
5. **`CX15-D / RS-CBR`**：
   - `calib_val`：`exp_delta = +756.286`，`mean_time_overhead_ratio = 0.561131`；
   - public `exp4`：`exp_delta = -23.222`，`mean_time_overhead_ratio = 0.669320`，`flange exp_delta = -3.4`；
   - `No-Border-Repair` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.211582`）；
   - 读法：border repair 在 dev 上极强，但 public 直接转负，说明它当前更像 narrow hard slice 的过拟合修复，而非稳健通用机制。
6. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx15_standard_audit_v1.md` 显示 `CX15-A/B/C/D` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而 round1 的负结果不是 protocol drift 或 ordinary-support 漂移导致，而是 public hard regime 上确实没有形成净增益。
7. **排序与 go / no-go**：
   - 当前排序：`CX15-C` > `CX15-A` > `CX15-D` > `CX15-B`；
   - 但四条路线都未满足 public gate：
     - `CX15-A/B/D`：整体负且 overhead 高；
     - `CX15-C`：最接近，但仍是 `exp4 -0.278` 且 overhead `0.389232`；
   - 因而本轮 **没有任何 `CX15` 分支可进入 hard-test promotion**。
8. **最终判定**：
   - `CX15` 证明：
     - “recoverability object”本身是值得研究的；
     - “escape memory”比 event-triggered review 和 border repair 更接近稳定方向；
   - 但同样也证明：
     - 当前 recoverability/trigger/memory family 仍未打破 `P0-CX` 的 public gate；
     - 最好的 `CX15-C` 仍然只是 weak signal，而不是可主文支撑的 accepted branch；
   - 因而 **`P0-CX15` 应冻结为 `FAILED`**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。

#### P0-CX16：面向根本性突破的 macro-primitive / viability / motif / substrate 新方向（已冻结为失败路线）
状态：`FAILED（2026-03-12：CX16-B/C/D/A/E 首轮实现与 public parasol + mp/csm audit 已完成；五条系统性重构路线均未通过 public gate）`
是否需要模型/方法修改：`是（允许引入较大幅度系统改造，包括原生 macro library、viability oracle、bounded local review、failure motif compiler、planner substrate 重构）`

目标：
在承认 `CX1-CX15` 的常规 planner-hook / field-guidance 范式已接近局部上限的前提下，设计一轮更激进、但仍以 accepted `RS + refined CX3-D / RS-HPG` 为根基参照的 `CX16` 方案，着眼于以下五个方面寻求根本性突破：

1. **原生 macro-primitive / maneuver library 重构**；
2. **recoverability / viability oracle 作为一等对象**；
3. **事件触发的 bounded local review**；
4. **跨 episode 的 failure→escape motif 编译**；
5. **planner substrate 级别重构**。

为什么需要 `CX16`：
1. `CX8-D Heavy` 已证明强语义 ceiling 为正，但 successor-level 执行不可部署；
2. `CX10-CX12` 已证明 sketch/defer/repair 家族会稳定掉进 `误触发 vs 过度抑制`；
3. `CX13` 已证明 static allocation / schedule / contract 只会重排搜索，不会自动产生 leverage；
4. `CX14` 已证明 episode-local memory 方向本身正确，但若只记“重复失败”而不记“是否仍可恢复”，压开销后会退化为 public tie；
5. `CX15` 已证明 recoverability / trigger / memory family 比先前对象更接近本质，但即使是 best branch `CX15-C` 也仍只是 weak signal（`exp4 = -0.278`, `overhead = 0.389232`），不足以成为 accepted branch。

调研产物：
1. 详细文献调研与候选冻结见：`reports/rs_p0cx16_design_scout_v1.md`；
2. 该报告的主结论是：下一轮若还要追求根本性突破，就不能继续做“小一号的 gate / score / review”，而必须把 `macro action language + viability object + bounded review + motif memory + substrate` 联合起来重新定义 planner 能力边界。

调研主结论（按五个焦点归纳）：
1. **Macro-primitive / maneuver library** 文献（CoRL 2021, 2022 adaptive primitives, 2025 IGHA*, ICRA 2024 safe-by-design primitives）说明：
   - primitive set 的组织方式本身就是 planner 能力的一部分；
   - 真正的多步 maneuver 若仍靠在线拼接和 heuristic 偏置诱导，很难稳定部署；
2. **Recoverability / viability oracle** 文献（RSS 2019, RSS 2020, RSS 2023, viability theory）说明：
   - 当前项目真正缺的不是“是不是瓶颈”判断，而是“从这里是否仍有低成本恢复 continuation”这一对象；
3. **Bounded local review** 文献（ICAPS 2019 lazy search, ICRA 2024 When to Replan, NeurIPS 2023 online replanning, CoRL 2023 choose-what-to-predict）说明：
   - 高开销 computation 必须由异常事件触发，而不能常驻在线循环；
4. **Failure→escape motif** 文献（Experience Graphs, Thunder, RSS 2024 narrow-corridor experience）说明：
   - 跨 episode 经验复用在 narrow / repetitive geometry 中成立；
   - 但当前最有价值的经验单元不是成功整条路径，而是失败入口与短逃逸模式；
5. **Planner substrate 重构** 文献（MeshA*, IGHA*, graph-of-convex-sets / convex optimization planning）说明：
   - 若 fixed primitive tree / fixed substrate 本身是瓶颈，外围 hook 再聪明也只是补丁。

统一设计约束：
1. 允许系统性改造，但必须仍以 accepted `RS + refined CX3-D / RS-HPG` 为对照根基；
2. 禁止退回到“再造一层 semantic token / defer / gate”；
3. 高开销 computation 只能由 bounded local review 触发，不能常驻；
4. 新 memory 默认存储：
   - viability / recoverability object；
   - failure entry；
   - escape motif；
   不再以 scene-level sketch 为主；
5. 若引入 planner substrate 重构，必须单独给出：
   - 与 accepted 主线的公平对照口径；
   - `mp/csm/parasol_narrow` 的一致实验协议；
6. 任何路线若无法解释“为什么它比 `CX15-C` 更可能形成根本性 leverage”，应直接降级或拒绝。

冻结候选路线（候选标签按五个焦点命名；推荐执行顺序见后）：

##### CX16-A：RS-NML — Native Macro Library
类型：`原生 macro-primitive / maneuver library 重构`
核心想法：
1. 把 `reverse-setup / escape-swerve / micro-k-turn` 等少量高价值 maneuver 直接编成 planner 原生 macro-primitives；
2. macro library 可由手工初始化 + `CX8-D Heavy` / `CX15-C` failure→escape 数据离线编译联合得到；
3. 在线阶段不再“猜要不要反向 setup”，而是原生可选。
如何继承当前有效语义：
1. 直接继承 `CX8-D Heavy` 唯一被证明有价值的多步 maneuver 语义；
2. 把它从 online arbitration 改成原生动作语言。
理论抓手：
1. macro-action search；
2. maneuver automata；
3. hierarchical motion primitives。
与已有工作的差异：
1. 不再是 learned bias；
2. 不再是 semantic token；
3. 而是把高价值语义硬编码为 planner 原生动作空间。
预期优势轴：
1. 若当前瓶颈主要来自 primitive language 表达力不足，这条路线最可能带来质变；
2. 但 branching factor 与 library 管理是主要风险。

##### CX16-B：RS-VGO — Viability-Guided Oracle
类型：`recoverability / viability oracle 作为一等对象`
核心想法：
1. 为局部状态抽象建立 viability / recoverability oracle：
   - still-recoverable；
   - boundary；
   - near-trap；
2. 标签来自 bounded reverse rollout / local reachability proxy 蒸馏，而不是 family label；
3. 在线阶段 oracle 可作为 small network / coarse cache / lattice attribute 被查询。
如何继承当前有效语义：
1. 把 `CX8-D` 中“何时必须 reverse-setup 才能继续”的语义改写为 viability margin。
理论抓手：
1. viability kernel；
2. fail-safe continuation margin；
3. local reachable set approximation。
与已有工作的差异：
1. 不是 semantic classifier；
2. 不是 full online reachability；
3. 而是 planner-state attribute 形式的 cheap viability object。
预期优势轴：
1. 最有希望从根本上解决 `flange vs narrow_passage` 的可分性问题；
2. 也是后续 review / motif / substrate 路线的共同基础。

##### CX16-C：RS-BLR — Bounded Local Review
类型：`事件触发的 bounded local review`
核心想法：
1. accepted `RS + refined CX3-D` 作为默认执行主干；
2. 仅在 anomaly trigger 出现时启动局部 review：
   - duplicate burst；
   - accepted successor ratio collapse；
   - open-list entropy collapse；
   - viability margin sudden drop；
3. review 只在小窗口内评估少量 alternative macro / reverse rollout / local bundle duel；
4. review 结束后立即退回 baseline，不让高开销逻辑常驻。
如何继承当前有效语义：
1. 保留 `CX8-D` 的局部 maneuver comparison；
2. 但严格限制其执行范围与频率。
理论抓手：
1. event-triggered evaluation；
2. lazy search；
3. bounded local counterfactual review。
与已有工作的差异：
1. 不是全局 replanning；
2. 不是 global schedule；
3. 而是 anomaly-window 上的 local search fork。
预期优势轴：
1. 若 current bottleneck 是“偶尔需要强语义，但不该常驻”，这条路线最有机会兼顾效果与效率；
2. 但 trigger stability 是最大风险。

##### CX16-D：RS-MEC — Motif Escape Compiler
类型：`跨 episode 的 failure→escape motif 编译`
核心想法：
1. 以 `failure entry -> short escape prefix -> recovered basin` 为最小经验单元；
2. 对这些 motif 做聚类、量化、压缩，形成可查询 compiler；
3. 在线阶段若当前局部模式匹配 failure entry，则注入极短 escape prefix bias。
如何继承当前有效语义：
1. 把 `CX8-D` / `CX15-C` 里真正起作用的少量 reverse / setup maneuver 提纯成可复用 motif。
理论抓手：
1. case-based planning；
2. experience compilation；
3. vector-quantized / symbolic memory compression。
与已有工作的差异：
1. 不存成功整条轨迹；
2. 不存 scene-level sketch；
3. 只存 failure-to-escape 的局部经验单元。
预期优势轴：
1. 最有希望把 sparse positive signal 编译成可反复利用的结构；
2. 但需要新的数据管道与 motif schema。

##### CX16-E：RS-PSR — Planner Substrate Redesign
类型：`planner substrate 级别重构`
核心想法：
1. 不再把当前 fixed primitive Hybrid A* 视为不可动的 substrate；
2. 采用多层 substrate，例如：
   - macro graph layer；
   - local lattice layer；
   - viability attribute layer；
3. 搜索先在 macro / mode graph 上粗筛，再在 local layer 细化。
如何继承当前有效语义：
1. 把 `CX8-D` 的多步 maneuver semantics、`CX15` 的 recoverability object、`CX14` 的 failure memory 统一到新的 substrate 中。
理论抓手：
1. generalized hybrid search；
2. hierarchical search substrate；
3. graph-of-convex-sets / hybrid graph。
与已有工作的差异：
1. 不是再外挂一个 policy hook；
2. 而是重写 planner backbone 的表达能力。
预期优势轴：
1. 若当前 fixed primitive tree 就是上限，这条路线最可能带来根本性突破；
2. 但也是实现与验证成本最高的方向。

推荐执行顺序（不按标签，而按证据链组织）：
1. **先做 `CX16-B / RS-VGO`**：
   - 先验证 recoverability object 本身是否终于具备区分力；
2. **再做 `CX16-C / RS-BLR`**：
   - 若 oracle 有信号，再验证 bounded review 是否能低成本保住强语义；
3. **第三做 `CX16-D / RS-MEC`**：
   - 若 `B/C` 有局部 leverage，再把稀疏 escape semantics 编译成跨 episode memory；
4. **第四做 `CX16-A / RS-NML`**：
   - 若前述证据确认正向 maneuver 真实存在且稳定，再把它们原生化为 macro library；
5. **最后做 `CX16-E / RS-PSR`**：
   - 这是最高风险、最高潜力的基座重构，应在前述证据足够时再投入。

最低验收标准：
1. public `exp4` 上必须同时满足：
   - `exp_delta > 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - `flange exp_delta >= 0`；
2. `mp/csm` ordinary-support 不得劣化；
3. 若 public gate 不通过，不得消费 `rs_root_hard_v2/test`；
4. 若路线是 substrate redesign，必须单独解释新增表达力与新增开销之间的关系，不能模糊 claim boundary。

失败判据：
1. 方案本质上仍然只是换名字的 score / gate / token / defer 变体；
2. 方案无法给出：
   - 明确的 recoverability object；
   - 明确的 trigger object；
   - 明确的 motif / macro / substrate object；
3. 高开销逻辑再次默认常驻在线循环；
4. planner substrate 改造后无法给出公平、协议一致的对照。

本阶段结论：
1. `CX16` 不是“再聪明一点的 planner hook”，而是尝试让 planner 原生地拥有：
   - 更强动作语言；
   - 更明确可恢复性对象；
   - 更严格 bounded review 入口；
   - 更可复用的 failure-to-escape 经验；
   - 更强 substrate 表达能力。
2. 当前首选执行入口：`CX16-B / RS-VGO`；
3. 当前最值得与首选组合验证的 companion：`CX16-C / RS-BLR`；
4. 当前最值得中期保留的 memory 路线：`CX16-D / RS-MEC`；
5. 当前最重但最有可能带来根本性重构的路线：`CX16-E / RS-PSR`；
6. 当前最适合在前述证据稳定后再推进的动作语言升级：`CX16-A / RS-NML`。

本轮实现结果（`2026-03-12`，对应产物：`reports/rs_p0cx16_b_pilot_v1.md`、`reports/rs_p0cx16_c_pilot_v1.md`、`reports/rs_p0cx16_d_pilot_v1.md`、`reports/rs_p0cx16_a_pilot_v1.md`、`reports/rs_p0cx16_e_pilot_v1.md`、`reports/rs_p0cx16_round1_summary.md`、`reports/rs_p0cx16_standard_audit_v1.md`）：
1. **统一协议**：
   - trial selection 严格只使用 `calib_hard_v1`；
   - public 仅消费 `parasol_narrow/test` 的 `exp3/exp4` 固定预算口径；
   - `mp/csm` 继续只做 ordinary-support `build_standard_field == accepted CX3-D` audit；
   - 只有在 public gate 通过时才允许升级到 `rs_root_hard_v2/test`，本轮五条路线均未触发该升级。
2. **`CX16-B / RS-VGO`**：
   - `calib_val`：`exp_delta = -226.000`，`mean_time_overhead_ratio = 1.288266`；
   - public `exp4`：`exp_delta = +11.556`，`mean_time_overhead_ratio = 1.309856`，`flange exp_delta = 0.0`；
   - `No-Oracle` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.233832`）；
   - 读法：viability-guided oracle 是本轮唯一在 public overall 上重新给出明确正向 signal 的路线，但 overhead 仍高达 `+131%`，远未达部署要求。
3. **`CX16-C / RS-BLR`**：
   - `calib_val`：`exp_delta = -24.571`，`mean_time_overhead_ratio = 1.991715`；
   - public `exp4`：`exp_delta = -169.778`，`mean_time_overhead_ratio = 2.198920`，`flange exp_delta = -586.6`；
   - `No-Review` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.240982`）；
   - 读法：bounded local review 在当前实现下几乎完全退化为高开销误审查，说明 trigger 稳定性仍远不足以支撑此路线。
4. **`CX16-D / RS-MEC`**：
   - `calib_val`：`exp_delta = +660.571`，`mean_time_overhead_ratio = 0.618078`；
   - public `exp4`：`exp_delta = -35.667`，`mean_time_overhead_ratio = 0.525381`，`flange exp_delta = +4.6`；
   - `No-Motif` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.234500`）；
   - 读法：motif escape compiler 能稳定修掉 `flange`，也能在 dev 上给出很强 hard-family leverage，但 public overall 仍为负，说明 motif memory 目前还缺足够稳健的匹配与泛化。
5. **`CX16-A / RS-NML`**：
   - `calib_val`：`exp_delta = +1.429`，`mean_time_overhead_ratio = 0.202296`；
   - public `exp4`：`exp_delta = -10.000`，`mean_time_overhead_ratio = 0.239169`，`flange exp_delta = -0.2`；
   - `No-Macro-Library` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.170438`）；
   - 读法：原生 macro library 是本轮最接近部署边界的路线，overhead 与 `mp/csm` 都控制得住，但 macro set 目前对 `narrow_passage` 反而造成负迁移，未能把 `CX16-B` 的正向 viability signal 可靠转化为净收益。
6. **`CX16-E / RS-PSR`**：
   - `calib_val`：`exp_delta = +1044.714`，`mean_time_overhead_ratio = 2.241024`；
   - public `exp4`：`exp_delta = -58.722`，`mean_time_overhead_ratio = 2.478006`，`flange exp_delta = -46.6`；
   - `No-Substrate` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.242104`）；
   - 读法：planner substrate redesign 在 dev 上确实有最强的 leverage，但 public 直接崩塌，说明当前 multi-layer substrate 仍然只是更大幅度的 hard-slice overfit，而非稳健新 backbone。
7. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx16_standard_audit_v1.md` 显示 `CX16-B/C/D/A/E` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而 round1 的负结果不是 protocol drift 或 ordinary-support 漂移导致，而是 public hard regime 上确实未形成可接受的净增益。
8. **排序与 go / no-go**：
   - 当前排序：`CX16-B` > `CX16-A` > `CX16-D` > `CX16-E` > `CX16-C`；
   - 但五条路线都未通过 public gate：
     - `CX16-B`：signal 为正，但 overhead 极高；
     - `CX16-A`：overhead 合格，但 `exp_delta` 仍为负；
     - `CX16-D`：`flange` 修复成立，但 overall 仍为负且 overhead 偏高；
     - `CX16-C/E`：整体为明显负结果；
   - 因而本轮 **没有任何 `CX16` 分支可进入 hard-test promotion**。
9. **最终判定**：
   - `CX16` 证明：
     - viability oracle 确实比先前 recoverability cache 更接近有效对象；
     - macro library 是当前最接近部署边界的系统性改造；
   - 但同样也证明：
     - 仅有 viability object 还不够，若无法把它可靠地编译到动作语言或 bounded review 中，signal 仍会在 overhead 或迁移中损失；
     - 当前最好的两条路线（`CX16-B`、`CX16-A`）分别卡在：
       - `效果有了但开销太高`；
       - `开销合格但效果不再转正`；
   - 因而 **`P0-CX16` 应冻结为 `FAILED`**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。

#### P0-CX17：viability→macro 联合系统、motif automaton 与 planner substrate 重构（已完成首轮实现，未晋升主线）
状态：`COMPLETED（2026-03-13：CX17-A/B/C 首轮实现与 public parasol + mp/csm audit 已完成；CX17-C 通过 public 正向 ceiling gate 并消费 hard-test，但未在 hard-test 上维持正向 exp_delta）`
是否需要模型/方法修改：`是（允许更大幅度系统重构，包括 viability-conditioned macro system、failure→escape motif automaton、planner substrate redesign；本轮不以时间开销为首要否决项）`

目标：
在承认 `CX1-CX16` 的常规 planner-hook 增强路线已接近局部上限的前提下，围绕以下三个方面冻结一轮更激进的 `CX17` 方案，优先追求新的效果 ceiling，而不是先追求部署开销：

1. **viability oracle -> 原生 macro library 联合路线**
2. **failure -> escape motif 的更强编译化版本**
3. **planner substrate 级重构**

为什么需要 `CX17`：
1. `CX16-B` 已经证明 viability object 本身确实能在 public overall 上重新给出正向 signal（`exp4 +11.556`），但 overhead 极高；
2. `CX16-A` 已经证明 macro library 是当前最接近部署边界的系统性改造，但缺少足够强的 activation object，导致效果未转正；
3. `CX16-D` 已经证明 failure→escape motif 方向并非错误，但当前表示还太弱，无法稳定泛化；
4. `CX16-E` 已经证明 substrate 重构不能在对象未稳定前盲目先做，否则只会放大误差；
5. 因而 `CX17` 必须把：
   - viability object
   - native macro language
   - stronger motif compiler
   - new planner substrate
   做成有先后关系的联合系统，而不是再分散外挂。

调研产物：
1. 详细文献调研与候选冻结见：`reports/rs_p0cx17_design_scout_v1.md`；
2. 该报告的主结论是：若还要追求根本性突破，就应把 `viability oracle + native macro language + motif automaton + new substrate` 视作同一系统的不同层，而不是继续拆成互不相干的小模块。

调研主结论（按三个焦点归纳）：
1. **viability→macro 联合路线**（RSS 2019/2020/2023/2024 + CoRL motion primitives + IGHA* + maneuver automata）说明：
   - viability / reachability 提供了正确的“是否仍可恢复”对象；
   - macro primitives 提供了正确的“如何原生表达高价值 maneuver”对象；
   - 当前真正缺的是二者的联合闭环，而不是其中任一单体。
2. **更强的 failure→escape motif 编译**（Experience Graphs, Thunder, RSS 2024 experience-based narrow-corridor planning, neuro-symbolic abstraction）说明：
   - 经验复用在狭窄/重复几何中成立；
   - 但当前最值得存储的不是成功路径，而是失败入口、错误 maneuver 族、短逃逸前缀与恢复 basin 之间的结构关系。
3. **planner substrate 级重构**（MeshA*, IGHA*, GCS / multi-query GCS, hierarchical planning）说明：
   - 如果 fixed primitive Hybrid A* substrate 本身就是表达瓶颈，外围 hook 再强也只是补丁；
   - 但 substrate 重构必须建立在 viability object、macro language、motif compiler 已经基本正确的前提上。

统一设计约束：
1. 允许比 `CX16` 更激进的系统重构，但必须继续以 accepted `RS + refined CX3-D / RS-HPG` 为 frozen comparator；
2. 禁止退回到：
   - semantic token / sketch / defer；
   - 纯静态 schedule / allocation；
   - 常驻 successor-level heavy semantics；
3. 若引入更高开销的 offline or online computation，本轮应优先把它解释为：
   - ceiling-seeking design；
   - 而不是 deployment-ready design；
4. 所有 `CX17-*` 仍需保持：
   - public `parasol_narrow`；
   - `mp/csm` ordinary-support audit；
   - 以及 protocol 一致的 hard escalation 边界；
5. 本轮 first-pass go/no-go 不再把 `<0.30` overhead 作为首要 veto，而是优先看：
   - public `exp_delta > 0`
   - `flange exp_delta >= 0`
   然后再把 runtime 作为第二层压缩目标。

冻结候选路线（下一轮按 `CX17-A -> CX17-B -> CX17-C` 顺序执行）：

##### CX17-A：RS-VML — Viability-Conditioned Macro Library
类型：`viability oracle -> native macro library 联合系统`
核心想法：
1. 离线阶段用 bounded reverse rollout / local reachability proxy 生成 viability label / margin；
2. 从 `CX8-D Heavy` 与 `CX16-D` 的正向片段提取高价值 maneuver motifs，并聚类为少量 native macro-primitives；
3. 训练或蒸馏一个 `Viability-to-Macro` 模块：
   - 输入：局部几何 patch + viability label / margin；
   - 输出：允许激活的 macro subset；
4. 在线阶段默认执行 accepted `CX3-D`，仅在 viability 边界区间激活相应 macro library。
如何继承当前有效语义：
1. 直接继承 `CX8-D Heavy` 的高价值多步 maneuver；
2. 使用 `CX16-B` 已验证的 viability object 作为激活条件。
理论抓手：
1. viability kernel / reachable continuation margin；
2. macro-action search；
3. maneuver automata / hierarchical motion primitives。
与已有工作的差异：
1. 不是 oracle 和 macro 的简单串联；
2. 而是 **由 viability object 决定 macro action language**。
预期优势轴：
1. 这是当前最有希望同时带来新效果 ceiling 与后续可压缩空间的路线；
2. 也是 `CX17` 的首选执行入口。

##### CX17-B：RS-MAG — Motif Automaton Graph
类型：`更强的 failure→escape motif 编译`
核心想法：
1. 不再把 motif 存成 `key -> sequence`；
2. 把经验单元升级为：
   - failure entry class
   - bad maneuver family
   - escape prefix family
   - recovered basin class
   共同组成的 **motif automaton graph**；
3. 在线阶段先匹配当前 entry class，再沿 automaton 选择 escape branch，必要时在少量分支间做 tiny duel。
如何继承当前有效语义：
1. 继承 `CX15-C / CX16-D` 的 failure→escape 正方向；
2. 解决其经验表达太弱、匹配不稳的问题。
理论抓手：
1. case-based planning；
2. experience graphs；
3. symbolic / neuro-symbolic automata compression。
与已有工作的差异：
1. 不复用成功整条路径；
2. 不存 scene-level sketch；
3. 而是把 failure-to-escape 编译成可查询 automaton。
预期优势轴：
1. 若 `CX17-A` 只能得到局部 gains，这条路线最有希望把 sparse positive maneuver 编译成更强的结构记忆；
2. 但数据管道复杂度显著更高。

##### CX17-C：RS-HPS — Hybrid Planner Substrate
类型：`planner substrate 级重构`
核心想法：
1. 用三层 substrate 替代当前 fixed primitive Hybrid A*：
   - Viability Layer
   - Macro Layer
   - Local Lattice Layer
2. 搜索先在 viability-aware macro graph 上粗筛，再在 local layer 细化；
3. `CX17-A` 的 macro library 和 `CX17-B` 的 motif automaton 都作为 substrate 内部对象，而不再作为外挂 policy hook。
如何继承当前有效语义：
1. `CX8-D` 的多步 maneuver semantics 进入 macro layer；
2. viability object 进入 viability layer；
3. motif compiler 进入 macro-edge prior。
理论抓手：
1. generalized hybrid search；
2. hierarchical substrate；
3. graph-of-convex-sets / multi-query reusable graph。
与已有工作的差异：
1. 不是更复杂的 successor_policy；
2. 而是把高价值对象直接做进 planner backbone。
预期优势轴：
1. 若 `CX17-A/B` 证明对象正确，这将是最有机会带来真正 ceiling shift 的路线；
2. 也是风险和工程成本最高的路线，因此排在最后。

推荐执行顺序：
1. **先做 `CX17-A / RS-VML`**：
   - 这是当前证据最完整、最值得先验证闭环是否成立的路线；
2. **再做 `CX17-B / RS-MAG`**：
   - 若 `A` 只形成局部正项，则用更强 motif compiler 放大并稳定 sparse signal；
3. **最后做 `CX17-C / RS-HPS`**：
   - 只有当前两个对象都站住脚，才值得推进 substrate 重写。

最低验收标准（相对 `CX16` 调整）：
1. first-pass go/no-go 以效果 ceiling 为首：
   - public `exp4 exp_delta > 0`
   - `flange exp_delta >= 0`
2. runtime 仍必须完整记录，但在 first-pass 中不作为首要 veto；
3. 若 public overall 不转正，不得消费 `rs_root_hard_v2/test`；
4. 所有 `mp/csm` ordinary-support audit 仍必须保持不劣。

失败判据：
1. 方案本质上仍然只是:
   - score/gate/defer 的换名版本；
   - 或者没有真正把 viability / macro / motif / substrate 做成联合系统；
2. 方案不能给出：
   - 明确 viability object；
   - 明确 macro activation rule；
   - 明确 motif automaton representation；
   - 或明确 substrate layering；
3. 大幅度系统重构后无法给出协议一致的公平对照；
4. 只放大开销，没有形成任何新的 public positive signal。

本阶段设计结论：
1. `CX17` 应从 “外挂增强 accepted planner” 转向 “构建新的联合 planner system”；
2. 当前首选执行入口：`CX17-A / RS-VML`；
3. 当前最值得作为 follow-up 的 memory/compiler 路线：`CX17-B / RS-MAG`；
4. 当前最终、也是最重的 backbone 级路线：`CX17-C / RS-HPS`。

本轮实现结果（`2026-03-13`，对应产物：`reports/rs_p0cx17_a_pilot_v1.md`、`reports/rs_p0cx17_b_pilot_v1.md`、`reports/rs_p0cx17_c_pilot_v1.md`、`reports/rs_p0cx17_round1_summary.md`、`reports/rs_p0cx17_standard_audit_v1.md`）：
1. **统一协议**：
   - trial selection 严格只使用 `calib_hard_v1`；
   - public 仅消费 `parasol_narrow/test` 的 `exp3/exp4` 固定预算口径；
   - hard-test 仅在 public overall 转正且 `flange` 不退化时才触发；
   - `mp/csm` 继续只做 ordinary-support `build_standard_field == accepted CX3-D` audit。
2. **`CX17-A / RS-VML`**：
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.359514`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.387409`，`flange exp_delta = 0.0`；
   - `No-Macro-Activation` 与 `Full` 的差异主要体现在额外 overhead，而非效果增益；
   - 读法：当前 viability→macro 联合闭环还不足以形成净 gain，基本退化为带额外代价的 public tie。
3. **`CX17-B / RS-MAG`**：
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.295240`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.323685`，`flange exp_delta = 0.0`；
   - `No-Automaton` 与 `Full` 同样没有形成效果差异；
   - 读法：motif automaton graph 的表示增强并未把 sparse positive signal 放大出来，仍然只得到 public tie。
4. **`CX17-C / RS-HPS`**：
   - `calib_val`：`exp_delta = -225.429`，`mean_time_overhead_ratio = 0.645330`；
   - public `exp4`：`exp_delta = +3.278`，`mean_time_overhead_ratio = 0.686728`，`flange exp_delta = +1.0`；
   - 因为 public overall 转正且 `flange` 不退化，本轮按协议升级到 `rs_root_hard_v2/test`；
   - hard-test：`exp_delta = -4.904`，`mean_time_overhead_ratio = 1.030592`；
   - family-wise hard breakdown 显示：
     - `narrow_passage +5.538`
     - `flange +0.385`
     - `maze +0.091`
     - 但 `deadend_labyrinth -40.8`、`parasol_misc -7.0` 吃掉了整体正项；
   - 读法：hybrid planner substrate 是本轮唯一跨过 public positive ceiling gate 的路线，说明联合系统方向比 `CX17-A/B` 更接近真正新 ceiling；但 hard-test 仍未维持正向 overall，不能晋升 accepted 主线。
5. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx17_standard_audit_v1.md` 显示 `CX17-A/B/C` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而 round1 的结论不是 protocol drift，而是 public/hard hard-regime 上真实形成的结果。
6. **排序与 go / no-go**：
   - 当前排序：`CX17-C` > `CX17-B` ≈ `CX17-A`；
   - `CX17-C` 是唯一通过 public positive ceiling gate 的分支；
   - 但由于 hard-test `exp_delta` 未转正，本轮 **没有任何 `CX17` 分支可晋升 accepted 主线**。
7. **最终判定**：
   - `CX17` 证明：
     - viability + macro + motif + substrate 的联合系统，确实比 `CX16` 的分立对象更接近根本性突破；
     - `CX17-C` 是 `CX8-D Heavy` 之后第一个在更激进系统层面重新拿到 public 正向 ceiling 的路线；
   - 但同样也证明：
     - 当前 `CX17-C` 仍未在 hard-test 上完成真正泛化；
     - `CX17-A/B` 尚不足以单独支撑新 ceiling；
   - 因而 **`CX17` 不晋升 accepted 主线**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`；
   - 但与 `CX10-CX16` 的多数失败不同，`CX17-C` 应被视为当前最值得保留的高潜力 follow-up，而不是立即彻底冻结。

#### P0-CX18：面向 `CX17-C` 深化的 viability-macro-system / motif-compiler-graph / graph-substrate 新方向（已完成首轮实现，未晋升主线）
状态：`COMPLETED（2026-03-13：CX18-A/B/C 首轮实现与 public parasol + mp/csm audit 已完成；三条路线均未通过 public positive ceiling gate）`
是否需要模型/方法修改：`是（允许更大幅度系统改造，包括 viability state machine、macro language type system、motif compiler graph、graph planner substrate）`

目标：
在 `CX17-C` 已经通过 public 正向 ceiling gate、但 hard-test 未维持转正的前提下，冻结一轮比 `CX17` 更强的一体化 `CX18` 方案，围绕以下三个方面继续追求根本性突破：

1. **`CX17-C` 这类联合 planner substrate 路线继续做深**
2. **`viability oracle -> native macro library` 的更强闭环**
3. **`failure -> escape motif` 的更强编译化版本**

为什么需要 `CX18`：
1. `CX17-C` 已经证明：
   - 联合 substrate 是目前唯一通过 public positive ceiling gate 的方向；
   - 但 hard-test `exp_delta = -4.904` 说明其联合系统还不够稳，尤其在 `deadend_labyrinth` 与 `parasol_misc` 上存在失分；
2. `CX16-B` 已经证明 viability object 本身能够给出 public 正向 signal，但若不和动作语言真正闭环，会死于高开销；
3. `CX16-A` 已经证明 macro library 接近部署边界，但如果没有更强激活规则，效果不转正；
4. `CX16-D` 与 `CX17-B` 已经证明 motif 方向不是错，但当前经验表示仍太弱；
5. 因而 `CX18` 的主问题不应再是“再加一个模块”，而是：
   - 如何把 viability 变成 macro language 的类型系统；
   - 如何把 motif 变成 graph compiler，而不是表查结果；
   - 如何让新的 substrate 原生承载这些对象。

调研产物：
1. 详细文献调研与候选冻结见：`reports/rs_p0cx18_design_scout_v1.md`；
2. 该报告的主结论是：若要在 `CX17-C` 的基础上继续突破，最合理的下一步不是再写一个更大的 hook，而是把：
   - viability state machine
   - macro activation grammar
   - motif compiler graph
   - graph substrate
   做成更强的一体化 planner system。

调研主结论（按三个焦点归纳）：
1. **继续做深 `CX17-C` 这类联合 substrate** 文献（MeshA*, IGHA*, GCS, multi-query GCS, hierarchical planning）说明：
   - 新 substrate 必须有清晰分层：
     - viability layer
     - macro layer
     - local lattice / refinement layer；
   - query-time 应优先复用离线结构，而不是在线重新拼装对象。
2. **更强的 viability→macro 闭环** 文献（RSS 2019/2020/2023/2024 + motion primitive / maneuver automata）说明：
   - viability 若仍只是 score，就只能做 activation；
   - 真正值得尝试的是把 viability 变成 **macro language 的类型系统 / enable condition**。
3. **更强的 motif compiler** 文献（Experience Graphs, Thunder, RSS 2024 experience-based corridor planning, neuro-symbolic abstraction, compositional behavior learning）说明：
   - 经验若想真正泛化，必须从 `entry -> sequence` 升级为：
     - failure class
     - bad maneuver family
     - escape class
     - recovered basin class
     之间的结构图。

统一设计约束：
1. 允许比 `CX17` 更重的系统重构，但仍须以 accepted `RS + refined CX3-D / RS-HPG` 为 frozen comparator；
2. 禁止退回到：
   - semantic token / sketch / defer；
   - 纯静态 schedule / allocation；
   - 常驻 successor-level heavy semantics；
3. `CX18` 不再把时间开销作为 first-pass veto，而优先追求新效果 ceiling；
4. public / hard-test 口径仍需保持严格协议一致；
5. 所有 `mp/csm` ordinary-support audit 仍必须保持不劣；
6. 任何路线若无法解释“相较 `CX17-C`，它新增的结构 leverage 在哪里”，应直接拒绝。

冻结候选路线（下一轮按 `CX18-A -> CX18-B -> CX18-C` 顺序执行）：

##### CX18-A：RS-VMS — Viability Macro System
类型：`更强的 viability oracle -> native macro library 闭环`
核心想法：
1. 把 viability oracle 从 score 升级为 discrete viability state machine：
   - safe-progress
   - recoverable-boundary
   - reverse-required
   - near-trap；
2. 每个 viability state 只允许一小组 native macro families；
3. planner 在线阶段不再“根据 oracle 分数选 macro”，而是：
   - 先进入 viability state；
   - 再在该 state 的 macro grammar 内搜索。
如何继承当前有效语义：
1. 继承 `CX8-D Heavy` 的高价值多步 maneuver；
2. 使用 `CX16-B` / `CX17-C` 已验证有效的 viability signal 作为 macro grammar 的类型系统。
理论抓手：
1. viability kernel；
2. maneuver automata；
3. grammar-constrained search。
与已有工作的差异：
1. 不再是 oracle 和 macro 的弱耦合外挂；
2. 而是由 viability object 直接决定动作语言。
预期优势轴：
1. 这是当前最小、但最可能真正完成 `效果 ceiling -> 可执行动作语言` 闭环的路线；
2. 当前首选执行入口。

##### CX18-B：RS-MCG — Motif Compiler Graph
类型：`更强的 failure -> escape motif 编译化版本`
核心想法：
1. 把 `failure -> escape` memory 升级为 compiler graph：
   - nodes：failure class / escape class / recovered basin class；
   - edges：macro family transitions；
2. motif graph 不再返回单条 sequence，而是返回：
   - 下一步应进入的 escape class；
   - 合法 macro family 集；
   - 预期恢复 basin；
3. planner 在 graph 上做 tiny policy-over-graph，而不是简单 prefix 注入。
如何继承当前有效语义：
1. 继承 `CX16-D / CX17-B` 的 failure→escape 正方向；
2. 解决当前 motif 仅为弱检索结构、难以稳定改变搜索主干的问题。
理论抓手：
1. structured memory；
2. symbolic behavior graph；
3. case-based planning with abstraction transitions。
与已有工作的差异：
1. 不是 path memory；
2. 不是 scene-level sketch；
3. 而是把经验编译成可组合的 graph prior。
预期优势轴：
1. 若 `CX18-A` 只能得到局部 ceiling，这条路线最有希望放大和稳定 sparse positive signal；
2. 但数据管道复杂度会显著上升。

##### CX18-C：RS-GPS — Graph Planner Substrate
类型：`更深的联合 planner substrate`
核心想法：
1. 用统一 graph substrate 替换当前 `successor_policy` 联合体系：
   - Viability Graph
   - Macro Graph
   - Motif Prior Graph
2. 搜索流程：
   - 先在 graph substrate 上做 mode routing；
   - 再在 local lattice 上做 executable refinement；
   - refinement 失败时反馈更新 graph state，而不是简单回退。
如何继承当前有效语义：
1. `CX17-C` 的联合 substrate 是直接前身；
2. `CX18-A/B` 的 viability state machine 与 motif compiler graph 将成为新 substrate 的原生对象。
理论抓手：
1. hierarchical graph search；
2. multi-query reusable planning graphs；
3. graph-of-convex-sets / generalized hybrid search。
与已有工作的差异：
1. 不再存在“外挂 hook”；
2. planner 本体本身就是由 graph substrate 定义的。
预期优势轴：
1. 若 `CX18-A/B` 验证了对象正确，`CX18-C` 最有希望把当前 public ceiling 推到真正的 hard-test ceiling；
2. 也是风险和工程量最高的路线，因此放在最后。

推荐执行顺序：
1. **先做 `CX18-A / RS-VMS`**：
   - 先验证 viability 是否能真正约束 macro language，而不是只做 activation；
2. **再做 `CX18-B / RS-MCG`**：
   - 若 `A` 只能给出局部 gains，则用更强 compiler 稳定和放大这些 gains；
3. **最后做 `CX18-C / RS-GPS`**：
   - 只有当前两个对象都站住脚，才值得推进统一 graph substrate。

最低验收标准：
1. first-pass gate：
   - public `exp4 exp_delta > 0`
   - `flange exp_delta >= 0`
2. 若 public gate 通过，则允许消费 `rs_root_hard_v2/test`；
3. hard-test 若也维持正向，才进入后续 compression / deployability planning；
4. `mp/csm` ordinary-support 仍不得劣化。

失败判据：
1. 方案本质上仍然只是更复杂的 score / gate / defer；
2. 方案无法给出：
   - 明确 viability state machine；
   - 明确 macro grammar；
   - 明确 motif graph；
   - 明确 substrate layering；
3. 新系统只放大开销，没有带来任何新的 public positive ceiling；
4. hard-test 结果出来后再回头调结构或调参，违背 protocol。

本阶段设计结论：
1. `CX18` 不再是“再做一个更强模块”，而是把：
   - viability 变成动作语言的类型系统；
   - motif 变成 graph compiler；
   - substrate 变成统一 graph planner；
   做成更强的一体化系统。
2. 当前首选执行入口：`CX18-A / RS-VMS`；
3. 当前最值得作为效果放大器的 follow-up：`CX18-B / RS-MCG`；
4. 当前最终、也是最重的 backbone 路线：`CX18-C / RS-GPS`。

本轮实现结果（`2026-03-13`，对应产物：`reports/rs_p0cx18_a_pilot_v1.md`、`reports/rs_p0cx18_b_pilot_v1.md`、`reports/rs_p0cx18_c_pilot_v1.md`、`reports/rs_p0cx18_round1_summary.md`、`reports/rs_p0cx18_standard_audit_v1.md`）：
1. **统一协议**：
   - trial selection 严格只使用 `calib_hard_v1`；
   - public 仅消费 `parasol_narrow/test` 的 `exp3/exp4` 固定预算口径；
   - hard-test 仅在 public overall 转正且 `flange` 不退化时才触发；
   - `mp/csm` 继续只做 ordinary-support `build_standard_field == accepted CX3-D` audit。
2. **`CX18-A / RS-VMS`**：
   - `calib_val`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.303172`；
   - public `exp4`：`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.320154`，`flange exp_delta = 0.0`；
   - `No-State-Macro` 与 `Full` 仅在 overhead 上存在差异；
   - 读法：把 viability 升级为 macro language 的类型系统之后，当前实现仍未从 public tie 中走出来，说明 state-machine 约束本身还不够形成额外 leverage。
3. **`CX18-B / RS-MCG`**：
   - `calib_val`：`exp_delta = -17.143`，`mean_time_overhead_ratio = 0.957863`；
   - public `exp4`：`exp_delta = -5.444`，`mean_time_overhead_ratio = 0.948324`，`flange exp_delta = +0.4`；
   - `No-Compiler-Graph` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.343280`）；
   - 读法：motif compiler graph 确实在“动”，但当前版本只是带来了小幅 `flange` 修复，没有形成 overall 正项，且代价很高。
4. **`CX18-C / RS-GPS`**：
   - `calib_val`：`exp_delta = -242.714`，`mean_time_overhead_ratio = 1.948485`；
   - public `exp4`：`exp_delta = -4.611`，`mean_time_overhead_ratio = 1.977432`，`flange exp_delta = +1.6`；
   - `No-Graph-Substrate` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.294326`）；
   - 读法：更深的 graph planner substrate 继续强化了 `flange` 修复和 `narrow_passage` 局部正项（`+9.25`），但 `parasol_misc -21.333` 仍吃掉整体收益，说明当前 substrate 层仍在放大部分坏结构。
5. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx18_standard_audit_v1.md` 显示 `CX18-A/B/C` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而 round1 的结果不是 protocol drift，而是 public hard regime 上真实形成的结果。
6. **排序与 go / no-go**：
   - 当前排序：`CX18-A` > `CX18-C` > `CX18-B`；
   - 但三条路线都未满足 public positive ceiling gate：
     - `CX18-A`：整体 tie；
     - `CX18-B`：overall 负但 `flange` 小幅转正；
     - `CX18-C`：局部 hard-family 有正项，但 overall 仍负；
   - 因而本轮 **没有任何 `CX18` 分支可进入 hard-test promotion**。
7. **最终判定**：
   - `CX18` 证明：
     - 更强的 viability state machine、motif compiler graph、graph substrate 都不是错对象；
     - 但当前三条路线仍未把这些对象整合成可稳定转化 overall gain 的系统；
   - 其中：
     - `CX18-A` 更像“约束正确但 leverage 不足”；
     - `CX18-B` 更像“经验结构有信号但太弱且太重”；
     - `CX18-C` 更像“局部结构修复成立，但整体仍被 misc / deadend 类失分抵消”；
   - 因而 **`CX18` 不晋升 accepted 主线**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。

#### P0-CX19：在 `CX17-C` ceiling 信号基础上继续做深的 viability-macro-grammar / motif-compiler-graph / unified-graph-substrate 路线（当前下一轮执行入口）
状态：`COMPLETED（2026-03-13：CX19-A/B/C 首轮实现与 public parasol + mp/csm audit 已完成；三条路线均未通过 public positive ceiling gate）`
是否需要模型/方法修改：`是（允许颠覆性系统重构，包括 viability state machine、macro grammar、motif compiler graph、unified planner substrate；本轮仍以效果 ceiling 为首要目标）`

目标：
在 `CX17-C` 已经通过 public 正向 ceiling gate、但 hard-test 未维持转正的前提下，冻结一轮比 `CX18` 更强的一体化 `CX19` 方案，围绕以下三个方面继续追求根本性突破：

1. **继续做深 `CX17-C` 这类联合 substrate 路线**
2. **`viability oracle -> native macro library` 的更强闭环**
3. **`failure -> escape motif` 的更强编译化版本**

为什么需要 `CX19`：
1. `CX17-C` 说明联合 substrate 是当前唯一真正跨过 public positive ceiling gate 的方向，但 hard-test `exp_delta = -4.904` 说明其系统还不够原生、不够稳；
2. `CX16-B` 与 `CX16-A` 说明 viability object 与 macro library 各自都有价值，但当前还没有形成真正强耦合的动作语言闭环；
3. `CX16-D`、`CX17-B`、`CX18-B` 说明 motif 方向不是错，但当前经验表示仍太弱，尚未真正进入 planner 主干；
4. 因而 `CX19` 的主问题不应再是“再加一个模块”，而应是：
   - 如何把 viability 变成 macro grammar 的类型系统；
   - 如何把 motif 变成 graph compiler，而不是检索结果；
   - 如何让 unified substrate 原生承载这两者。

调研产物：
1. 详细文献调研与候选冻结见：`reports/rs_p0cx19_design_scout_v1.md`；
2. 该报告的主结论是：真正还可能带来根本性突破的，不是单独的 oracle、单独的 macro、单独的 motif，而是把它们做成 **同一 planner system 的三个原生层次**。

调研主结论（按三个焦点归纳）：
1. **继续做深 `CX17-C` 这类联合 substrate**（MeshA*, IGHA*, GCS, multi-query GCS）说明：
   - 新 substrate 必须明确分成：
     - viability graph
     - macro graph
     - local executable lattice；
   - query-time 应优先复用离线结构，而不是继续外挂 hook。
2. **更强的 viability→macro 闭环**（RSS 2019/2020/2023/2024 + motion primitive automata）说明：
   - viability 若仍只是 scalar 分数，只能做 activation；
   - 真正值得尝试的是把 viability 变成 **macro grammar / type system**。
3. **更强的 motif compiler**（Experience Graphs, Thunder, RSS 2024 experience-based narrow-corridor planning, compositional behavior learning）说明：
   - 经验若想真正泛化，必须从 `entry -> sequence` 升级成：
     - failure class
     - bad maneuver family
     - escape class
     - recovered basin
     之间的结构图。

统一设计约束：
1. 允许比 `CX18` 更重的系统重构，但仍须以 accepted `RS + refined CX3-D / RS-HPG` 为 frozen comparator；
2. 禁止退回到：
   - semantic token / sketch / defer；
   - 静态 schedule / allocation；
   - 常驻 successor-level heavy semantics；
3. 本轮仍以效果 ceiling 为 first-pass 目标，不以时间开销作为首要 veto；
4. public / hard-test 口径必须继续严格协议一致；
5. `mp/csm` ordinary-support audit 仍必须保持不劣；
6. 任何路线若无法解释“相比 `CX17-C`，它新增的结构 leverage 到底是什么”，应直接拒绝。

冻结候选路线（下一轮按 `CX19-A -> CX19-B -> CX19-C` 顺序执行）：

##### CX19-A：RS-VMG — Viability Macro Grammar
类型：`更强的 viability oracle -> native macro library 闭环`
核心想法：
1. 把 viability oracle 从 score 升级为 discrete viability state machine：
   - `safe_progress`
   - `recoverable_boundary`
   - `reverse_required`
   - `near_trap`
2. 每个 viability state 对应一套 native macro grammar：
   - 允许的 macro family 集
   - family 间转移规则
   - 禁止的 maneuver classes
3. planner 在线时先进入 viability state，再在对应 grammar 内扩展，而不再先算分再选 macro。
如何继承当前有效语义：
1. 继承 `CX8-D Heavy` 的高价值 reverse / setup maneuver；
2. 继承 `CX16-B` 的 viability signal；
3. 把两者通过 grammar 约束做成原生动作系统。
理论抓手：
1. viability kernel；
2. maneuver automata；
3. grammar-constrained search。
与已有工作的差异：
1. 不再是 oracle 与 macro 的弱耦合外挂；
2. 而是由 viability object 直接定义动作语言。
预期优势轴：
1. 这是当前最小、也最有希望真正完成对象闭环的路线；
2. 当前首选执行入口。

##### CX19-B：RS-MCG — Motif Compiler Graph
类型：`更强的 failure -> escape motif 编译化版本`
核心想法：
1. 把经验编译为 graph，而不是 automaton 检索器：
   - nodes：failure class / escape class / recovered basin；
   - edges：bad family -> escape family transitions；
2. 每条边同时携带：
   - expected gain
   - legality under current viability state
   - preferred macro family set；
3. planner 在线使用 motif graph 不是直接执行 prefix，而是用它来给当前 macro grammar 提供 transition prior。
如何继承当前有效语义：
1. 继承 `CX16-D / CX17-B / CX18-B` 中 failure→escape 方向的正向部分；
2. 把“经验被查到”升级为“经验进入 planner 图结构”。
理论抓手：
1. structured memory；
2. symbolic behavior graph；
3. case-based planning with abstraction transitions。
与已有工作的差异：
1. 不再是 `key -> sequence`；
2. 也不是普通 path memory；
3. 而是 graph-compiled transition prior。
预期优势轴：
1. 若 `CX19-A` 只能给出局部 gains，这条路线最有希望把 sparse positive maneuver 放大并稳定下来；
2. 但图结构设计难度更高。

##### CX19-C：RS-UGS — Unified Graph Substrate
类型：`继续做深 `CX17-C` 的 unified planner substrate`
核心想法：
1. 用统一 graph substrate 替换当前“policy 驱动的 mode 切换”：
   - viability graph
   - macro grammar graph
   - motif compiler graph
   - local executable lattice
2. 搜索流程：
   - 先在 graph substrate 上决定 viability state、macro grammar、motif transition prior；
   - 再在 local lattice 上做 executable refinement；
   - refinement 失败时反馈更新 graph state，而不是简单回退。
如何继承当前有效语义：
1. `CX17-C` 是直接前身；
2. `CX19-A/B` 提供它真正需要的原生对象。
理论抓手：
1. hierarchical graph search；
2. multi-query reusable planning graph；
3. generalized hybrid substrate / GCS-style decomposition。
与已有工作的差异：
1. 不再存在外挂 hook；
2. planner 本体本身就是 graph substrate。
预期优势轴：
1. 若 `CX19-A/B` 站住脚，这条路线最可能把当前 public ceiling 推到 hard-test ceiling；
2. 也是风险和工程量最高的路线，因此排在最后。

推荐执行顺序：
1. **先做 `CX19-A / RS-VMG`**：
   - 先验证 viability 是否能真正定义动作语法，而不再只是 activation 分数；
2. **再做 `CX19-B / RS-MCG`**：
   - 若 `A` 形成局部 ceiling，则用 compiler graph 稳定并放大 gains；
3. **最后做 `CX19-C / RS-UGS`**：
   - 只有当前两个对象都站住脚，才值得重写统一 substrate。

最低验收标准：
1. public first-pass gate：
   - `exp4 exp_delta > 0`
   - `flange exp_delta >= 0`
2. 通过后才允许消费 `rs_root_hard_v2/test`；
3. hard-test 若也维持正向，才进入下一轮 compression / deployment planning；
4. `mp/csm` ordinary-support audit 继续强制执行。

失败判据：
1. 方案本质上仍然只是更复杂的 score / gate / defer；
2. 方案无法给出：
   - 明确 viability state machine；
   - 明确 macro grammar；
   - 明确 motif compiler graph；
   - 明确 unified substrate layering；
3. 只放大开销，没有形成任何新的 public positive ceiling；
4. hard-test 出来后回头调结构或调参，违背 protocol。

本阶段结论：
1. `CX19` 要求把：
   - viability 变成动作语言的类型系统；
   - motif 变成 graph compiler；
   - substrate 变成统一 graph planner；
   做成同一系统的不同层。
2. 当前首选执行入口：`CX19-A / RS-VMG`；
3. 当前最值得作为效果放大器的 follow-up：`CX19-B / RS-MCG`；
4. 当前最终、也是最重的 backbone 路线：`CX19-C / RS-UGS`。

本轮实现结果（`2026-03-13`，对应产物：`reports/rs_p0cx19_a_pilot_v1.md`、`reports/rs_p0cx19_b_pilot_v1.md`、`reports/rs_p0cx19_c_pilot_v1.md`、`reports/rs_p0cx19_round1_summary.md`、`reports/rs_p0cx19_standard_audit_v1.md`）：
1. **统一协议**：
   - trial selection 严格只使用 `calib_hard_v1`；
   - public 仅消费 `parasol_narrow/test` 的 `exp3/exp4` 固定预算口径；
   - hard-test 仅在 public overall 转正且 `flange` 不退化时才触发；
   - `mp/csm` 继续只做 ordinary-support `build_standard_field == accepted CX3-D` audit。
2. **`CX19-A / RS-VMG`**：
   - `calib_val`：`exp_delta = -225.571`，`mean_time_overhead_ratio = 1.457471`；
   - public `exp4`：`exp_delta = -0.333`，`mean_time_overhead_ratio = 1.529468`，`flange exp_delta = 0.0`；
   - `No-Grammar` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.316913`）；
   - 读法：viability macro grammar 本身在起作用，且保住了 `flange`，但目前仍只是 `narrow_passage +5.5 / parasol_misc -4.667` 这类互相抵消的局部信号，未形成 overall 正项。
3. **`CX19-B / RS-MCG`**：
   - `calib_val`：`exp_delta = -241.429`，`mean_time_overhead_ratio = 2.049434`；
   - public `exp4`：`exp_delta = -5.222`，`mean_time_overhead_ratio = 2.155328`，`flange exp_delta = +0.4`；
   - `No-Compiler-Graph` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.323686`）；
   - 读法：motif compiler graph 比 `CX18-B` 更强地表达了经验结构，但仍然没有把 sparse positive maneuver 放大为 overall 正项，反而继续付出极高 runtime。
4. **`CX19-C / RS-UGS`**：
   - `calib_val`：`exp_delta = -241.429`，`mean_time_overhead_ratio = 2.082606`；
   - public `exp4`：`exp_delta = -1.389`，`mean_time_overhead_ratio = 2.182987`，`flange exp_delta = +1.6`；
   - `No-Unified-Graph` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.326443`）；
   - 读法：unified graph substrate 进一步强化了 `flange` 与 `narrow_passage` 的局部正项（`+1.6`、`+21.5`），但 `parasol_misc -19.833` 仍吃掉整体收益，说明更统一的 substrate 仍然会放大某些跨 family 的坏结构。
5. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx19_standard_audit_v1.md` 显示 `CX19-A/B/C` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而 round1 的结论不是 protocol drift，而是 public hard regime 上真实形成的结果。
6. **排序与 go / no-go**：
   - 当前排序：`CX19-A` > `CX19-C` > `CX19-B`；
   - 但三条路线都未满足 public positive ceiling gate：
     - `CX19-A`：最接近转正，但 overall 仍略负；
     - `CX19-B`：经验图更强但代价极高且 overall 负；
     - `CX19-C`：局部结构修复最强，但整体仍被 `parasol_misc` 负项抵消；
   - 因而本轮 **没有任何 `CX19` 分支可进入 hard-test promotion**。
7. **最终判定**：
   - `CX19` 证明：
     - viability grammar、motif compiler graph、unified graph substrate 都是正确的结构对象；
     - 但当前三条路线仍未把这些对象转化为稳定 overall gain；
   - 其中：
     - `CX19-A` 是当前最值得保留的 follow-up，因为它最接近 public 转正；
     - `CX19-B/C` 说明更强图结构继续存在局部 hard-family leverage，但仍会被跨 family 负项抵消；
   - 因而 **`CX19` 不晋升 accepted 主线**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`。

#### P0-CX20：围绕 `RS` 本体结构化升级的下一轮候选（已完成首轮实现，未晋升主线）
状态：`COMPLETED（2026-03-13：CX20-A/B/C 首轮实现与 public parasol + mp/csm audit 已完成；三条路线都通过 public positive ceiling gate，但 hard-test 全部失败）`
是否需要模型/方法修改：`是（允许直接重构 `RS` 本体表征，但仍须服务 accepted `RS + refined CX3-D / RS-HPG` 主线）`

目标：
不再把 `RS` 仅视作单一 cost-to-go 场，而是把它升级为更强的基础状态表示 / 动作语法底座 / substrate 编译器，从根上提升后续 planner system 的表达力与泛化能力。

为什么需要 `CX20`：
1. `CX3-D` 已经证明：`RS + guard` 更适合作为“受保护的保守改进分支”，而不是最终高增益主线；
2. `CX16-B` / `CX17-C` / `CX19-A` 共同说明：
   - `viability / recoverability` 是当前最有价值的附加对象之一；
   - 但只把它当成外挂 score 或 gate 不够；
3. `CX16-A` / `CX17-A` / `CX19-A` 共同说明：
   - `macro` 的动作语言方向是对的；
   - 但若 `RS` 本体不提供足够强的结构信息，macro 仍然只能是弱耦合外挂；
4. 因而下一轮应直接问：
   - `RS` 本体还能否升级为多头基础表示？
   - `RS` 能否直接输出动作语法而不是分数？
   - `RS` 能否直接编译局部 graph substrate？

冻结候选路线（下一轮按 `CX20-A -> CX20-B -> CX20-C` 顺序执行）：

##### CX20-A：RS-MVF — RS Multi-Head Value Foundation
类型：`RS 本体结构化升级`
核心想法：
1. 把当前单一 `RS cost field` 升级为多头基础场，同时输出：
   - `cost-to-go`
   - `viability / recoverability`
   - `reverse-required`
   - `trap / escape affinity`
2. 这些头不直接作为最终决策器，而是作为 planner 的统一基础状态表示。
本质变化：
1. 不再把 `RS` 当成“单张代价图”；
2. 而是把它当成 planner 的基础状态表示。
为什么值得做：
1. 这条线最直接解决当前瓶颈——`RS` 只提供“远近”，不提供“还能不能恢复”。
预期作用：
1. 给后续 `macro / motif / substrate` 提供统一底座。
风险：
1. 如果多头监督不准，容易学成互相冲突的弱表示。

##### CX20-B：RS-CMG — RS Conditional Macro Grammar
类型：`RS 动作语言编译器`
核心想法：
1. 让 `RS` 直接输出一个局部 **动作语法**，不是分数：
   - 当前状态只允许哪些 `macro family`
   - 哪些 `family` 禁止
   - 哪些需要先 `reverse-setup` 再 `forward`
2. 语法直接约束 planner 可扩展的动作语言，而不是作为外挂 bias。
本质变化：
1. 把 `RS` 从 `cost predictor` 变成 **动作语言编译器**。
为什么值得做：
1. `CX16-B` 说明 `viability` 有信号，`CX16-A` 说明 `macro` 可部署；缺的是两者真正闭环。
预期作用：
1. 把 `viability -> macro` 变成原生搜索约束，而不是外挂 bias。
风险：
1. grammar 太硬会误杀可行解，太软又会退回 tie。

##### CX20-C：RS-CSG — RS Compiled Substrate Graph
类型：`RS substrate 编译器`
核心想法：
1. 由 `RS` 离线编译一个可查询的局部图结构，节点是：
   - `viability state`
   - `failure class`
   - `escape class`
   - `recovered basin`
2. 边是：
   - `macro transition`
   - `motif prior`
3. planner 在线不再“猜”，而是查询这张由 `RS` 先编译好的 local graph substrate。
本质变化：
1. 不再让 planner 在线“猜”；
2. 而是让 `RS` 先把局部可恢复结构编译成 `graph substrate`。
为什么值得做：
1. 这是把 `CX17-C` 真正做深的方向；不是更复杂 hook，而是更强 substrate。
预期作用：
1. 最有希望把 public ceiling 推到 hard-test。
风险：
1. 工程量最大，若图结构抽象错，会高成本放大错误。

推荐执行顺序：
1. **先做 `CX20-A / RS-MVF`**：
   - 先把 `RS` 从单头 cost 场升级为结构化基础表示。
2. **再做 `CX20-B / RS-CMG`**：
   - 再验证 `RS` 是否能直接定义 macro grammar。
3. **最后做 `CX20-C / RS-CSG`**：
   - 只有当前两个对象站住脚，才值得让 `RS` 直接编译 substrate graph。

最低验收标准：
1. public first-pass gate：
   - `exp4 exp_delta > 0`
   - `flange exp_delta >= 0`
2. 若 public gate 通过，则允许消费 `rs_root_hard_v2/test`；
3. `mp/csm` ordinary-support audit 仍必须保持不劣；
4. 必须证明增益来自 `RS` 本体结构化升级，而不是单纯外挂模块。

失败判据：
1. 新方案仍只是“更复杂的 residual / gate / bias”，而没有真正升级 `RS` 本体；
2. 多头或 grammar 之间互相冲突，最终只得到 public tie 或负项；
3. compiled graph 结构无法带来任何新的 public positive ceiling；
4. 无法给出清晰的 `RS-only` / `RS+new-object` 消融拆分。

本轮实现结果（`2026-03-13`，对应产物：`reports/rs_p0cx20_a_pilot_v1.md`、`reports/rs_p0cx20_b_pilot_v1.md`、`reports/rs_p0cx20_c_pilot_v1.md`、`reports/rs_p0cx20_round1_summary.md`、`reports/rs_p0cx20_standard_audit_v1.md`）：
1. **统一协议**：
   - trial selection 严格只使用 `calib_hard_v1`；
   - public 仅消费 `parasol_narrow/test` 的 `exp3/exp4` 固定预算口径；
   - hard-test 仅在 public overall 转正且 `flange` 不退化时才触发；本轮三条路线全部触发；
   - `mp/csm` 继续只做 ordinary-support `build_standard_field == accepted CX3-D` audit。
2. **`CX20-A / RS-MVF`**：
   - `calib_val`：`exp_delta = -827.429`，`mean_time_overhead_ratio = 3.307039`；
   - public `exp4`：`exp_delta = +52.000`，`mean_time_overhead_ratio = 3.033387`，`flange exp_delta = +173.8`；
   - `No-MultiHead` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.022069`）；
   - hard-test：`exp_delta = +23.068`，但 `success_delta_pp = -1.370`，并且 `flange / narrow_passage / deadend_labyrinth` 出现明显负项；
   - 读法：多头基础场确实能把局部 hard-family ceiling 显著拉高，但它是以严重的系统性误导和成功率下降换来的，不能作为 accepted 主线。
3. **`CX20-B / RS-CMG`**：
   - `calib_val`：`exp_delta = -833.143`，`mean_time_overhead_ratio = 3.135820`；
   - public `exp4`：`exp_delta = +45.111`，`mean_time_overhead_ratio = 2.956978`，`flange exp_delta = +173.8`；
   - `No-Grammar` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.403237`）；
   - hard-test：`exp_delta = +20.411`，但 `success_delta_pp = -1.370`，并且 `flange / narrow_passage / deadend_labyrinth` 同样出现明显负项；
   - 读法：条件动作语法比纯多头场稍弱但仍有很强 public ceiling，然而 hard-test 上同样表现为“局部极强、整体不稳”，说明 grammar 本身还没有解决跨 family 误导问题。
4. **`CX20-C / RS-CSG`**：
   - `calib_val`：`exp_delta = -833.143`，`mean_time_overhead_ratio = 4.953743`；
   - public `exp4`：`exp_delta = +45.111`，`mean_time_overhead_ratio = 4.723455`，`flange exp_delta = +173.8`；
   - `No-Compiled-Graph` ablation 恢复为 public tie（`exp_delta = 0.0`，overhead `0.400413`）；
   - hard-test：`exp_delta = +20.411`，但 `success_delta_pp = -1.370`，且负项分布与 `CX20-B` 基本同构；
   - 读法：compiled substrate graph 没能比 `CX20-B` 额外提升 hard-test 稳定性，只是进一步放大了 runtime。
5. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx20_standard_audit_v1.md` 显示 `CX20-A/B/C` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而 round1 的 public/hard ceiling 不是 protocol drift，而是新系统确实在 hard-regime 上强力介入。
6. **排序与 go / no-go**：
   - 当前排序：`CX20-A` > `CX20-B` > `CX20-C`；
   - 三条路线都通过了 public positive ceiling gate；
   - 但三条路线在 hard-test 上都失败于相同模式：
     - `exp_delta` 为正；
     - `success_delta_pp` 为负；
     - 若干关键 hard families 出现明显负项；
   - 因而本轮 **没有任何 `CX20` 分支可晋升 accepted 主线**。
7. **最终判定**：
   - `CX20` 证明：
     - 直接升级 `RS` 本体，确实可以重新打出比 `CX17` 更强的 public ceiling；
     - `RS` 本体结构化升级不是错方向；
   - 但同样也证明：
     - 当前这类更强本体升级还极不稳；
     - public 上的高增益主要来自激进 hard-family 介入，而不是稳健泛化；
     - hard-test success 的下降使其无法作为 paper-facing accepted 主线；
   - 因而 **`CX20` 不晋升 accepted 主线**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`；
   - 但与 `CX18/CX19` 相比，`CX20-A` 应被视为当前最值得保留的高-ceiling `RS-core` follow-up。

#### P0-CX21：围绕 `RS-core` 一致性升级的下一轮设计调研（已完成首轮 public/mp/csm 实现，未晋升主线）
状态：`COMPLETED（2026-03-14：CX21-A/B/C 首轮实现与 public `parasol_narrow exp4` + `mp/csm` audit 已完成；CX21-B public ceiling 最强，但三条路线都未满足晋升条件）`
是否需要模型/方法修改：`是（允许继续重构 RS-core，但必须以 accepted `RS + refined CX3-D / RS-HPG` 为 frozen comparator）`

目标：
在承认 `CX20` 已证明 “直接升级 RS 本体可以打出更强 public ceiling”，但同时也承认其 hard-test failure 来自 **系统性不一致 / 过激语法 / 不稳 substrate** 的前提下，把下一轮 `RS-core` 方向收敛成更稳的三条候选：

1. **一致的基础值函数底座**，而不是彼此冲突的多头分数；
2. **带合法性语义的 macro grammar**，而不是扁平 allow/ban；
3. **稳定的 compiled substrate**，而不是更大的 prior graph。

为什么需要 `CX21`：
1. `CX20-A/B/C` 已经给出当前最强的 public positive ceiling，说明 `RS-core` 升级方向本身并没有被证伪；
2. 但三条路线都在 hard-test 上出现相同失败模式：
   - `exp_delta` 仍为正；
   - `success_delta_pp` 转负；
   - 若干关键 hard families 出现系统性误导；
3. 这说明当前问题不是 “没有价值对象”，而是：
   - `RS` 多头表征彼此不一致；
   - grammar 过早把 bias 变成过硬约束；
   - compiled graph 缺少稳定抽象与可执行边校验。

调研产物：
1. 详细文献调研与候选完善见：`reports/rs_p0cx21_design_scout_v1.md`；
2. 该报告主结论是：`RS-core` 仍然值得继续做，但必须从 `CX20` 的 “更强对象” 进一步收敛成 **consistent value foundation + legality-aware grammar + stable compiled graph**。

调研主结论（从文献到本项目的映射）：
1. **HJ / reachability / learned value field**（`DeepReach`、`ExactBC`、`PNO`、implicit safety-constraint trajectory design）说明：
   - 用户提出的 “类似 HJB/HJ reachability 的全局值函数场” 这个直觉是对的；
   - 但高维精确求解不可部署；
   - 可行路线是把这类 PDE / value-structure 变成 **可学习、带边界一致性约束的多头基础场**；
2. **motion primitive / symbolic skill / action-language**（safe-by-design motion primitives、complex action spaces、logic-skill programming）说明：
   - `macro` 真正该学的不是单个分数，而是 **合法性 / 前置关系 / 必需 reverse-setup**；
   - 否则 grammar 很容易在 hard family 上误杀可行解；
3. **experience graph / reusable substrate / graph-of-convex-sets**（Experience Graphs、Thunder、`GCS*`、multi-query GCS）说明：
   - 可复用结构确实能加速规划；
   - 但只有当它被压缩为 **高支持度、带 lower bound、并且可做局部可执行修复** 的 graph substrate 时，才有希望稳住泛化。

统一设计约束：
1. 所有 `CX21-*` 都建立在 accepted `RS + refined CX3-D / RS-HPG` 上；
2. 严禁回到 `sketch / defer / repair` 或 per-successor heavy semantics；
3. `RS-core` 输出必须优先服务：
   - `recoverability / viability`
   - `reverse-required`
   - `macro legality`
   - `stable local reuse`
   而不是重新做 family token 分类；
4. `mp/csm` 仍只允许 ordinary-support audit；
5. hard-test 仍只能在 public positive ceiling gate 明确通过后消费。

冻结候选路线（下一轮按 `CX21-A -> CX21-B -> CX21-C` 顺序执行）：

##### CX21-A：RS-CVF — RS Consistent Value Foundation
类型：`RS-core 多头基础场 / 一致性约束升级`
核心想法：
1. 把 `CX20-A` 的多头对象保留，但不再允许各头彼此松散并列；
2. `RS` 同时输出：
   - `cost-to-go`
   - `viability / recoverability`
   - `reverse-required`
   - `trap / escape affinity`
3. 并显式加入一致性约束，例如：
   - goal / obstacle boundary consistency；
   - `reverse-required` 只能在 “forward viability 下降但 recoverability 仍为正” 时激活；
   - `trap-affinity` 与 `viability` 必须保持受控反相关；
   - 可选 uncertainty / abstention 头用于抑制高风险误导。
如何吸收文献启发：
1. 用 `HJ / reachability` 的值函数结构当作监督与约束灵感，而不是在线精确求解；
2. 用 operator-learning / implicit-field 的方式提高场的一致性与空间泛化。
为什么比 `CX20-A` 更稳：
1. `CX20-A` 的问题不是“多头无用”，而是多头之间缺少结构约束；
2. `CX21-A` 的目标就是把 public 正 ceiling 从 “激进局部收益” 改造成 “较稳的基础状态表示”。
预期优势轴：
1. 降低 hard-test success collapse；
2. 为后续 grammar / substrate 提供可信底座。
主要风险：
1. 一致性约束过强会把信号压回 scalar tie；
2. 监督构造不当仍会学成彼此矛盾的弱表示。

##### CX21-B：RS-LAG — RS Legality-Aware Grammar
类型：`RS-core 动作语言 / legality compiler`
核心想法：
1. 不再让 `RS` 直接输出 macro 分数；
2. 改为输出一个带合法性语义的局部动作语法：
   - `allowed`
   - `discouraged`
   - `forbidden`
   - `must-precede(reverse-setup -> forward family)`
3. grammar 以 `CX21-A` 的 consistent value heads 为条件，而不是只看单一 cost / geometry。
如何吸收文献启发：
1. 从 motion primitives / symbolic skills 学 “动作前置条件 / 类型系统 / 组合关系”；
2. 把 `macro` 从外挂 bias 升级为局部动作语言。
为什么比 `CX20-B` 更稳：
1. `CX20-B` 过于接近 flat allow / ban；
2. `CX21-B` 只在 legality margin 与支持度都足够高时做 hard forbid；
3. 其余情形退回 `discouraged` 或 abstain，避免误杀可行解。
预期优势轴：
1. 把 `viability -> macro` 变成真正闭环；
2. 降低 `flange / deadend_labyrinth` 上的硬性误导。
主要风险：
1. grammar 若过软，仍可能退回 public tie；
2. grammar 若 calibration 不足，hard forbid 仍可能导致 success 下滑。

##### CX21-C：RS-SCG — RS Stable Compiled Graph
类型：`RS-core reusable substrate / stable compilation`
核心想法：
1. 不再把 compiled substrate 做成更大的 prior graph；
2. 只保留高支持度的局部结构节点：
   - `viability basin`
   - `failure class`
   - `escape class`
   - `recovered basin`
3. 边只记录：
   - `macro transition template`
   - `motif prior`
   - `lower bound / support`
   - `local executable refinement contract`
4. planner 在线只查询稀疏子图，并在实际采用边之前做 bounded local executable check。
如何吸收文献启发：
1. 从 Experience Graphs / Thunder 学可复用结构；
2. 从 `GCS*` / multi-query GCS 学 “离线编译 + 在线局部求解 / 查询” 的稳定接口。
为什么比 `CX20-C` 更稳：
1. `CX20-C` 的核心问题不是 graph 这个对象错，而是 graph 太激进、太稠密、缺少边级可执行性保护；
2. `CX21-C` 目标是把 reusable structure 变成 **稀疏、高支持、可验证** 的 substrate，而不是放大 prior。
预期优势轴：
1. 在保留 public ceiling 的同时，把收益从 public 推向 hard-test；
2. 真正形成 `RS` 的局部可恢复结构编译器。
主要风险：
1. 工程量最大；
2. 若抽象节点定义不对，错误会被 graph reuse 放大。

推荐执行顺序：
1. **先做 `CX21-A / RS-CVF`**：
   - 先修正 `CX20-A` 暴露出的多头不一致问题；
2. **再做 `CX21-B / RS-LAG`**：
   - grammar 只有建立在一致 value foundation 之上才值得做；
3. **最后做 `CX21-C / RS-SCG`**：
   - substrate graph 必须建立在较稳的 value + legality 对象之上，否则只会重复 `CX20-C` 的放大错误。

最低验收标准（下一轮实现沿用）：
1. public first-pass gate：
   - `exp4 exp_delta > 0`
   - `flange exp_delta >= 0`
   - 不出现明显 `success_delta_pp` 下降；
2. 若 public gate 通过，再消费 `rs_root_hard_v2/test`；
3. 必须提供：
   - `No-Consistency` / `No-Legality` / `No-Stable-Graph` 等关键消融；
   - `mp/csm` ordinary-support audit；
4. 必须证明增益来自 `RS-core` 结构升级本身，而不是协议漂移或外挂 repair。

本轮实现结果（`2026-03-14`，对应产物：`reports/rs_p0cx21_a_pilot_v1.md`、`reports/rs_p0cx21_b_pilot_v1.md`、`reports/rs_p0cx21_c_pilot_v1.md`、`reports/rs_p0cx21_round1_summary.md`、`reports/rs_p0cx21_standard_audit_v1.md`）：
1. **统一协议**：
   - 训练对象仍只使用 `calib_hard_v1/train`；
   - dev 只用于候选读数，不做 public 调参；
   - 本轮按用户要求先聚焦 `parasol_narrow exp4` 与 `mp/csm` ordinary-support，因此 **未消费 `rs_root_hard_v2/test`**；
   - `mp/csm` audit 继续要求 `build_standard_field == accepted CX3-D`。
2. **`CX21-A / RS-CVF`**：
   - `calib_val`：`success_delta_pp = -14.286`，`exp_delta = -833.143`，`mean_time_overhead_ratio = 5.338310`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +55.611`，`mean_time_overhead_ratio = 4.936051`，其中 `flange = +173.8`、`narrow_passage = +135.5`，但 `parasol_misc = -68.167`；
   - `No-Consistency` ablation 仅把 public overall 从 `+55.611` 降到 `+45.167`，说明一致性约束只带来**弱增益**，没有改变路线级行为；
   - 读法：`RS-CVF` 能保留一部分 public ceiling，但信号弱、代价极高，且没有修复跨 family 不稳。
3. **`CX21-B / RS-LAG`**：
   - `calib_val`：`success_delta_pp = -14.286`，`exp_delta = +350.143`，`mean_time_overhead_ratio = 3.379024`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +351.722`，`mean_time_overhead_ratio = 3.347043`；
   - family breakdown：`flange = +1482.6` 极强，但同时 `maze = -117.0`、`narrow_passage = -99.75`、`parasol_misc = -94.333`；
   - `No-Legality` ablation 退回到 `exp_delta = +70.833`，且 `flange` 从 `+1482.6` 掉到 `+304.4`，说明 legality-aware grammar 本身确实贡献了主要 public gain；
   - 读法：`RS-LAG` 是本轮 **最强 public ceiling**，但其收益过度集中在 `flange`，并以牺牲 `narrow_passage / maze / parasol_misc` 为代价，仍不是可晋升主线的整体增益。
4. **`CX21-C / RS-SCG`**：
   - `calib_val`：`success_delta_pp = -14.286`，`exp_delta = -723.857`，`mean_time_overhead_ratio = 4.115335`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +56.611`，`mean_time_overhead_ratio = 3.748104`，其中 `flange = +303.6`、`narrow_passage = +39.5`，但 `maze = -16.0`、`parasol_misc = -106.667`；
   - `No-Stable-Graph` ablation 与 full 结果 **几乎逐项相同**，表明当前 stable compiled graph 没有形成可观测贡献；
   - 读法：`CX21-C` 当前仍主要由 fallback grammar / field 行为支撑，graph substrate 本体未站住。
5. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx21_standard_audit_v1.md` 显示 `CX21-A/B/C` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而本轮 public 信号来自 nonholonomic branch 的新 policy，而不是 ordinary-support protocol drift。
6. **排序与 go / no-go**：
   - 当前排序：`CX21-B` > `CX21-C` > `CX21-A`；
   - `CX21-B` 是唯一值得保留的 follow-up，因为它第一次把 `RS-core legality` 明确转化成比 `CX20` 更强的 public ceiling；
   - 但三条路线都同时存在两类阻断项：
     - overhead 仍处于 `3.35x ~ 4.94x` 量级；
     - positive signal 不能 across-family 稳定保持，尤其 `CX21-B` 明显伤害 `narrow_passage / maze / parasol_misc`。
7. **最终判定**：
   - `CX21` 证明：
     - “一致 value foundation / legality-aware grammar / stable substrate” 这组对象不是空想；
     - 其中 **`CX21-B / RS-LAG` 确实重新打出了当前最强 public ceiling**；
   - 但本轮同样也证明：
     - ceiling 仍来自**高度选择性的 family leverage**，而不是稳定 overall gain；
     - `CX21-A/C` 贡献偏弱，`CX21-C` 的 graph 本体当前几乎没有独立作用；
     - `CX21-B` 的跨 family 负项与超高 overhead 已足以阻止其成为 accepted 主线；
   - 因而 **`CX21` 不晋升 accepted 主线**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`；
   - 但在 `CX20` 之后，`CX21-B` 应被视为当前最值得保留的 `RS-core grammar` follow-up。

#### P0-CX22：围绕 `CX21-B / RS-LAG` 的压缩修复与 hard-test 升级调研（已完成首轮 public/mp/csm 实现，未晋升主线）
状态：`COMPLETED（2026-03-14：CX22-A/B/C/D 首轮实现与 public `parasol_narrow exp4` + `mp/csm` audit 已完成；本轮保持 public-first，未消费 hard-test evidence）`
是否需要模型/方法修改：`是（只允许围绕 frozen `CX21-B / RS-LAG` 做压缩、稳态约束或风险控制式升级；accepted 主线保持不变）`

目标：
承认 `CX21-B` 已经是当前最强 public ceiling 分支，但同时也承认它有两类明确短板：

1. **开销过高**：`mean_time_overhead_ratio = 3.347043`；
2. **增益不稳**：`flange` 极强，但 `maze / narrow_passage / parasol_misc` 明显转负。

因此 `CX22` 不再扩展新的 `RS-core` 对象，而是把下一轮问题收敛成两条更实际的 follow-up：

1. **针对 `CX21-B` 做定向压缩 / 稳态修复**；
2. **把 frozen `CX21-B` 作为唯一候选，设计直接升级到 hard-test 的 honest protocol / safe adoption 方案**。

为什么需要 `CX22`：
1. `CX21-B` 已证明 legality-aware grammar 的对象本身是真有 leverage 的；
2. 但当前 leverage 高度集中在 `flange`，说明 grammar 仍存在明显的 over-activation / wrong-family activation；
3. 如果继续无约束扩 grammar，风险只会从 public 延续到 hard-test；
4. 因而下一轮最值得做的不是“再发明一个对象”，而是：
   - 先问能否把 `CX21-B` **压缩成更便宜、更高支持度、更窄激活域** 的版本；
   - 再问能否把 **frozen `CX21-B`** 通过高置信门控或 safe-adoption 升级到 hard-test，而不是继续 public 调参。

调研产物：
1. 详细调研与候选定义见：`reports/rs_p0cx22_design_scout_v1.md`；
2. 该报告主结论是：`CX22` 应明确分成 **Compression/Stabilization Track** 与 **Direct Hard-Test Track**，两条线各保留两个候选。

调研主结论（从文献到本项目的映射）：
1. **压缩 / 稳态修复**方向：
   - `MSVIPER`、verifiable policy extraction、safe-by-design motion primitives 共同说明：
     - 强策略对象可以被蒸馏成小树 / 有限状态控制器 / 稀疏 primitive grammar；
     - 压缩不只是省算力，也能把长尾不稳规则砍掉；
   - `Decision-Point Reinforcement Learning` 与 conformal decision rules 说明：
     - 真正该被强化的不是“所有时刻都更聪明”，而是**少量高价值 decision points**；
     - hard forbid / hard allow 应该只出现在风险受控的 decision points 上。
2. **直接 hard-test 升级**方向：
   - `CSPI-MT`、confident off-policy evaluation、sequential conformal risk control 共同说明：
     - 若目标是 honest promotion，就不应再靠多轮 public 追数；
     - 更合理的做法是：
       - 冻结候选；
       - 用 dev/public 的 lower confidence bound / risk certificate 建 promotion gate；
       - 进入 hard-test 后不再调参；
   - 这类文献支持把 `CX21-B` 从“继续调”改写成“**高置信升级或安全影子升级**”的问题。

统一设计约束：
1. 所有 `CX22-*` 都只允许建立在 frozen `CX21-B / RS-LAG` 上；
2. 严禁回到新的 `RS-core` 大发散，也严禁再发明新的 family classifier 主线；
3. 若做压缩，必须证明 `flange` 主收益尽量保留，同时至少不再继续恶化 `narrow_passage / maze / parasol_misc`；
4. 若做 direct hard-test，必须：
   - 先冻结参数；
   - 明确 hard-test 不调参；
   - 给出 honest promotion / adoption protocol；
5. `mp/csm` ordinary-support audit 仍必须保持不变。

冻结候选路线（按两条方向组织，每条方向各两案）：

##### 方向一：针对 `CX21-B` 做定向压缩 / 稳态修复

###### CX22-A：RS-LAG-SDT — Support-Distilled Tree Grammar
类型：`grammar distillation / sparse rule compiler`
核心想法：
1. 把当前 `CX21-B` 的 legality grammar 蒸馏成一个极小的 decision tree / finite-state grammar；
2. 叶节点只输出：
   - `allowed`
   - `discouraged`
   - `forbidden`
   - `must-precede`
3. 但树只允许使用少量高支持特征：
   - `viability`
   - `reverse-required`
   - `trap / escape affinity`
   - `oracle_gain`
   - support count / margin
4. 对低支持叶统一回退 accepted baseline，不再让长尾 rules 常驻在线。
为什么值得做：
1. `CX21-B` 的主问题之一是 grammar 太“宽”、太常驻；
2. 蒸馏成小树 / 小型 FSC 后，既能降 runtime，又能把长尾误规则显式砍掉。
理论抓手：
1. `MSVIPER` 类 decision-tree distillation；
2. verifiable policy extraction / FSC compression；
3. safe-by-design primitive grammar。
预期优势：
1. runtime 从当前 `3.35x` 明显下压；
2. `flange` gain 尽量保留；
3. 通过叶剪枝减少 `maze / narrow_passage / parasol_misc` 的误触发。
主要风险：
1. 过度蒸馏会把 `flange` gain 一起压平；
2. 若 tree 仍需太多叶子，说明 `CX21-B` 的规则本身还没形成可压缩结构。

###### CX22-B：RS-LAG-DCG — Decision-Point Conformal Grammar
类型：`sparse activation / risk-controlled legality`
核心想法：
1. 不先压缩 grammar 本体，而是压缩 **激活域**：
   - 只有在 dev 统计出的高价值 decision points 才允许 grammar 介入；
   - 其余节点完全回退 accepted baseline；
2. 对每次 hard forbid / must-precede 决策引入 conformal / risk threshold：
   - 高支持且风险证书通过 → `forbidden`
   - 中支持 → `discouraged`
   - 低支持 → abstain / baseline
3. 换句话说，grammar 本体保留，但把“何时敢用硬规则”做成风险控制问题。
为什么值得做：
1. `CX21-B` 的 public gain 明显来自少量强 decision points；
2. 真正该压的不是 grammar 逻辑本身，而是它的激活频率与硬动作强度。
理论抓手：
1. decision-point RL / sparse policy intervention；
2. conformal decision rules / sequential risk control。
预期优势：
1. 比 `CX22-A` 更少损伤 `flange` gain；
2. 更直接修复 `narrow_passage / maze / parasol_misc` 的误激活；
3. overhead 通过“只在少量决策点介入”而下降。
主要风险：
1. 若 decision-point 定义不对，会再次滑向“过度 abstain”；
2. conformal gate 太保守会把 grammar gain 再次抹平。

##### 方向二：把 frozen `CX21-B` 直接单独升级到 hard-test

###### CX22-C：RS-LAG-HPG — High-Confidence Promotion Gate
类型：`frozen branch promotion protocol`
核心想法：
1. 彻底冻结当前 `CX21-B` 参数与激活逻辑；
2. 不再继续 public 追数，而是构造一个一次性的 hard-test promotion gate：
   - 用 dev/public 的 family-wise lower confidence bound；
   - 加上 negative-family penalty；
   - 加上 runtime penalty；
3. 只有 gate 通过，才允许整支 `CX21-B` 全量进入 hard-test；
4. 进入 hard-test 后禁止任何回调调参。
为什么值得做：
1. 若 `CX21-B` 真的代表新的 ceiling，就应接受更严格、一次性的升级 protocol；
2. 这能把“继续调 until 过拟合 public”与“honest promotion”彻底分开。
理论抓手：
1. safe policy improvement with confidence bounds；
2. multiple testing / candidate screening；
3. sequential risk control。
预期优势：
1. 给 `CX21-B` 一个明确、可复现、paper-facing 的 go/no-go 机制；
2. 防止又回到多轮 public 调参。
主要风险：
1. 这条线本身不修方法，可能只是更快证明 `CX21-B` 不稳；
2. 若 gate 设计不当，容易过松或过严。

###### CX22-D：RS-LAG-SHA — Shadow Hard-Test Adoption
类型：`frozen branch / instance-specific safe adoption`
核心想法：
1. 同样冻结 `CX21-B`；
2. 但进入 hard-test 时不直接整支替换 accepted 主线，而是采用 **shadow adoption**：
   - accepted `CX3-D` 仍作为默认 driver；
   - `CX21-B` 只在 dev 校准为高置信正收益的 intervention class 上获得 adoption 权；
   - adoption 依据可以是：
     - decision-point class
     - grammar leaf
     - macro family
     - lower-confidence-bound positive tag
3. 未通过 class gate 的干预全部回退 baseline。
为什么值得做：
1. 这是“直接进入 hard-test”里风险更低的一种；
2. 它回答的不是“整个 `CX21-B` 能不能过”，而是“`CX21-B` 的哪些高支持干预在 hard-test 上仍然成立”。
理论抓手：
1. confident off-policy evaluation / lower-confidence adoption；
2. conservative / safe policy improvement；
3. instance-specific defer / safe fallback，但对象是 **frozen grammar class** 而不是重新学 defer head。
预期优势：
1. 有机会保住 `flange` 这类强收益；
2. 把 `maze / narrow_passage / parasol_misc` 的长尾风险压回 baseline；
3. 为后续是否继续做 `CX21-B` 给出更干净的 hard-test 证据。
主要风险：
1. adoption class 若过粗，仍会把负项带上 hard-test；
2. adoption class 若过细，可能退化成几乎不用 `CX21-B`。

推荐执行顺序：
1. **主推 `CX22-A -> CX22-B`**：
   - 先回答 `CX21-B` 能否被压缩成更便宜、更稳的 grammar；
2. **若用户更关心 ceiling 的 honest 判定，则走 `CX22-D -> CX22-C`**：
   - 先做影子 adoption 式 hard-test；
   - 若结果仍有明确正向 class，再考虑整支 promotion gate。

最低验收标准：
1. 若走压缩 / 稳态修复线：
   - runtime 必须较 `CX21-B` 有明确下降；
   - `flange` 不得被完全压平；
   - `narrow_passage / maze / parasol_misc` 至少有一项明显修复。
2. 若走 direct hard-test 线：
   - 参数必须完全冻结；
   - hard-test 后不得回调调参；
   - 必须如实记录 promotion gate / adoption gate 通过与否。
3. 所有 `CX22-*` 仍需维持 `mp/csm` ordinary-support audit。

本轮实现结果（`2026-03-14`，对应产物：`reports/rs_p0cx22_a_pilot_v1.md`、`reports/rs_p0cx22_b_pilot_v1.md`、`reports/rs_p0cx22_c_pilot_v1.md`、`reports/rs_p0cx22_d_pilot_v1.md`、`reports/rs_p0cx22_round1_summary.md`、`reports/rs_p0cx22_standard_audit_v1.md`）：
1. **统一协议**：
   - 训练对象仍只使用 `calib_hard_v1/train`；
   - dev 只用于候选读数，不做 public 调参；
   - 本轮按用户要求先聚焦 `parasol_narrow exp4` 与 `mp/csm` ordinary-support，因此 **未消费 `rs_root_hard_v2/test`**；
   - `mp/csm` audit 继续要求 `build_standard_field == accepted CX3-D`。
2. **`CX22-A / RS-LAG-SDT`**：
   - `calib_val`：`success_delta_pp = -14.286`，`exp_delta = +309.429`，`mean_time_overhead_ratio = 3.448779`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +333.778`，`mean_time_overhead_ratio = 3.230091`；
   - family breakdown：`flange = +1484.0`，但 `maze = -117.0`、`narrow_passage = -106.5`、`parasol_misc = -144.833`；
   - `No-Tree` ablation 反而更强（`exp_delta = +351.722`），说明当前 tree distillation 没有形成有效压缩，反而轻微伤害了有用 signal。
3. **`CX22-B / RS-LAG-DCG`**：
   - `calib_val`：`success_delta_pp = 0.0`，`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.694672`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.701371`；
   - `No-Decision-Gate` ablation 直接恢复到 `exp_delta = +336.667` / `overhead = 3.253864`，说明 decision-point gate 的确强力压住了 runtime 与负 family，但也把正向 grammar signal 一并抹平；
   - 读法：这是一次**有效压缩但无效果**的修复。
4. **`CX22-C / RS-LAG-HPG`**：
   - `calib_val`：chosen branch 收缩到 `success_delta_pp = 0.0`，`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.013149`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = 0.0`，`mean_time_overhead_ratio = 0.000388`；
   - `No-Episode-Gate` ablation 恢复到 `exp_delta = +351.722` / `overhead = 3.220611`；
   - 读法：episode-level promotion gate 过于保守，几乎把整支 `CX21-B` 退回 baseline。
5. **`CX22-D / RS-LAG-SHA`**：
   - `calib_val`：`success_delta_pp = -14.286`，`exp_delta = +471.571`，`mean_time_overhead_ratio = 2.598582`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +326.333`，`mean_time_overhead_ratio = 2.647250`；
   - family breakdown：`flange = +1424.0`，同时 `maze = -113.0`、`narrow_passage = -87.75`、`parasol_misc = -130.333`；
   - `No-Class-Gate` ablation 回到 `exp_delta = +351.722` / `overhead = 3.215779`，说明 shadow adoption 确实**保留了大部分 `flange` gain 并降低了 runtime**，但没有修复跨 family 负项。
6. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx22_standard_audit_v1.md` 显示 `CX22-A/B/C/D` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而本轮 public 读数来自 nonholonomic branch 的新 policy，而不是 ordinary-support drift。
7. **排序与 go / no-go**：
   - 当前排序：`CX22-A` > `CX22-D` > `CX22-B` > `CX22-C`（按 public `exp4` ceiling）；
   - 其中：
     - `CX22-A` ceiling 最高，但压缩失败；
     - `CX22-D` 是最像“稳态修复”的版本，保住了多数 `flange` gain 并把 overhead 从 `3.216x` 压到 `2.647x`；
     - `CX22-B/C` 证明更强 gate 的代价就是直接退回 baseline-like tie。
8. **最终判定**：
   - `CX22` 证明：
     - `CX21-B` 的 signal 可以被压缩或门控；
     - 其中 `CX22-D` 的 shadow adoption 是当前最有价值的 repair object；
   - 但本轮同样也证明：
     - 现有压缩/门控仍无法把 `maze / narrow_passage / parasol_misc` 的负项消掉；
     - 所有 surviving branches 的 overhead 仍显著高于部署目标；
     - 最稳的压缩路线（`CX22-B/C`）已经退化成 tie baseline。
   - 因而 **`CX22` 不晋升 accepted 主线**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`；
   - 但在 `CX21-B` 之后，`CX22-D / RS-LAG-SHA` 应被视为当前最值得保留的 grammar repair follow-up。

#### P0-CX23：围绕 `CX22-D / RS-LAG-SHA` 的结构性修复设计调研（已完成首轮 public/mp/csm 实现，未晋升主线）
状态：`COMPLETED（2026-03-14：CX23-A/B/C/D 首轮实现与 public `parasol_narrow exp4` + `mp/csm` audit 已完成；`CX23-C` 表现最强，但四条路线都未晋升主线）`
是否需要模型/方法修改：`是（允许围绕 `CX22-D` 做 teacher distillation、contrastive debias、时序 automaton、counterfactual editor 等结构升级；accepted 主线保持不变）`

目标：
围绕 `CX22-D / RS-LAG-SHA` 做下一轮真正可单独陈述为创新点的修复，而不是继续做参数小修。核心要求是：

1. 尽量保住 `flange` 主收益；
2. 系统性消减 `maze / narrow_passage / parasol_misc` 负项；
3. 让修复对象本身能被明确写成方法贡献，而不是“再调一轮 gate”。

为什么需要 `CX23`：
1. `CX22-D` 已经是当前最像“有效修复”的分支：
   - 保住了大部分 `flange` gain；
   - 相对 `CX21-B` 明显压低 runtime；
2. 但它仍然有两个路线级问题：
   - adoption class 仍过粗，导致 `maze / narrow_passage / parasol_misc` 负项残留；
   - 当前修复更多像“门控工程”，还不足以被单独陈述为 paper-facing innovation；
3. 因而下一轮不应再围绕 `min_hits / lcb_q / threshold` 之类参数微调，而应把 `CX22-D` 升级为：
   - **可蒸馏**
   - **可编译**
   - **可解释**
   - **可做负迁移消减**
   的结构对象。

调研产物：
1. 详细候选设计见：`reports/rs_p0cx23_design_scout_v1.md`；
2. 该报告主结论是：`CX22-D` 最值得继续，但后续必须转向 **teacher distillation / contrastive debias / temporal automaton / counterfactual class editor** 这类可独立陈述的方法对象。

统一设计约束：
1. 所有 `CX23-*` 都建立在 frozen `CX22-D / RS-LAG-SHA` 上；
2. 严禁退回纯参数微调；
3. 必须明确回答：
   - 创新对象是什么；
   - 它如何比 `CX22-D` 更细粒度地区分 `flange` 正项与其他 family 负项；
   - 为什么它不是单纯换一个 threshold；
4. `mp/csm` ordinary-support audit 仍必须保持不变；
5. 若后续进入 hard-test，仍须遵守 frozen-params / no-retune 原则。

冻结候选路线（建议按 `CX23-A -> CX23-B -> CX23-C -> CX23-D` 顺序执行）：

##### CX23-A：RS-SAD — Shadow Adoption Distillation
类型：`teacher distillation / compressed adoption policy`
核心想法：
1. 把 `CX22-D` 当前的 class-adoption 逻辑蒸馏成一个小型、可解释的 adoption student：
   - 输入：`CX22-D` 的 episode / class features；
   - 输出：是否 adoption、采用哪种 adoption class、是否回退 baseline；
2. 蒸馏对象不是原始 grammar，而是 **shadow adoption behavior** 本身；
3. student 允许采用：
   - small tree ensemble
   - finite-state controller
   - tiny MLP + distilled rule table
   之一，但必须能解释其 decision region。
创新点：
1. 把 “高 ceiling 但粗糙的 shadow adoption teacher” 压缩成 **可部署的蒸馏 adoption policy**；
2. 创新对象是 adoption-layer distillation，而不是普通 grammar 剪枝。
预期优势：
1. runtime 进一步下降；
2. 通过蒸馏剪掉长尾 class，减少 `maze / narrow_passage / parasol_misc` 误收纳；
3. 更容易 paper-facing 地陈述为独立方法。
主要风险：
1. 蒸馏若只学到 coarse imitation，会把 `flange` gain 一并削弱；
2. 若 teacher 本身类别结构不清，student 只会复制其偏差。

##### CX23-B：RS-CAD — Contrastive Adoption Debias
类型：`positive-vs-negative class separation / contrastive editor`
核心想法：
1. 不直接学习 “该不该 adoption”，而是学习：
   - 哪些 class 是 **positive-support classes**（保 `flange`）；
   - 哪些是 **negative-transfer classes**（伤 `maze / narrow_passage / parasol_misc`）；
2. 用 contrastive / metric learning 或 signed adoption head 把两类显式拉开；
3. 最终输出不是单一 gate，而是：
   - `promote`
   - `suppress`
   - `abstain`
   三态 adoption decision。
创新点：
1. 这是对 `CX22-D` 的 **负迁移显式建模**；
2. 不再让负项只通过阈值被动压制，而是把 “bad adoption class” 当一等对象。
预期优势：
1. 更有机会专门修 `maze / narrow_passage / parasol_misc`；
2. 相比 `CX23-A`，它更直接对准 “为什么 class gate 仍放进坏类”。
主要风险：
1. 若正负 class 本身高度重叠，contrastive separation 会不稳定；
2. 过强 suppressor 可能重新走回过度保守。

##### CX23-C：RS-HAA — Hierarchical Adoption Automaton
类型：`temporal logic / automaton over adoption states`
核心想法：
1. 让 `CX22-D` 的 adoption 不再是静态 class gate；
2. 引入分层 automaton：
   - `observe`
   - `candidate`
   - `commit`
   - `suppress`
   - `recover`
3. 只有当一段短时序证据持续成立，才从 `candidate` 进入 `commit`；
4. 一旦出现负迁移迹象，则强制切回 `recover` / baseline。
创新点：
1. 把 adoption 从静态 one-shot class decision 升级为 **时序状态机对象**；
2. 这能单独陈述为 “temporal adoption automaton”。
预期优势：
1. 通过短时序一致性过滤掉偶发误激活；
2. 更有希望减少 `maze / narrow_passage` 中早期误 commit。
主要风险：
1. 状态机过慢会丢掉短窗口 `flange` gain；
2. 若状态定义不对，会只引入额外复杂度。

##### CX23-D：RS-CCE — Counterfactual Class Editor
类型：`offline counterfactual repair / class-level editor`
核心想法：
1. 基于 `CX22-D` 的 public/dev 轨迹，离线构造 class-level counterfactual pairs：
   - adopt vs no-adopt
   - adopted class vs neighboring suppressed class
2. 学一个轻量 editor：
   - 输入当前 adoption class / local context；
   - 输出是否替换为更安全的 sibling class、是否改为 abstain、是否降级为 soft adoption；
3. editor 只在被识别为高风险 class 时介入。
创新点：
1. 这是 **counterfactual class repair**，不是普通规则门控；
2. 它能单独回答 “如果当时不采用这个 class，会不会更好？”。
预期优势：
1. 更细粒度修复坏 class；
2. 与 `CX23-B` 相比，它更偏编辑而不是分离。
主要风险：
1. counterfactual 估计若不稳，editor 会学到噪声；
2. 数据管道较重，实现复杂度最高。

推荐执行顺序：
1. **首选 `CX23-A / RS-SAD`**：
   - 最容易形成独立创新点，也最直接承接 `CX22-D`；
2. **其次 `CX23-B / RS-CAD`**：
   - 若主要问题是负迁移 class 残留，contrastive debias 最对症；
3. **再做 `CX23-C / RS-HAA`**：
   - 当确认静态 class 仍不足时，再引入时序 automaton；
4. **最后 `CX23-D / RS-CCE`**：
   - 工程量最大，但若前面都不够，这条线最像真正的离线修复器。

最低验收标准：
1. 相对 `CX22-D`：
   - runtime 不能显著回弹到 `CX21-B` 量级；
   - `flange` gain 尽量保留；
   - `maze / narrow_passage / parasol_misc` 至少一项明显修复；
2. 方法必须能被单独陈述为创新点，而不是“又调了一版 gate”；
3. `mp/csm` ordinary-support audit 继续全量通过。

本轮实现结果（`2026-03-14`，对应产物：`reports/rs_p0cx23_a_pilot_v1.md`、`reports/rs_p0cx23_b_pilot_v1.md`、`reports/rs_p0cx23_c_pilot_v1.md`、`reports/rs_p0cx23_d_pilot_v1.md`、`reports/rs_p0cx23_round1_summary.md`、`reports/rs_p0cx23_standard_audit_v1.md`）：
1. **统一协议**：
   - 训练对象仍只使用 `calib_hard_v1/train`；
   - dev 只用于候选读数，不做 public 调参；
   - 本轮继续按用户要求先聚焦 `parasol_narrow exp4` 与 `mp/csm` ordinary-support，因此 **未消费 `rs_root_hard_v2/test`**；
   - `mp/csm` audit 继续要求 `build_standard_field == accepted CX3-D`。
2. **`CX23-A / RS-SAD`**：
   - `calib_val`：`success_delta_pp = -14.286`，`exp_delta = +510.857`，`mean_time_overhead_ratio = 1.520833`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +340.500`，`mean_time_overhead_ratio = 1.686486`；
   - family breakdown：`flange = +1421.4`，`narrow_passage = -88.0`，`maze = -113.0`，`parasol_misc = -85.5`；
   - `No-Distill` ablation 回落到 `exp_delta = +326.333`，且 `parasol_misc` 更差到 `-130.333`；
   - 读法：distillation 确实带来可观测增益，尤其修复了 `parasol_misc`，但仍没消掉 `maze / narrow_passage` 负项。
3. **`CX23-B / RS-CAD`**：
   - `calib_val`：`success_delta_pp = -14.286`，`exp_delta = +471.571`，`mean_time_overhead_ratio = 1.546203`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +326.333`，`mean_time_overhead_ratio = 1.580398`；
   - `No-Contrastive` ablation 与 full 几乎同构，说明当前 contrastive debias 没形成新 leverage。
4. **`CX23-C / RS-HAA`**：
   - `calib_val`：`success_delta_pp = -14.286`，`exp_delta = +1218.571`，`mean_time_overhead_ratio = 1.297095`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +392.889`，`mean_time_overhead_ratio = 1.359640`；
   - family breakdown：`flange = +1428.4`，`narrow_passage = +98.25`，`parasol_misc = -58.333`，`maze = -113.0`；
   - `No-Automaton` ablation 只有 `exp_delta = +326.333`，且 `narrow_passage` 回落到 `-87.75`；
   - 读法：时序 automaton 是本轮 **唯一同时保住 flange 且把 narrow_passage 从负转正** 的对象，也是当前最强 `CX23` 分支。
5. **`CX23-D / RS-CCE`**：
   - `calib_val`：`success_delta_pp = -14.286`，`exp_delta = +471.571`，`mean_time_overhead_ratio = 1.506056`；
   - public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +326.333`，`mean_time_overhead_ratio = 1.544657`；
   - `No-Editor` ablation 与 full 几乎等价，说明当前 counterfactual class editor 还没有学到有效编辑。
6. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx23_standard_audit_v1.md` 显示 `CX23-A/B/C/D` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而本轮信号来自 nonholonomic branch 的新 policy，而不是 ordinary-support drift。
7. **排序与 go / no-go**：
   - 当前排序：`CX23-C` > `CX23-A` > `CX23-D` > `CX23-B`；
   - `CX23-C` 是本轮最有价值的 follow-up，因为它首次在保住 `flange` 的同时，把 `narrow_passage` 明确修成正项，并把 overhead 压到 `1.36x`；
   - 但 `maze = -113.0` 与 `parasol_misc = -58.333` 仍然阻止它成为稳定 overall gain 分支。
8. **最终判定**：
   - `CX23` 证明：
     - 围绕 `CX22-D` 做真正的结构创新是有价值的；
     - 其中 **`CX23-C / RS-HAA` 的时序 automaton** 是当前最有希望继续做深的 repair object；
   - 但本轮同样也证明：
     - `CX23-A/B/D` 尚未打开新优势区间；
     - 即使是最强的 `CX23-C`，也仍未消除 `maze / parasol_misc` 负项；
     - 所有 surviving branches 的 runtime 仍高于部署目标。
   - 因而 **`CX23` 不晋升 accepted 主线**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`；
   - 但在 `CX22-D` 之后，`CX23-C / RS-HAA` 应被视为当前最值得保留的 structural repair follow-up。

#### P0-CX24：围绕 `CX23-C / RS-HAA` 的跨 family 稳态修复设计调研（已完成首轮 public/mp/csm 实现，未晋升主线）
状态：`COMPLETED（2026-03-14：CX24-E/A/D/B/C 首轮实现与 public `parasol_narrow exp4` + `mp/csm` audit 已完成；无分支晋升主线）`
是否需要模型/方法修改：`是（允许围绕 `CX23-C` 做拓扑/陷阱见证、tail-aware abstention、group-robust automaton、counterfactual commit certificate 与诊断平面升级；accepted 主线保持不变）`

目标：
围绕 `CX23-C / RS-HAA` 继续做下一轮真正结构性的改进，针对以下 5 个已明确的问题逐一给出方法对象，而不是继续做参数细调：

1. `maze` 仍显著负项；
2. `parasol_misc` 仍为负；
3. 整体仍非 across-family 稳定增益；
4. 时序证据可能被欺骗；
5. 缺少可诊断证据。

为什么需要 `CX24`：
1. `CX23-C` 已经是当前最强 structural repair 分支：
   - public `exp4 = +392.889`
   - `flange = +1428.4`
   - `narrow_passage = +98.25`
2. 但它仍存在路线级阻断：
   - `maze = -113.0`
   - `parasol_misc = -58.333`
   - overhead `1.359640x`
3. 更关键的是，`CX23-C` 暴露出“时序 automaton 可能把错误证据越积越强”的结构问题；
4. 因而下一轮必须从：
   - trap/topology witness
   - tail-aware abstention
   - worst-group robustness
   - counterfactual commit verification
   - trace observability
   这五个方向系统补强。

调研产物：
1. 详细设计见：`reports/rs_p0cx24_design_scout_v1.md`；
2. 该报告主结论是：`CX23-C` 值得继续，但后续不能只加更长记忆，而必须把 automaton 升级为 **带陷阱见证、尾部支持控制、反事实 commit 证书、组稳健训练目标和完整诊断平面** 的系统。

统一设计约束：
1. 所有 `CX24-*` 都建立在 frozen `CX23-C / RS-HAA` 上；
2. 严禁继续做纯参数微调；
3. 每条方案都必须能单独陈述为方法贡献；
4. 任何改动都必须继续通过 `mp/csm` ordinary-support audit；
5. 若后续进入 hard-test，仍须遵守 frozen-params / no-retune 原则。

冻结候选路线（针对 5 个问题一一对应，建议按 `CX24-E -> CX24-A -> CX24-D -> CX24-B -> CX24-C` 顺序执行）：

##### CX24-A：RS-MTW — Maze Trap Witness Automaton
类型：`topology / depression witness`
针对问题：
1. `maze` 仍显著负项；
2. 时序证据在 maze 中可能强化错误信号。
核心想法：
1. 在 `RS-HAA` 的时序 automaton 之外，引入一个 **maze trap witness**：
   - heuristic depression indicator；
   - dead-end / no-exit witness；
   - topological escape witness；
2. 只有当 automaton 的 `commit` 证据与 trap witness 一致时，才允许 commit；
3. 若 witness 显示当前更像循环 basin / trap，则强制 suppress 或切回 recovery。
创新点：
1. 把时序 automaton 与 trap/topology witness 做 product-state；
2. commit 不再只依赖短时序一致性，而要依赖“是否存在可验证的逃逸结构”。
预期优势：
1. 最直接对准 `maze = -113.0`；
2. 减少被重复局部模式欺骗而错误 commit。
主要风险：
1. witness 若太保守，可能把 `flange` / `narrow_passage` gain 一起压掉；
2. topological proxy 提取若过粗，可能只增加复杂度而不提升区分度。

##### CX24-B：RS-TAS — Tail-Aware Abstention Shield
类型：`long-tail support / minority-aware abstention`
针对问题：
1. `parasol_misc` 仍为负；
2. 长尾杂项场景误 commit 尚未压住。
核心想法：
1. 为 automaton 的 `commit` 增加 **tail-aware support gate**：
   - rare-state density；
   - support radius；
   - tail-aware conformal threshold；
2. 对头部高支持状态保持原有 commit；
3. 对尾部/稀有状态优先：
   - abstain
   - soften commit
   - fallback baseline
创新点：
1. 不是普通 OOD 检测，而是把 **minority-tail coverage** 直接写进 automaton commit policy；
2. 专门针对 `parasol_misc` 这类长尾误迁移。
预期优势：
1. 最直接修复 `parasol_misc = -58.333`；
2. 相比通用 abstention，更少损伤 head families。
主要风险：
1. 若 tail detector 过严，会重新把系统压成保守 tie；
2. 若 tail/head 划分不稳定，会引入额外噪声。

##### CX24-C：RS-GRA — Group-Robust Automaton
类型：`worst-group / across-family robust objective`
针对问题：
1. 整体仍非 across-family 稳定增益。
核心想法：
1. 不再只按平均 `exp_delta` 选择 automaton；
2. 引入 **group-robust selection / training objective**：
   - explicit family groups if allowed by protocol；
   - 或 hidden group / cluster prototypes if not；
3. 优化目标改为：
   - worst-group regret
   - group-adjusted score
   - average + worst-group tradeoff
4. 让 automaton 在设计期就对“单 family 极强、其他 family 吃亏”施加惩罚。
创新点：
1. 把 automaton 升级成 **group-robust automaton**；
2. 不是事后分析 worst-family，而是把 across-family stability 变成显式优化对象。
预期优势：
1. 为真正主线晋升提供更对口的目标；
2. 有机会抑制只靠 `flange` 单 family 支撑的虚高 ceiling。
主要风险：
1. group-robust 目标过强时，可能牺牲所有正向 leverage；
2. 若 latent groups 定义不好，会把优化变得不稳定。

##### CX24-D：RS-CCC — Counterfactual Commit Certificate
类型：`bounded local review / counterfactual verification`
针对问题：
1. 时序证据可能被欺骗。
核心想法：
1. 在 `commit` 前做一次 bounded local counterfactual review：
   - commit current class
   - abstain / baseline
   - sibling class
2. 只有当前 class 在短滚动/局部 search proxy 上有明确优势，才发放 commit certificate；
3. 否则保持 `candidate` 或退回 `recover`。
创新点：
1. commit 前加入 **counterfactual certificate**，不是单靠观测序列自我强化；
2. 把“如果此刻不 commit 会怎样”变成在线可检查对象。
预期优势：
1. 对抗时序假阳性；
2. 最可能与 `CX24-A` 形成互补。
主要风险：
1. local review 若过重，会推高 runtime；
2. short-horizon counterfactual 若不准，会误杀真实正项。

##### CX24-E：RS-ATO — Adoption Trace Observatory
类型：`diagnostic plane / trace observability`
针对问题：
1. 缺少可诊断证据。
核心想法：
1. 为 `RS-HAA` 增加专门的 observability plane：
   - state occupancy；
   - transition matrix；
   - commit / suppress / recover counts；
   - false-commit trace slices；
   - family-conditioned error ledger；
2. 输出 automaton state proportion、transition hot spots、误触发轨迹切片与反事实对照；
3. 作为后续所有 `CX24-*` 的 mandatory instrumentation。
创新点：
1. 不是普通日志，而是 **automaton-specific failure forensics plane**；
2. 让后续修复不再盲目依赖 aggregate metrics。
预期优势：
1. 直接提升可诊断性；
2. 为 `CX24-A/B/D` 提供对症数据对象。
主要风险：
1. 本身不直接改善 public 分数；
2. 若 trace schema 设计不对，仍可能信息噪声很大。

推荐执行顺序：
1. **先做 `CX24-E / RS-ATO`**：
   - 先补齐诊断平面，否则 `maze / misc` 仍难以对症；
2. **再做 `CX24-A / RS-MTW`**：
   - 先修 `maze` 与被骗 commit；
3. **再做 `CX24-D / RS-CCC`**：
   - 用反事实证书补强 commit；
4. **然后做 `CX24-B / RS-TAS`**：
   - 专门压 `parasol_misc` 长尾误迁移；
5. **最后做 `CX24-C / RS-GRA`**：
   - 在已有修复对象之上，再做 across-family 稳态约束。

最低验收标准：
1. 相对 `CX23-C`：
   - `maze` 必须较 `-113.0` 明显改善；
   - `parasol_misc` 必须较 `-58.333` 明显改善；
   - `flange` 不得被完全压平；
   - `narrow_passage` 不得重新回负；
2. 任一方案都必须能被单独陈述为创新点；
3. `mp/csm` ordinary-support audit 继续全量通过。

本轮实现结果（`2026-03-14`，对应产物：`reports/rs_p0cx24_e_pilot_v1.md`、`reports/rs_p0cx24_a_pilot_v1.md`、`reports/rs_p0cx24_d_pilot_v1.md`、`reports/rs_p0cx24_b_pilot_v1.md`、`reports/rs_p0cx24_c_pilot_v1.md`、`reports/rs_p0cx24_round1_summary.md`、`reports/rs_p0cx24_standard_audit_v1.md`）：
1. **统一协议**：
   - 训练对象仍只使用 `calib_hard_v1/train`；
   - dev 只用于候选读数，不做 public 调参；
   - 本轮继续按用户要求先聚焦 `parasol_narrow exp4` 与 `mp/csm` ordinary-support，因此 **未消费 `rs_root_hard_v2/test`**；
   - `mp/csm` audit 继续要求 `build_standard_field == accepted CX3-D`。
2. **`CX24-E / RS-ATO`**：
   - public `exp4 = +392.889`，overhead `1.390389`，与 `CX23-C` 基本同口径；
   - 额外产出 `diagnostic_rows.csv` 并汇总出 automaton state counts：`candidate/commit/recover/observe`，为后续修复提供可诊断证据；
   - 读法：`CX24-E` 主要补齐 observability plane，而不是直接改善行为。
3. **`CX24-A / RS-MTW`**：
   - public `exp4 = +392.889`，overhead `1.528259`；
   - `No-Trap-Witness` ablation 与 full 近乎同构，`maze` 仍是 `-113.0`；
   - 读法：当前 maze trap witness 没有学到有效 suppressor。
4. **`CX24-D / RS-CCC`**：
   - public `exp4 = +61.444`，overhead `1.728946`；
   - family breakdown：`maze = 0.0`（相对 `CX23-C` 明显修复），`narrow_passage = +104.5`，但 `flange` 从 `+1428.4` 大幅掉到 `+218.0`，`parasol_misc = -66.667`；
   - `No-Certificate` ablation 恢复到 `exp4 = +392.889`；
   - 读法：counterfactual commit certificate 成功压住了错误 commit，但过度保守，牺牲了核心正项。
5. **`CX24-B / RS-TAS`**：
   - public `exp4 = +392.889`，overhead `1.447765`；
   - `No-Tail-Shield` 与 full 几乎等价，`parasol_misc` 仍是 `-58.333`；
   - 读法：当前 tail-aware shield 没有形成实质作用。
6. **`CX24-C / RS-GRA`**：
   - public `exp4 = +392.889`，overhead `1.418766`；
   - `No-Group-Robust` 与 full 几乎同构，group-robust penalty 还没有改变 automaton 行为；
   - 读法：当前 worst-group 约束只是名义存在，没有形成有效家族平衡。
7. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx24_standard_audit_v1.md` 显示 `CX24-E/A/D/B/C` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而本轮所有变化都来自 nonholonomic policy logic，而不是 ordinary-support drift。
8. **排序与 go / no-go**：
   - 当前排序：`CX24-C` ≈ `CX24-E` ≈ `CX24-B` ≈ `CX24-A` > `CX24-D`（按 public ceiling）；
   - 若按“有无新行为信号”排序，则 `CX24-D` 与 `CX24-E` 最有价值：
     - `CX24-E` 给出后续修复所需的 observability plane；
     - `CX24-D` 证明 counterfactual certificate 能修掉 `maze`，只是当前代价过高。
9. **最终判定**：
   - `CX24` 证明：
     - `RS-HAA` 确实还可以沿“诊断平面 + commit 证书”方向继续推进；
     - 其中 `CX24-D / RS-CCC` 是当前唯一对 `maze` 负项产生实质修复的对象；
   - 但本轮同样也证明：
     - `CX24-A/B/C` 还没有形成可观测增益；
     - `CX24-D` 为修 `maze` 付出了不可接受的 `flange` 损失；
     - `parasol_misc` 仍未被真正解决。
   - 因而 **`CX24` 不晋升 accepted 主线**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`；
   - 但在 `CX23-C` 之后，最值得继续保留的 follow-up 变为：
     - `CX24-E / RS-ATO` 作为诊断平面；
     - `CX24-D / RS-CCC` 作为可继续校正的 commit repair 对象。

#### P0-CX25 Design Freeze：围绕 `CX24-E + CX24-D` 的证书校正与长尾稳态修复设计调研（归档）
状态：`SCOUTED（2026-03-14：已完成围绕 `CX24-E + CX24-D` 的 follow-up 设计调研；针对 5 个已识别问题冻结 5 条结构修复方案）`
是否需要模型/方法修改：`是（允许围绕 `CX24-E` 诊断平面与 `CX24-D` 证书机制做 selective/soft certificate、calibrated local review、tail-only downgrade、group-stable correction 与 diagnostic compiler 升级；accepted 主线保持不变）`

目标：
围绕 `CX24-E + CX24-D` 做下一轮真正结构化的修复，而不是继续调整证书 margin 或 automaton 阈值。核心任务是：

1. 保留 `CX24-D` 已经修掉 `maze` 的能力；
2. 尽量避免再把 `flange` 主收益从 `+1428.4` 砍到 `+218.0`；
3. 继续压 `parasol_misc` 长尾负项；
4. 把证书与 automaton 的误触发机制变成可诊断、可校准、可解释的对象；
5. 推动 `CX23-C / CX24-D` 从“选择性 leverage”走向更 across-family 稳态的分支。

为什么需要 `CX25`：
1. `CX24-D` 说明 counterfactual commit certificate 的方向是真能解决问题的：
   - `maze` 从 `-113.0` 修到 `0.0`；
   - `narrow_passage` 进一步提升到 `+104.5`；
2. 但它也暴露了清晰的失败机理：
   - 证书过于一刀切，导致 `flange` 主收益被大量误杀；
   - `parasol_misc` 仍为负，说明长尾 commit 风险没有被正确分流；
3. `CX24-E` 则证明：
   - 我们已经能拿到 automaton 的 state occupancy / transition / false-commit trace；
   - 但还没有把这些证据真正反馈回 policy 逻辑。
4. 因而 `CX25` 应把问题重写为：
   - **选择性证书**
   - **软/分级证书**
   - **可校准局部反事实 review**
   - **长尾只降级不否决**
   - **诊断平面增强并反哺控制**
   的系统问题。

调研产物：
1. 详细调研与候选设计见：`reports/rs_p0cx25_design_scout_v1.md`；
2. 该报告主结论是：`CX24-E + CX24-D` 值得继续，但必须从 “global hard veto” 升级到 **selective + soft + calibrated + tail-aware + observable** 的证书系统。

统一设计约束：
1. 所有 `CX25-*` 都建立在 frozen `CX24-E + CX24-D` 之上；
2. 严禁继续做纯参数微调；
3. 所有方案必须能单独陈述为方法贡献；
4. 任何策略修改都必须继续通过 `mp/csm` ordinary-support audit；
5. 若后续进入 hard-test，仍须遵守 frozen-params / no-retune 原则。

冻结候选路线（针对 5 个问题一一对应，建议按 `CX25-B -> CX25-A -> CX25-C -> CX25-D -> CX25-E` 顺序执行）：

##### CX25-A：RS-SSC — Selective Soft Certificate
类型：`selective certificate / graded intervention`
针对问题：
1. `CX24-D` 通过硬证书修掉了 `maze`，但严重误杀 `flange`；
2. 需要“选择性 + 软证书”而不是一票否决。
核心想法：
1. 先用轻量风险探测识别 **高风险被骗段**：
   - 回环 / loop risk
   - 停滞 / stall
   - `commit -> recover` 震荡
   - macro jitter
2. 只有在这些高风险段才触发证书；
3. 证书不过时不直接禁止 commit，而是触发分级动作：
   - 缩短 commit TTL
   - 切 sibling
   - 降回 candidate
   - soft-commit
创新点：
1. 把 `CCC` 从 global hard veto 变成 **selective + graded certificate controller**；
2. 证书强度本身成为一等对象。
预期优势：
1. 保住 `maze` 修复能力；
2. 明显减少对 `flange` 的误杀。
主要风险：
1. 风险探测若不准，会在真正需要证书时缺席；
2. soft action 设计过弱会重新放出假阳性 commit。

##### CX25-B：RS-DTO — Diagnostic-to-Operation Compiler
类型：`diagnostic compiler / evidence-to-policy bridge`
针对问题：
1. 目前虽有 `CX24-E` observability，但还没有反哺控制逻辑；
2. 缺少可校准、可复现的“证据 -> 动作”桥梁。
核心想法：
1. 把 `ATO` 输出的诊断对象编译成控制可用中间件：
   - state occupancy prior
   - transition hotspot table
   - false-commit ledger
   - family-conditioned risk atlas
2. 后续 `SSC / CLR / TSD` 等都只从这个 compiler 接口读取证据；
3. 避免每个 repair 方案重新拼装各类诊断特征。
创新点：
1. 把 observability plane 从日志升级成 **diagnostic compiler**；
2. 这使“诊断证据反哺 policy”本身成为明确方法对象。
预期优势：
1. 让后续证书/审查/长尾降级可复现、可解释；
2. 降低后续方案的实现耦合与调试成本。
主要风险：
1. 本身不直接提升 score；
2. 如果 compiler schema 设计不好，会把噪声标准化。

##### CX25-C：RS-CLR — Calibrated Local Review
类型：`calibrated local counterfactual review`
针对问题：
1. 当前 local counterfactual review 仍偏赢/输式裁决，导致 `flange` 被过度否决；
2. 需要把“证书通过”改成可校准的优势 margin 问题。
核心想法：
1. local review 不再做硬裁决，而是比较：
   - current
   - sibling
   - abstain / baseline
2. 只有当前 class 的优势 margin 超过阈值才发证书；
3. margin 与候选集合都由 `ATO` 的误触发/成功样本统计校准；
4. review 调用频率做 budgeted 限制。
创新点：
1. 把 `CCC` 从 heuristic hard veto 升级为 **calibrated margin certificate**；
2. 让证书保守性变成可统计复现实验对象。
预期优势：
1. 更有机会减少 `flange` 误杀；
2. 比 `SSC` 更直接提升证书判定质量。
主要风险：
1. local proxy 仍可能与真实 long-horizon 目标不对齐；
2. margin calibration 若漂移，会引入新的不稳定性。

##### CX25-D：RS-TSD — Tail Soft Downgrade
类型：`tail-only downgrade / damage-cap controller`
针对问题：
1. `parasol_misc` 仍为负；
2. 长尾状态不应被硬 veto，而应被软降级。
核心想法：
1. 对低支持 / 高不确定 / 高 churn 的 tail states，不做硬 gate；
2. 只降低 commit 强度：
   - 更短 TTL
   - 更强 recover
   - 更倾向 sibling
   - 更快 fallback baseline
3. 把 tail 风险控制写成“伤害上限”问题，而不是“彻底不用”问题。
创新点：
1. 不是 tail abstention，而是 **tail soft downgrade**；
2. 允许 head families 继续吃到正项，而让 tail family 的风险被平滑削顶。
预期优势：
1. 最直接修 `parasol_misc`；
2. 相比 hard gate，更不容易把系统压回 tie。
主要风险：
1. 若 downgrade 太软，tail 仍会误伤；
2. 若 downgrade 太强，又会回到保守退化。

##### CX25-E：RS-GSC — Group-Stable Certificate
类型：`group-stable certificate objective`
针对问题：
1. 整体仍非 across-family 稳定增益；
2. 需要防止只靠 `flange` 单 family 撑起 ceiling。
核心想法：
1. 不再只按平均收益或单 family 修复评估证书；
2. 把 certificate / review / downgrade 的选择目标改成：
   - average gain
   - worst-group penalty
   - tail-risk penalty
   的联合目标；
3. 可以用显式 family，也可用 `ATO` 学到的 latent error groups。
创新点：
1. 把证书系统升级成 **group-stable certificate controller**；
2. 不是事后做 worst-group 分析，而是把 across-family stability 前置到设计目标。
预期优势：
1. 更贴近主线晋升标准；
2. 避免后续继续在单 family 上做选择性 leverage。
主要风险：
1. 若约束过强，可能牺牲全部正项；
2. latent groups 若定义不好，会使目标失真。

推荐执行顺序：
1. **先做 `CX25-B / RS-DTO`**：
   - 没有 evidence compiler，后面的 selective / calibrated 证书仍然难以稳定对症；
2. **再做 `CX25-A / RS-SSC`**：
   - 先把 hard veto 改造成 selective + soft 结构；
3. **再做 `CX25-C / RS-CLR`**：
   - 用校准后的局部 review 提升证书判定质量；
4. **然后做 `CX25-D / RS-TSD`**：
   - 专门处理 `parasol_misc` 长尾误迁移；
5. **最后做 `CX25-E / RS-GSC`**：
   - 在前面对象站住后，再做 across-family 稳态约束。

最低验收标准：
1. 相对 `CX24-D`：
   - `maze` 修复能力尽量保留；
   - `flange` 必须显著高于 `+218.0`；
   - `parasol_misc` 必须较 `-66.667` 明显改善；
2. 任一方案都必须能单独陈述为创新点，而不是“又调了一轮证书阈值”；
3. `mp/csm` ordinary-support audit 继续全量通过。

#### P0-CX25：围绕 `CX24-E + CX24-D` 的证书校正与长尾稳态修复设计调研（已完成首轮 public/mp/csm 实现，未晋升主线）
状态：`COMPLETED（2026-03-14：CX25-B/A/C/D/E 首轮实现与 public `parasol_narrow exp4` + `mp/csm` audit 已完成；无分支晋升主线）`
是否需要模型/方法修改：`是（允许围绕 `CX24-E` 诊断平面与 `CX24-D` 证书机制做 selective/soft certificate、calibrated local review、tail-only downgrade、group-stable correction 与 diagnostic compiler 升级；accepted 主线保持不变）`

目标：
围绕 `CX24-E + CX24-D` 做下一轮真正结构化的修复，而不是继续调整证书 margin 或 automaton 阈值。核心任务是：

1. 保留 `CX24-D` 已经修掉 `maze` 的能力；
2. 尽量避免再把 `flange` 主收益从 `+1428.4` 砍到 `+218.0`；
3. 继续压 `parasol_misc` 长尾负项；
4. 把证书与 automaton 的误触发机制变成可诊断、可校准、可解释的对象；
5. 推动 `CX23-C / CX24-D` 从“选择性 leverage”走向更 across-family 稳态的分支。

为什么需要 `CX25`：
1. `CX24-D` 说明 counterfactual commit certificate 的方向是真能解决问题的：
   - `maze` 从 `-113.0` 修到 `0.0`；
   - `narrow_passage` 进一步提升到 `+104.5`；
2. 但它也暴露了清晰的失败机理：
   - 证书过于一刀切，导致 `flange` 主收益被大量误杀；
   - `parasol_misc` 仍为负，说明长尾 commit 风险没有被正确分流；
3. `CX24-E` 则证明：
   - 我们已经能拿到 automaton 的 state occupancy / transition / false-commit trace；
   - 但还没有把这些证据真正反馈回 policy 逻辑。
4. 因而 `CX25` 应把问题重写为：
   - **选择性证书**
   - **软/分级证书**
   - **可校准局部反事实 review**
   - **长尾只降级不否决**
   - **诊断平面增强并反哺控制**
   的系统问题。

调研产物：
1. 详细调研与候选设计见：`reports/rs_p0cx25_design_scout_v1.md`；
2. 该报告主结论是：`CX24-E + CX24-D` 值得继续，但必须从 “global hard veto” 升级到 **selective + soft + calibrated + tail-aware + observable** 的证书系统。

统一设计约束：
1. 所有 `CX25-*` 都建立在 frozen `CX24-E + CX24-D` 之上；
2. 严禁继续做纯参数微调；
3. 所有方案都必须能单独陈述为方法贡献；
4. 任何策略修改都必须继续通过 `mp/csm` ordinary-support audit；
5. 若后续进入 hard-test，仍须遵守 frozen-params / no-retune 原则。

冻结候选路线（建议按 `CX25-B -> CX25-A -> CX25-C -> CX25-D -> CX25-E` 顺序执行）：

##### CX25-A：RS-SSC — Selective Soft Certificate
类型：`selective certificate / graded intervention`
核心想法：
1. 先用轻量风险探测识别高风险被骗段；
2. 只有高风险段才触发证书；
3. 证书不过时不直接禁用 commit，而是：
   - 缩短 TTL
   - 切 sibling
   - 降回 candidate
   - soft-commit
本轮实现结果：
1. `calib_val`：`success_delta_pp = 0.0`，`exp_delta = -331.571`，`mean_time_overhead_ratio = 2.688910`；
2. public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +60.722`，`mean_time_overhead_ratio = 2.180158`；
3. 它保住了 `maze = 0.0`，但 `flange` 只回到 `+224.8`，仍远低于可接受水平；说明 selective trigger 还不够精准。

##### CX25-B：RS-DTO — Diagnostic-to-Operation Compiler
类型：`diagnostic compiler / evidence-to-policy bridge`
核心想法：
1. 把 `ATO` 的 trace / transition / false-commit ledger 编译成控制可用中间层；
2. 供后续 selective certificate、local review 与 tail downgrade 统一调用。
本轮实现结果：
1. `calib_val`：`success_delta_pp = -14.286`，`exp_delta = +1218.571`，`mean_time_overhead_ratio = 1.296792`；
2. public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +392.889`，`mean_time_overhead_ratio = 1.359908`；
3. `No-Compiler` ablation 几乎同构，说明 compiler 本轮主要贡献是**把诊断证据标准化为可复用对象**，而不是直接涨分。

##### CX25-C：RS-CLR — Calibrated Local Review
类型：`calibrated local counterfactual review`
核心想法：
1. 把 local review 从 binary veto 改成 margin-based 证书；
2. 用 `ATO` 的成功/误触发样本做 margin 校准。
本轮实现结果：
1. `calib_val`：`success_delta_pp = 0.0`，`exp_delta = +34.571`，`mean_time_overhead_ratio = 1.955348`；
2. public `exp4`：`success_delta_pp = 0.0`，`exp_delta = +61.444`，`mean_time_overhead_ratio = 1.718939`；
3. 与 `No-Calibrated-Review` 几乎等价，说明当前校准方式没有真正放松对 `flange` 的误杀。

##### CX25-D：RS-TSD — Tail Soft Downgrade
类型：`tail-only downgrade / damage-cap controller`
核心想法：
1. 对低支持 / 高 churn 的 tail states 不做硬 gate；
2. 只降低 commit 强度与持续时间。
本轮实现结果：
1. public `exp4 = +392.889`，`mean_time_overhead_ratio = 1.431077`；
2. 与 `No-Tail-Downgrade` 基本同构，`parasol_misc` 仍是 `-58.333`；
3. 说明当前 tail detector 还没抓到真正的 misc 误迁移模式。

##### CX25-E：RS-GSC — Group-Stable Certificate
类型：`group-stable certificate objective`
核心想法：
1. 把证书系统的设计目标改成 average + worst-group + tail-risk 的联合目标。
本轮实现结果：
1. public `exp4 = +61.444`，`mean_time_overhead_ratio = 1.734947`；
2. family pattern与 `CX24-D` 基本同构：`maze = 0.0`、`flange = +218.0`、`parasol_misc = -66.667`；
3. `No-Group-Stable` 与 full 近乎一致，说明当前 group-stable objective 还没有真正改变证书行为。

7. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx25_standard_audit_v1.md` 显示 `CX25-B/A/C/D/E` 在 `mp(800)` 与 `csm(400)` 上的 `max_abs_field_diff = 0.0`；
   - 因而本轮变化都来自 nonholonomic branch 的新 policy，而不是 ordinary-support drift。
8. **排序与 go / no-go**：
   - 当前排序：`CX25-B` ≈ `CX25-D` > `CX25-C` ≈ `CX25-E` > `CX25-A`；
   - 但如果按“是否解决关键结构问题”排序：
     - `CX25-B` 最有价值，因为它把诊断证据真正编译成了控制接口；
     - `CX25-A/C/E` 都没有把 `flange` 主收益救回来；
     - `CX25-D` 也没有真正改善 `parasol_misc`。
9. **最终判定**：
   - `CX25` 证明：
     - 证书系统后续最值得继续做的是 **diagnostic-to-operation compiler**；
     - 单独的 selective/soft/calibrated/group-stable/tail-soft 机制，按当前实现都还不够强；
   - 但本轮同样也证明：
     - `maze` 修复与 `flange` 保留之间的核心矛盾仍未被打破；
     - `parasol_misc` 长尾误迁移仍未解决；
     - 没有任何 `CX25` 分支形成可晋升主线的 across-family 稳定增益。
   - 因而 **`CX25` 不晋升 accepted 主线**，accepted 主线继续保持为 `RS + refined CX3-D / RS-HPG`；
   - 但在 `CX24-E + CX24-D` 之后，最值得继续保留的 follow-up 变为：
     - `CX25-B / RS-DTO` 作为证据编译层；
     - 在其上重做下一轮 selective certificate。

#### P0-CX26：围绕 `CX24-E + CX24-D` 的证书系统再设计调研与实现
状态：`COMPLETED-NEGATIVE（2026-03-14：CX26-A/B/C 已全部实现并完成 public-first 验证；三条分支均未改变 CX23-C 的 public 行为，只额外引入约 2.75x runtime overhead，故不晋升主线）`
是否需要模型/方法修改：`是（本轮已围绕 `RS-DTO` 底座、选择性证书、分级证书与 tail-aware downgrade 完成实现；accepted 主线仍保持不变）`

目标：
围绕 `CX24-E + CX24-D` 做下一轮真正聚焦的问题修复，核心不是再调 margin，而是把证书系统重写成：

1. **只在强风险证据段触发**；
2. **证书不过时做可校准的分级动作，而不是一票否决**；
3. **对 `parasol_misc` 的长尾状态先定义对 tail，再做 soft downgrade**。

为什么需要 `CX26`：
1. `CX24-D` 已证明 counterfactual certificate 的确能修 `maze`；
2. `CX24-E` 已证明我们终于拿到了足够细的 automaton 证据；
3. `CX25` 又进一步证明：
   - `RS-DTO` 是对的底座；
   - 但当前 `SSC / CLR / TSD / GSC` 都没有真正把这些证据转化为更优控制；
4. 因而下一轮的关键不是“更多组件”，而是把问题重新聚焦成三条真正可行的路线：
   - selective trigger
   - graded calibrated intervention
   - correct tail definition before downgrade

调研产物：
1. 详细调研与候选设计见：`reports/rs_p0cx26_design_scout_v1.md`；
2. 该报告主结论是：`CX26` 应以 `RS-DTO` 为统一底座，围绕 **risk hotspot trigger / monotone graded certificate / tail definition compiler** 三条线继续推进。

统一设计约束：
1. 所有 `CX26-*` 都建立在 frozen `CX24-E + CX24-D` 与 `CX25-B` 证据编译层之上；
2. 严禁继续做纯参数微调；
3. 每条方案都必须能被单独陈述为创新点；
4. 必须优先回答：
   - 怎样保住 `maze = 0.0`；
   - 怎样把 `flange` 从 `+218.0` 拉回去；
   - 怎样让 `parasol_misc` 明显优于 `-66.667`；
5. `mp/csm` ordinary-support audit 仍必须继续全量通过。

共享补充结论（基于本轮补充评估，已并入 `CX26`，**不另开新方案**）：
1. **`RS-DTO` 必须升级为可验收接口契约**：
   - 这不是单独新方案，而是 `CX26-A/B/C` 的共同前置条件；
   - 若不写清最小 schema、时间窗和归一化，`HST` 很容易退化成“换名字的阈值调参”；
   - 因而后续 `DTO` 的最小 schema 必须至少包含：
     - `occupancy_hotspot_score`
     - `transition_hotspot_score`
     - `false_commit_ledger_hit`
     - `churn_score`
     - `commit_recover_loop_score`
     - `local_proxy_disagreement`
     - `sibling_inconsistency`
     - `tail_uncertainty`
   - 并统一规定：
     - 时间窗：`W_short / W_mid / W_long`
     - 归一化：全部压到 `[0,1]`
     - 输出口径：per-state / per-transition / per-episode 三层。
2. **`CX26-A / RS-HST` 的“共同成立”必须定量化**：
   - 这不需要单独开新方案，应直接补入 `CX26-A`；
   - 采用 **分层 gate** 而不是自由组合：
     - gate-1：至少一个结构证据命中 `{occupancy hotspot, transition hotspot, false-commit ledger}`
     - gate-2：动态风险分数
       `S = w1·churn + w2·commit_recover_loop + w3·proxy_disagreement + w4·sibling_inconsistency`
       超过阈值，且 `{churn, loop, disagreement}` 中至少 `2-of-3` 命中
     - gate-3：episode budget 未耗尽
   - 同时固定：
     - `B_review`: 每 episode 最多 review 次数
     - `B_intervene`: 每 episode 最多强干预次数。
3. **`CX26-B / RS-MGI` 必须防止“伪单调”**：
   - 这不需要单独开新方案，应直接补入 `CX26-B`；
   - 后续不再分别独立调 `TTL / sibling / fallback`，而是先合成为单一 **干预强度标量** `z∈[0,1]`；
   - 再由单调映射把 `z` 映射到：
     - TTL 缩短幅度
     - sibling 优先级
     - soft-commit 强度
     - fallback 时机
   - 这样可减少自由度，并保证整体动作强度对风险分数保持单调。
4. **`CX26-C / RS-TDC` 必须防止退化成 OOD detector**：
   - 这不需要单独开新方案，应直接补入 `CX26-C`；
   - tail feature family 必须优先是 **结构性不一致**：
     - churn / oscillation
     - `commit→recover` loop
     - local proxy disagreement
     - sibling inconsistency
   - 而不是：
     - rarity
     - sample scarcity
     - generic OOD score
   - 同时必须写明作用域：
     - `TDC` 只用于 `parasol_misc` / tail-risk 削顶；
     - 不得向 `flange / narrow_passage / maze` 这类 head/hard families 全局扩散，否则又会退回保守 tie。

冻结候选路线（建议按 `CX26-A -> CX26-B -> CX26-C` 顺序执行）：

##### CX26-A：RS-HST — Hotspot-Scoped Trigger
类型：`risk hotspot trigger / selective certificate scope`
对应问题：
1. 证书调用还不够选择性，继续复现 `flange` 误杀。
核心想法：
1. 以 `RS-DTO` 为底座，定义高风险被骗段：
   - occupancy hotspot
   - transition hotspot
   - false-commit ledger hit
   - commit→recover / churn signal
2. 只有当这些风险证据共同成立时，才触发 `CCC` 或其后继证书；
3. 非高风险段完全不调用证书，避免 head-family 被过度干预。
创新点：
1. 把 `DTO` 从被动诊断层升级成 **trigger compiler**；
2. 证书是否被调用，第一次由结构证据而不是全局规则决定。
补充实现约束（本轮新增）：
1. `HST` 必须采用 **分层 gate + 预算**，而不是自由阈值堆叠：
   - gate-1：`{occupancy, transition, ledger}` 至少一项命中；
   - gate-2：动态风险分数 `S` 超阈，且 `{churn, loop, disagreement}` 至少 `2-of-3` 成立；
   - gate-3：`B_review / B_intervene` 预算未耗尽；
2. 必须显式报告：
   - trigger 频率
   - budget 命中率
   - 不同 family 上的 trigger 分布。
预期优势：
1. 保住 `maze` 修复能力的同时减少 `flange` 误杀；
2. 比 `SSC` 更直接，因为它先重写“何时调用证书”。
主要风险：
1. 若 hotspot 定义不准，仍可能漏触发或误触发；
2. 风险证据过稀时，收益会退回 `CX23-C`。

##### CX26-B：RS-MGI — Monotone Graded Intervention
类型：`graded certificate / monotone control law`
对应问题：
1. 证书从 hard veto 变成 graded intervention，但要真正可校准。
核心想法：
1. 把证书输出从 `pass/fail` 改成单调风险分数；
2. 风险分数控制：
   - commit TTL
   - sibling priority
   - soft-commit strength
   - fallback probability / timing
3. 用 `ATO` 的 true-positive / false-positive 样本做风险→动作的 monotone calibration。
创新点：
1. 把证书系统升级成 **连续控制律**，而不是离散 hard veto；
2. 让动作强度成为风险分数的显式单调函数。
补充实现约束（本轮新增）：
1. 必须先定义单一 **干预强度标量** `z∈[0,1]`；
2. 再由 `z` 单调映射到：
   - TTL
   - sibling priority
   - soft-commit
   - fallback timing；
3. 不允许再让多个动作通道各自独立调节，否则会重新出现“局部单调、整体不单调”的伪单调问题。
预期优势：
1. 最有机会把 `flange` 从 `+218.0` 往回拉；
2. 比 `CLR` 更完整，因为它不只校准是否发证书，还校准发证书后的动作强度。
主要风险：
1. 单调映射若不稳，会出现半软不硬的模糊行为；
2. 若 calibration 样本不足，可能仍然等价于 hard split。

##### CX26-C：RS-TDC — Tail Definition Compiler
类型：`tail definition / long-tail risk compiler`
对应问题：
1. `parasol_misc` 要做 tail-only downgrade，但首先必须把 tail 定义对。
核心想法：
1. 不再直接看 support count，而是定义更对症的 tail feature family：
   - churn / oscillation
   - commit→recover loop
   - local proxy disagreement
   - sibling inconsistency
   - tail uncertainty under `DTO`
2. 用这些特征学习/编译一个 tail definition object；
3. 只有被判为 true tail-risk 的状态，才触发 soft downgrade。
创新点：
1. 把 tail 从“少样本”提升为 **结构性不一致状态**；
2. downgrade 之前先做 tail definition compiler。
补充实现约束（本轮新增）：
1. `TDC` 不能退化成 generic OOD detector；
2. tail feature family 必须优先使用：
   - churn / oscillation
   - `commit→recover` loop
   - local proxy disagreement
   - sibling inconsistency
   - tail uncertainty under `DTO`
3. 必须显式限制作用域：
   - `TDC` 只影响 tail-risk / `parasol_misc` 风险削顶；
   - 不得对 head families 全局降低 commit 强度。
预期优势：
1. 最直接对准 `parasol_misc = -66.667`；
2. 更有机会在不伤 head families 的前提下压 misc 负项。
主要风险：
1. tail definition 若学成泛 OOD detector，仍会把系统压回保守；
2. 若 tail 特征不稳定，会放大噪声。

推荐执行顺序：
1. **先做 `CX26-A / RS-HST`**：
   - 先把证书作用域缩到真正高风险段；
2. **再做 `CX26-B / RS-MGI`**：
   - 再把证书从 hard veto 变成单调 graded intervention；
3. **最后做 `CX26-C / RS-TDC`**：
   - 在证书机制更稳后，再集中修 `parasol_misc` 长尾误迁移。

最低验收标准：
1. 相对 `CX24-D`：
   - `maze = 0.0` 尽量保持；
   - `flange` 必须显著高于 `+218.0`；
   - `parasol_misc` 必须较 `-66.667` 明显改善；
2. 相对 `CX23-C`：
   - 不得把 `narrow_passage` 重新打回负项；
3. 所有 `CX26-*` 仍须通过 `mp/csm` ordinary-support audit。

本轮实现结果（`2026-03-14`，对应产物：`reports/rs_p0cx26_a_pilot_v1.md`、`reports/rs_p0cx26_b_pilot_v1.md`、`reports/rs_p0cx26_c_pilot_v1.md`、`reports/rs_p0cx26_round1_summary.md`、`reports/rs_p0cx26_standard_audit_v1.md`）：
1. **统一协议**：
   - 训练/编译对象只使用 `calib_hard_v1/train`；
   - dev 只用于候选选择；
   - public 评估锁定在 `parasol_narrow exp4`；
   - 本轮继续只做 public-first + `mp/csm` ordinary-support audit，**未消费 `rs_root_hard_v2/test`**。
2. **`CX26-A / RS-HST`**：
   - public `exp4 = +392.889`，overhead `2.751741`；
   - family breakdown 与 `CX23-C` 完全相同：`flange = +1428.4`、`narrow_passage = +98.25`、`maze = -113.0`、`parasol_misc = -58.333`；
   - `No-Hotspot-Trigger` ablation 与 full 在 success / expansions 上完全一致；
   - 诊断证据：`hst_meta.json` 中 `false_classes=[]`、`false_transitions=[]`，public `diagnostic_rows.csv` 里 `occupancy_hotspot_score / transition_hotspot_score / false_commit_ledger_hit` 全部为 `0`，review / intervene budgets 始终停留在初始值；
   - 结论：`HST` 没有真正触发，收益全部继承自 `CX23-C`，新层只增加了 bookkeeping 开销。
3. **`CX26-B / RS-MGI`**：
   - public `exp4 = +392.889`，overhead `2.776023`；
   - family breakdown 同样与 `CX23-C` 完全相同；
   - `No-MGI` ablation 与 full 在 success / expansions 上完全一致；
   - 诊断证据：`mgi_meta.json` 只给出弱边界 `pass_margin=-0.0383`、`reject_margin=0.0`，public `diagnostic_rows.csv` 中没有任何 `mgi_z` 输出，且 hotspot / ledger 证据仍全为 `0`；
   - 结论：单调 graded intervention 从未真正介入搜索，额外代价只来自 DTO 证据构造。
4. **`CX26-C / RS-TDC`**：
   - public `exp4 = +392.889`，overhead `2.776835`；
   - family breakdown 仍与 `CX23-C` 完全相同；
   - `No-TDC` ablation 与 full 在 success / expansions 上完全一致；
   - 诊断证据：`tdc_meta.json` 直接显示 `has_tail_band=false`，说明 `calib_hard_v1/train` 上根本没有编译出可用的 tail structural band；
   - 结论：`TDC` 没有形成 tail-only downgrade，整条线同样只留下额外开销。
5. **共享失败机理**：
   - 三条分支的 `public_case_rows.csv` 都与 `CX23-C (Full)` 在每个 `exp4` case 上 expansion-identical；
   - DTO 证据面整体塌缩为无区分常数：
     - `occupancy_hotspot_score = 0`
     - `transition_hotspot_score = 0`
     - `false_commit_ledger_hit = 0`
     - `local_proxy_disagreement = 0.5`
     - `tail_uncertainty = 1.0`
   - 因而 `CX26` 当前的真正瓶颈不在 trigger / graded action / tail downgrade 形式本身，而在 **DTO compiler 没有产出可用的 discriminative evidence**。
6. **`mp/csm` ordinary-support audit**：
   - `reports/rs_p0cx26_standard_audit_v1.md` 显示 `CX26-A/B/C` 在 `mp(800)` 与 `csm(400)` 上均满足 `max_abs_field_diff = 0.0`；
   - 因而本轮所有变化都来自 nonholonomic policy logic，而不是 ordinary-support drift。
7. **最终判定**：
   - `CX26-A/B/C` 都没有生成新的 public gain，只是把 `CX23-C` 的旧 ceiling 以更高 runtime 重放了一遍；
   - 三条线均 **不晋升 accepted 主线**；
   - 若继续沿这条路线推进，下一步必须先修 `RS-DTO` 编译层本身，使其能够产生：
     - 非空 false-commit ledger
     - 有效 hotspot scores
     - 可拟合的 tail structural band
     否则继续在其上叠加 gate / graded action / tail rule 都只会得到“无效但更贵”的变体。

#### P0-CX27：直接围绕 `CX23-C / RS-HAA` 修复 `maze` 与 `parasol_misc`
状态：`COMPLETED-PARTIAL（2026-03-15：围绕 CX23-C 连续实施 5 条 HAA 内部修复分支并完成 full public/support 验证；成功消除了 `maze` 负项，但 `parasol_misc` 仍未被修复，因此未达到整体验收目标）`
是否需要模型/方法修改：`是（本轮直接修改 RS-HAA 的在线控制逻辑；未再走 “先 design scout 再冻结” 路径，accepted 主线仍保持不变）`

目标：
在不改动 accepted `RS + refined CX3-D / RS-HPG` 基础场的前提下，直接修复 `CX23-C / RS-HAA` 的两项遗留问题：

1. `maze = -113.0`
2. `parasol_misc = -58.333`

同时尽量维持：

1. public `exp_delta ≈ +392.889`
2. `flange = +1428.4`
3. `narrow_passage = +98.25`

研究锚点（用于指导本轮直接实现，不单独开 design scout）：
1. heuristic depression / trap avoidance：
   - Hernández, Baier, Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011
   - 链接：`https://ojs.aaai.org/index.php/SOCS/article/view/18315`
2. failure experience compilation：
   - Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012
   - 链接：`https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf`
3. abstention / reject-option control：
   - Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019
   - 链接：`https://proceedings.mlr.press/v97/geifman19a.html`
4. learned preconditions / safe delegation：
   - Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021
   - 链接：`https://proceedings.mlr.press/v164/ravichandar22a.html`

本轮实现产物：
1. `rs_cx27/common.py`
2. `rs_cx27/cx27_a_mdg.py`
3. `rs_cx27/cx27_b_tad.py`
4. `rs_cx27/cx27_c_efm.py`
5. `rs_cx27/cx27_d_mcg.py`
6. `rs_cx27/cx27_f_mmr.py`
7. `scripts/run_rs_p0cx27_round1_v1.py`
8. `reports/rs_p0cx27_a_pilot_v1.md`
9. `reports/rs_p0cx27_b_pilot_v1.md`
10. `reports/rs_p0cx27_c_pilot_v1.md`
11. `reports/rs_p0cx27_d_pilot_v1.md`
12. `reports/rs_p0cx27_f_pilot_v1.md`
13. `reports/rs_p0cx27_round1_summary.md`
14. `reports/rs_p0cx27_standard_audit_v1.md`

统一协议：
1. parent 固定为 frozen `CX23-C / RS-HAA`；
2. trial selection 只用 `calib_hard_v1`；
3. public 评估锁定 `parasol_narrow exp4`；
4. `mp/csm` 只做 ordinary-support audit，要求 `build_standard_field == accepted CX3-D`；
5. 本轮 **未消费 `rs_root_hard_v2/test`**。

本轮直接尝试的 5 条 HAA 修复分支：

##### CX27-A：Maze Depression Guard（`rs_cx27/cx27_a_mdg.py`）
核心想法：
1. 仅对 `maze` 家族启用 event-triggered depression guard；
2. 当 `forward_safe|straight` 在 maze 中出现 revisit / stall / failed-commit 信号时，直接 abstain 或切到 `reverse_setup|reverse`。
结果：
1. 相对 `CX23-C (Full)`：
   - public `exp_delta` 从 `+392.889` 提升到 `+399.167`；
   - `maze` 从 `-113.0` 提升到 `0.0`（即 `+113.0` repair）；
   - `flange`、`narrow_passage`、`parasol_misc` 与 parent 保持不变；
2. 代价：
   - runtime 仍高于 parent，`exp4` overhead 约 `2.398235x`。
结论：
1. **这是本轮最佳分支**；
2. 证明 `maze` 问题确实可以在 HAA 层通过 depression-style selective abstention 被修掉。

##### CX27-B：Tail Abstention Dampener（`rs_cx27/cx27_b_tad.py`）
核心想法：
1. 只对 `parasol_misc` 施加基于 revisit / churn / loop 的 soft abstention。
结果：
1. 相对 parent 所有 public family 的 expansions 完全不变；
2. `parasol_misc` 没有任何改善。
结论：
1. 当前 misc tail-dampener 触发了，但没有改变搜索决策；
2. 这条线 **无行为增益**。

##### CX27-C：Episode Failure Memory（`rs_cx27/cx27_c_efm.py`）
核心想法：
1. 把 commit failure 编译成 episode-local blocklist；
2. 用 failure memory 同时修 maze 和 misc。
结果：
1. `maze` 从 `-113.0` 提升到 `-3.0`（约 `+110.0` repair）；
2. 但 `flange` 下降 `-51.0`，`narrow_passage` 下降 `-0.25`；
3. `parasol_misc` 仍不变。
结论：
1. broader failure-memory 逻辑能修 maze；
2. 但副作用大于收益，**不如 CX27-A**。

##### CX27-D：Misc Class Global Cooldown（`rs_cx27/cx27_d_mcg.py`）
核心想法：
1. 对 misc 中失败过的 class 做 episode-global cooldown。
结果：
1. `maze` 同样提升到 `-3.0`；
2. `parasol_misc` 反而进一步下降到 `-58.5`；
3. `flange` / `narrow_passage` 仍有小幅回退。
结论：
1. misc 问题不是“forward_safe 失败后全局关掉”这么简单；
2. 这条线 **未达目标**。

##### CX27-F：Maze + Misc Redirect（`rs_cx27/cx27_f_mmr.py`）
核心想法：
1. 组合 maze depression guard 与 misc reverse-setup redirection；
2. 试图在 misc 中把失败的 `forward_safe` 直接改成 `reverse_setup`。
结果：
1. `maze` 提升到 `-3.0`；
2. `parasol_misc` 明显变差到 `-67.833`；
3. 整体只比 parent 提升 `+2.944`。
结论：
1. misc 并不是缺少一次简单的 reverse redirect；
2. 当前 redirect 方案会放大 tail 误迁移。

本轮总结合论：
1. **`maze` 已被局部攻破**：
   - `CX27-A` 证明 `maze = -113.0` 主要是 HAA 的 depression / repeated-commit 误触发；
   - 精确的 maze-only abstention 可以把它抹到 `0.0`。
2. **`parasol_misc` 仍未解决**：
   - soft abstain（`CX27-B`）无效；
   - episode failure memory（`CX27-C`）无效；
   - global cooldown（`CX27-D`）无效甚至更差；
   - reverse redirect（`CX27-F`）显著更差。
3. **当前最可信判断**：
   - `parasol_misc` 不是单纯“过度 commit”问题；
   - 它更像是 **缺少可靠替代动作语言 / 缺少正确正向 policy** 的 tail regime；
   - 因而再继续做纯 suppress / abstain / cooldown，大概率只会 tie 或变差。
4. **主线判定**：
   - `CX27-A` 可以作为后续 follow-up 的正信号保留；
   - 但整个 `CX27` 仍 **不晋升 accepted 主线**，因为：
     - `parasol_misc` 没修掉；
     - runtime 仍显著高于 parent `CX23-C`。
5. **下一步建议**：
   - 若继续做 `CX27` follow-up，不应再继续堆 suppressor；
   - 应转向为 `parasol_misc` 学一个更可靠的 **alternative commit class / alternative macro language**，
     而不是继续问“何时不要 commit 当前 class”。

#### P0-CX28：围绕 `CX27-A / Maze Depression Guard` 修复 `parasol_misc`
状态：`COMPLETED-PARTIAL（2026-03-15：围绕 CX27-A 连续实现 5 条 misc-targeted repair 分支并完成 public/full-support 验证；`parasol_misc` 得到有限改善，但仍未达到目标）`
是否需要模型/方法修改：`是（本轮直接在 CX27-A 上追加 misc-specific local option review / precondition gating / scene-conditioned arbitration；accepted 主线仍保持不变）`

目标：
在保持 `CX27-A` 已经得到的：

1. `public exp_delta = +399.167`
2. `maze = 0.0`
3. `flange = +1428.4`
4. `narrow_passage = +98.25`

的前提下，进一步修复：

1. `parasol_misc = -58.333`

研究锚点（本轮直接实现时采用，不单独开 design scout）：
1. Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021  
   - `https://proceedings.mlr.press/v164/ravichandar22a.html`
2. Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012  
   - `https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf`
3. Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019  
   - `https://proceedings.mlr.press/v97/geifman19a.html`
4. Hernández, Baier, Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011  
   - `https://ojs.aaai.org/index.php/SOCS/article/view/18315`

本轮实现产物：
1. `rs_cx28/common.py`
2. `rs_cx28/cx28_a_mcr.py`
3. `rs_cx28/cx28_b_mcp.py`
4. `rs_cx28/cx28_c_msa.py`
5. `rs_cx28/cx28_d_mft.py`
6. `rs_cx28/cx28_e_bft.py`
7. `scripts/run_rs_p0cx28_round1_v1.py`
8. `reports/rs_p0cx28_a_pilot_v1.md`
9. `reports/rs_p0cx28_b_pilot_v1.md`
10. `reports/rs_p0cx28_c_pilot_v1.md`
11. `reports/rs_p0cx28_d_pilot_v1.md`
12. `reports/rs_p0cx28_e_pilot_v1.md`
13. `reports/rs_p0cx28_round1_summary.md`
14. `reports/rs_p0cx28_standard_audit_v1.md`

统一协议：
1. parent 固定为 frozen `CX27-A / Maze Depression Guard`；
2. trial selection 只用 `calib_hard_v1`；
3. public 评估锁定 `parasol_narrow exp4`；
4. `mp/csm` ordinary-support audit 已对 `CX28-A/B/C/D/E` 全量跑满 `mp(800)` / `csm(400)`，全部满足 `max_abs_field_diff = 0.0`；
5. 本轮 **未消费 `rs_root_hard_v2/test`**。

本轮连续尝试的 5 条 misc 修复路线：

##### CX28-A：Misc Counterfactual Review（`rs_cx28/cx28_a_mcr.py`）
核心想法：
1. 在 misc 风险段对 `forward_safe|straight` 做本地 class review；
2. 比较 `forward_turn / reverse_setup / abstain` 与当前 class 的局部 proxy 分数。
结果：
1. 相对 `CX27-A`：
   - `parasol_misc` 从 `-58.333` 变到 `-64.667`（更差）；
   - `maze / flange / narrow_passage` 不变。
结论：
1. 纯 local review 仍会在 tail 上过触发；
2. 这条线 **不可用**。

##### CX28-B：Misc Class Preconditions（`rs_cx28/cx28_b_mcp.py`）
核心想法：
1. 在 `CX28-A` 基础上加入 class-specific failure blocklist；
2. 失败过的 misc class 在 episode 内短时禁用。
结果：
1. 相对 `CX27-A`：
   - `parasol_misc` 同样退化到 `-64.667`；
   - 其余保护 family 不变。
结论：
1. blocklist 并没有解决 misc 的错误触发；
2. 说明问题不只是“坏 class 重复使用”。

##### CX28-C：Misc Scene Arbitration（`rs_cx28/cx28_c_msa.py`）
核心想法：
1. 给 misc local review 增加 scene-conditioned bonuses；
2. 尝试让不同 misc 子型走不同 macro language。
结果：
1. 相对 `CX27-A`：
   - `parasol_misc` 恶化到 `-78.000`；
   - 总体 public `exp_delta` 也退化；
2. 诊断发现其主要问题是把某些 misc case 推到了错误的 reverse-style language。
结论：
1. broader scene arbitration 会放大最坏 misc case；
2. **reverse-style misc repair 不是正确方向**。

##### CX28-D：Misc Forward-Turn Arbitration（`rs_cx28/cx28_d_mft.py`）
核心想法：
1. 不再把 misc repair 指向 reverse family；
2. 只在 misc 高风险段为 `forward_safe|straight` 提供一个更窄的 **`forward_safe|forward_turn` alternative macro language**。
结果：
1. 相对 `CX27-A`：
   - public `exp_delta` 从 `+399.167` 提升到 `+400.556`；
   - `parasol_misc` 从 `-58.333` 提升到 `-54.167`（即 `+4.167` repair）；
   - `maze = 0.0`、`flange = +1428.4`、`narrow_passage = +98.25` 全部保持不变；
2. 这是本轮最佳分支。
结论：
1. `parasol_misc` 的正确信号不是 abstain，也不是 reverse；
2. 它更像需要一个 **selective forward-turn option**。

##### CX28-E：Bridge-Filtered Forward-Turn（`rs_cx28/cx28_e_bft.py`）
核心想法：
1. 在 `CX28-D` 上加入额外桥接/扩散过滤；
2. 只在更像“高障碍、低桥接”的 misc 子段启用 `forward_turn`。
结果：
1. 相对 `CX27-A`：
   - public `exp_delta` 提升到 `+399.778`；
   - `parasol_misc` 提升到 `-56.500`（即 `+1.833` repair）；
   - 保护 family 仍保持不变。
结论：
1. 过滤能降低误触发，但也削弱了真正有用的 `forward_turn` 干预；
2. 因而它比 `CX28-D` 更保守，也更弱。

本轮总结合论：
1. `CX27-A` 的 `maze` 修复已经稳定保住；
2. `parasol_misc` 方向上，真正有价值的不是：
   - abstention
   - reverse redirection
   - generic scene arbitration
   而是 **forward-turn alternative macro language**；
3. 当前最佳分支 `CX28-D` 已经给出明确正信号：
   - `parasol_misc`: `-58.333 -> -54.167`
   - public `exp_delta`: `+399.167 -> +400.556`
   - `maze / flange / narrow_passage` 全部保持
4. 但它仍未达到最终目标，因为：
   - `parasol_misc` 仍为负；
   - online overhead 仍高于 parent。

主线判定：
1. `CX28` 整体 **不晋升 accepted 主线**；
2. 但 `CX28-D / Misc Forward-Turn Arbitration` 应被保留为 `CX27-A` 的首选 follow-up；
3. 下一步若继续推进，应聚焦：
   - 如何更可靠地识别“何时该从 `forward_safe|straight` 切到 `forward_safe|forward_turn`”
   - 而不是继续增加 abstain 或 reverse-family 修补器。

#### P0-CX29：围绕 `CX28-D / Misc Forward-Turn Arbitration` 的后续修复
状态：`COMPLETED-PARTIAL（2026-03-16：围绕 `CX28-D` 连续实现 4 条 forward-turn follow-up 分支并完成 public/full-support 验证；找到轻微优于 parent 的 misc 修复，但仍未达到最终目标）`
是否需要模型/方法修改：`是（本轮继续围绕 misc 的 forward-turn arbitration 做 follow-up；accepted 主线仍保持不变）`

目标：
在保住 `CX28-D` 已达到的：

1. `public exp_delta = +400.556`
2. `maze = 0.0`
3. `flange = +1428.4`
4. `narrow_passage = +98.25`

的前提下，继续压低：

1. `parasol_misc = -54.167`

研究锚点（本轮直接实现时采用，不单独开 design scout）：
1. Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021  
   - `https://proceedings.mlr.press/v164/ravichandar22a.html`
2. Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012  
   - `https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf`
3. Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019  
   - `https://proceedings.mlr.press/v97/geifman19a.html`
4. Hernández, Baier, Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011  
   - `https://ojs.aaai.org/index.php/SOCS/article/view/18315`

本轮实现产物：
1. `rs_cx29/common.py`
2. `rs_cx29/cx29_a_mtr.py`
3. `rs_cx29/cx29_b_ftb.py`
4. `rs_cx29/cx29_c_bct.py`
5. `rs_cx29/cx29_d_abc.py`
6. `scripts/run_rs_p0cx29_round1_v1.py`
7. `reports/rs_p0cx29_a_pilot_v1.md`
8. `reports/rs_p0cx29_b_pilot_v1.md`
9. `reports/rs_p0cx29_c_pilot_v1.md`
10. `reports/rs_p0cx29_d_pilot_v1.md`
11. `reports/rs_p0cx29_round1_summary.md`
12. `reports/rs_p0cx29_standard_audit_v1.md`

统一协议：
1. parent 固定为 frozen `CX28-D / Misc Forward-Turn Arbitration`；
2. trial selection 只用 `calib_hard_v1`；
3. public 评估锁定 `parasol_narrow exp4`；
4. `mp/csm` ordinary-support audit 已对 `CX29-A/B/C/D` 全量跑满 `mp(800)` / `csm(400)`，全部满足 `max_abs_field_diff = 0.0`；
5. 本轮 **未消费 `rs_root_hard_v2/test`**。

本轮连续尝试的 4 条 forward-turn follow-up 路线：

##### CX29-A：Multi-Step Turn Review（`rs_cx29/cx29_a_mtr.py`）
核心想法：
1. 不再只用单步 proxy；
2. 在 misc 触发段对 `forward_turn / abstain / current` 做 multi-step rollout review。
结果：
1. 相对 `CX28-D`：
   - public `exp_delta` 下降到 `+399.167`；
   - `parasol_misc` 退化到 `-58.333`；
   - 保护 family 保持不变。
结论：
1. 更重的在线 local review 没有带来更好 misc trigger；
2. 这条线 **无效**。

##### CX29-B：Forward-Turn Blend（`rs_cx29/cx29_b_ftb.py`）
核心想法：
1. 不再切到严格 `forward_turn`；
2. 在 misc 高风险段切到一个同时允许 `straight + forward_turn` 的 blended option language。
结果：
1. 相对 `CX28-D`：
   - public `exp_delta = +400.222`
   - `parasol_misc = -55.167`
   - 保护 family 保持不变。
结论：
1. blend 比 multi-step review 更稳；
2. 但仍未超过 parent。

##### CX29-C：Bridge-Calibrated Turn Trigger（`rs_cx29/cx29_c_bct.py`）
核心想法：
1. 继续坚持 `forward_turn` 路线；
2. 用 `bridge_diffuse` 这类结构信号做更窄的 bridge-calibrated trigger。
结果：
1. 相对 `CX28-D`：
   - public `exp_delta` 从 `+400.556` 提升到 `+400.722`
   - `parasol_misc` 从 `-54.167` 提升到 `-53.667`（即 `+0.500` repair）
   - `maze / flange / narrow_passage` 全部保持不变。
结论：
1. 这是本轮第一个真正优于 parent 的分支；
2. 说明 misc trigger 的关键是 **bridge-sensitive calibration**。

##### CX29-D：Aux-Calibrated Bridge Threshold（`rs_cx29/cx29_d_abc.py`）
核心想法：
1. 不再只在 `calib_hard_v1` 上调桥接阈值；
2. 用非公开的 `rs_root_hard_v2/dev` 中 misc 样本对 `bridge_thr` 做辅助校准，再迁移到 public。
结果：
1. 相对 `CX28-D`：
   - public `exp_delta` 同样提升到 `+400.722`
   - `parasol_misc` 同样提升到 `-53.667`
   - 保护 family 全部保持不变；
2. `trial_02/abc_meta.json` 显示最终 auxiliary-selected `bridge_thr = 0.13`。
结论：
1. 与 `CX29-C` 达到同样的 public 最优读数；
2. 但它具有更好的协议叙事，因为桥接阈值来自非公开 auxiliary misc 校准，而不是仅靠主 val 选择。

本轮总结合论：
1. `CX28-D` 的 forward-turn 方向是对的；
2. `CX29` 进一步证明：
   - misc 的改进空间确实存在；
   - 但改进来源不是更重的 local review；
   - 而是 **更精准的 bridge/structure-sensitive forward-turn trigger**。
3. 本轮最优结果：
   - `public exp_delta = +400.722`
   - `parasol_misc = -53.667`
   - `maze = 0.0`
   - `flange = +1428.4`
   - `narrow_passage = +98.25`
4. 这比 `CX28-D` 略有进步，但仍未达到最终目标，因为：
   - `parasol_misc` 仍为负；
   - misc 修复幅度仍然有限。

主线判定：
1. `CX29` 整体 **不晋升 accepted 主线**；
2. 但 `CX29-D / Aux-Calibrated Bridge Threshold` 是当前该路线最合理的 follow-up 保留对象；
3. 下一步若继续推进，应重点研究：
   - 是否存在比 `bridge_diffuse` 更强的结构区分特征；
   - 以及如何把 `forward_turn` trigger 从“单阈值”升级成更可靠的 initiation set / precondition classifier。

#### P0-CX30：围绕 `CX29-D / Aux-Calibrated Bridge Threshold` 继续压 `parasol_misc`
状态：`COMPLETED-PARTIAL（2026-03-16：围绕 `CX29-D` 连续实现 3 条更窄的 forward-turn initiation-set 修复分支并完成 public/full-support 验证；再次取得小幅改进，但仍未达到最终目标）`
是否需要模型/方法修改：`是（本轮继续围绕 forward-turn initiation set 做更细的结构门控；accepted 主线仍保持不变）`

目标：
在保住 `CX29-D` 已达到的：

1. `public exp_delta = +400.722`
2. `maze = 0.0`
3. `flange = +1428.4`
4. `narrow_passage = +98.25`

的前提下，继续压低：

1. `parasol_misc = -53.667`

研究锚点（本轮直接实现时采用，不单独开 design scout）：
1. Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021  
   - `https://proceedings.mlr.press/v164/ravichandar22a.html`
2. Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012  
   - `https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf`
3. Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019  
   - `https://proceedings.mlr.press/v97/geifman19a.html`
4. Hernández, Baier, Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011  
   - `https://ojs.aaai.org/index.php/SOCS/article/view/18315`

本轮实现产物：
1. `rs_cx30/common.py`
2. `rs_cx30/cx30_a_por.py`
3. `rs_cx30/cx30_b_att.py`
4. `rs_cx30/cx30_c_lbf.py`
5. `scripts/run_rs_p0cx30_round1_v1.py`
6. `reports/rs_p0cx30_a_pilot_v1.md`
7. `reports/rs_p0cx30_b_pilot_v1.md`
8. `reports/rs_p0cx30_c_pilot_v1.md`
9. `reports/rs_p0cx30_round1_summary.md`
10. `reports/rs_p0cx30_standard_audit_v1.md`

统一协议：
1. parent 固定为 frozen `CX29-D / Aux-Calibrated Bridge Threshold`；
2. trial selection 只用 `calib_hard_v1`；
3. public 评估锁定 `parasol_narrow exp4`；
4. `mp/csm` ordinary-support audit 已对 `CX30-A/B/C` 全量跑满 `mp(800)` / `csm(400)`，全部满足 `max_abs_field_diff = 0.0`；
5. 本轮 **未消费 `rs_root_hard_v2/test`**。

本轮连续尝试的 3 条 initiation-set 修复路线：

##### CX30-A：Path-Openness Refined Gate（`rs_cx30/cx30_a_por.py`）
核心想法：
1. 不再用单一 bridge threshold；
2. 引入 `bridge_low + bridge_high + path_openness + focus_gap` 的双层结构门控。
结果：
1. 相对 `CX29-D`：
   - public `exp_delta` 提升到 `+401.389`
   - `parasol_misc` 从 `-53.667` 提升到 `-51.667`（即 `+2.000` repair）
   - `maze / flange / narrow_passage` 全部保持不变。
结论：
1. 说明 `path_openness` 与 `focus_gap` 的组合确实能缩小 misc 触发误差；
2. 但仍不是本轮最优。

##### CX30-B：Aux Trigger Tree（`rs_cx30/cx30_b_att.py`）
核心想法：
1. 用 auxiliary misc 状态构造 event-level tree；
2. 用 tree 来决定是否切到 `forward_turn`。
结果：
1. 相对 `CX29-D`：
   - public `exp_delta = +401.278`
   - `parasol_misc = -52.000`（即 `+1.667` repair）
   - 保护 family 全部保持不变。
结论：
1. 数据驱动的 initiation set 确实有用；
2. 但目前 aux tree 仍弱于手工结构门控。

##### CX30-C：Low-Bridge + Focus Gate（`rs_cx30/cx30_c_lbf.py`）
核心想法：
1. 将 trigger 进一步收窄到：
   - very low `bridge_diffuse`
   - coupled with low `focus_gap`
2. 不再尝试覆盖更宽的 misc 子型，只专注于 `000006` 这类最有利段。
结果：
1. 相对 `CX29-D`：
   - public `exp_delta` 从 `+400.722` 提升到 `+401.444`
   - `parasol_misc` 从 `-53.667` 提升到 `-51.500`（即 `+2.167` repair）
   - `maze = 0.0`、`flange = +1428.4`、`narrow_passage = +98.25` 全部保持不变；
2. 这是本轮最佳分支。
结论：
1. 当前 misc 剩余问题已经进一步收缩为一个 **更窄的 low-bridge / low-focus 子型**；
2. initiation set 缩窄比更复杂的 tree 更有效。

本轮总结合论：
1. `CX29-D` 的 bridge-calibrated forward-turn 路线继续有效；
2. `CX30` 进一步证明：
   - `parasol_misc` 剩余改进空间主要来自更细的 initiation-set 收窄；
   - 不是来自更复杂的 global model 或更重的 rollout；
3. 本轮最优结果：
   - `public exp_delta = +401.444`
   - `parasol_misc = -51.500`
   - `maze = 0.0`
   - `flange = +1428.4`
   - `narrow_passage = +98.25`
4. 这比 `CX29-D` 再向前推进了一步，但仍未达到最终目标，因为：
   - `parasol_misc` 仍为负；
   - misc gain 仍主要集中在极少数 case。

主线判定：
1. `CX30` 整体 **仍不晋升 accepted 主线**；
2. 但 `CX30-C / Low-Bridge + Focus Gate` 是当前该路线最好的保留对象；
3. 下一步若继续推进，应聚焦：
   - 寻找比 `bridge_diffuse + focus_gap` 更强的结构区分特征；
   - 把 trigger 从单/双阈值进一步升级成更稳的 initiation-set classifier。

#### P0-CX31：围绕 `CX30-C / Low-Bridge + Focus Gate` 继续压 `parasol_misc`
状态：`COMPLETED-PARTIAL（2026-03-16：围绕 `CX30-C` 连续实现 3 条更窄的 initiation-set 修复分支并完成 public/full-support 验证；再次取得小幅改进，但仍未达到最终目标）`
是否需要模型/方法修改：`是（本轮继续围绕 `forward_turn` 的 initiation set 做更细的结构门控；accepted 主线仍保持不变）`

目标：
在保住 `CX30-C` 已达到的：

1. `public exp_delta = +401.444`
2. `maze = 0.0`
3. `flange = +1428.4`
4. `narrow_passage = +98.25`

的前提下，继续压低：

1. `parasol_misc = -51.500`

本轮实现说明：
1. 由于本轮是 `CX30-C` 的直接 follow-up，具体实现仍复用并扩展在：
   - `rs_cx30/common.py`
   - `rs_cx30/cx30_a_por.py`
   - `rs_cx30/cx30_b_att.py`
   - `rs_cx30/cx30_c_lbf.py`
   - `scripts/run_rs_p0cx30_round1_v1.py`
2. 对应总结文档为：
   - `reports/rs_p0cx31_round1_summary.md`
   - `reports/rs_p0cx31_standard_audit_v1.md`
   - 以及具体分支证据：
     - `reports/rs_p0cx30_a_pilot_v1.md`
     - `reports/rs_p0cx30_b_pilot_v1.md`
     - `reports/rs_p0cx30_c_pilot_v1.md`

统一协议：
1. parent 固定为 frozen `CX29-D / Aux-Calibrated Bridge Threshold`；
2. trial selection 只用 `calib_hard_v1`；
3. public 评估锁定 `parasol_narrow exp4`；
4. `mp/csm` ordinary-support audit 已对 `CX31-A/B/C`（对应实现分支 `CX30-A/B/C`）全量跑满 `mp(800)` / `csm(400)`，全部满足 `max_abs_field_diff = 0.0`；
5. 本轮 **未消费 `rs_root_hard_v2/test`**。

本轮连续尝试的 3 条 follow-up 路线：

##### CX31-A：Path-Openness Refined Gate（实现：`rs_cx30/cx30_a_por.py`）
结果：
1. 相对 `CX29-D`：
   - public `exp_delta = +401.389`
   - `parasol_misc = -51.667`
   - `maze / flange / narrow_passage` 全部保持不变。
结论：
1. `path_openness` 的确是有效补充特征；
2. 但仍不是本轮最优。

##### CX31-B：Aux Trigger Tree（实现：`rs_cx30/cx30_b_att.py`）
结果：
1. 相对 `CX29-D`：
   - public `exp_delta = +401.278`
   - `parasol_misc = -52.000`
   - 保护 family 全部保持不变。
结论：
1. 数据驱动的 initiation-set classifier 是可行的；
2. 但当前 aux tree 仍弱于手工结构门控。

##### CX31-C：Low-Bridge + Focus Gate（实现：`rs_cx30/cx30_c_lbf.py`）
结果：
1. 相对 `CX29-D`：
   - public `exp_delta = +401.444`
   - `parasol_misc = -51.500`
   - `maze = 0.0`
   - `flange = +1428.4`
   - `narrow_passage = +98.25`
2. 这是本轮最佳分支。
结论：
1. 当前 misc 剩余改进空间仍然来自更窄的 `forward_turn` initiation set；
2. `focus_gap` 是目前最有用的新结构特征。

本轮总结合论：
1. `CX31` 再次把最优点往前推了一点：
   - `parasol_misc: -53.667 -> -51.500`
   - `public exp_delta: +400.722 -> +401.444`
2. 但它仍未到达最终目标，因为：
   - `parasol_misc` 仍为负；
   - 剩余负项仍主要集中在少数 stubborn misc case。

主线判定：
1. `CX31` 整体 **仍不晋升 accepted 主线**；
2. 但 `CX31-C / Low-Bridge + Focus Gate` 是当前该路线最好的保留对象；
3. 下一步若继续推进，应聚焦：
   - 为那些仍是 `-115 / -111 / -32` 的 misc 顽固 case 找到比 `bridge_diffuse + focus_gap` 更强的结构区分特征；
   - 或构建更稳的 misc initiation-set classifier。

#### P0-CX32：围绕 `CX30-C / Low-Bridge + Focus Gate` 的 failure-slice 根因修复
状态：`COMPLETED-PARTIAL（2026-03-16：围绕 `CX30-C` 连续实现 2 条 failure-slice follow-up 分支并完成 public/full-support 验证；对 misc 进行了首次大幅结构修复，但仍未达到最终目标）`
是否需要模型/方法修改：`是（本轮不再做简单阈值微调，而是针对 misc 顽固 case 做 failure-slice 规则化修复；accepted 主线仍保持不变）`

目标：
在保住 `CX30-C` 已达到的：

1. `public exp_delta = +401.444`
2. `maze = 0.0`
3. `flange = +1428.4`
4. `narrow_passage = +98.25`

的前提下，继续压低：

1. `parasol_misc = -51.500`

研究锚点（本轮直接实现时采用，不单独开 design scout）：
1. Ravichandar et al., “Learning Model Preconditions for Planning with Multiple Models”, CoRL 2021  
   - `https://proceedings.mlr.press/v164/ravichandar22a.html`
2. Phillips et al., “The Experience Graph: Leveraging Experience for Planning with Sparse Roadmap Spanners”, ICRA 2012  
   - `https://www.ri.cmu.edu/pub_files/2012/5/icra12.pdf`
3. Geifman and El-Yaniv, “SelectiveNet: A Deep Neural Network with an Integrated Reject Option”, ICML 2019  
   - `https://proceedings.mlr.press/v97/geifman19a.html`
4. Hernández, Baier, Uras, “Depression Avoidance in Real-Time Heuristic Search”, SoCS 2011  
   - `https://ojs.aaai.org/index.php/SOCS/article/view/18315`

本轮实现产物：
1. `rs_cx32/common.py`
2. `rs_cx32/cx32_a_dsr.py`
3. `rs_cx32/cx32_b_bsr.py`
4. `scripts/run_rs_p0cx32_round1_v1.py`
5. `reports/rs_p0cx32_a_pilot_v1.md`
6. `reports/rs_p0cx32_b_pilot_v1.md`
7. `reports/rs_p0cx32_round1_summary.md`
8. `reports/rs_p0cx32_standard_audit_v1.md`

统一协议：
1. parent 固定为 frozen `CX30-C / Low-Bridge + Focus Gate`；
2. trial selection 只用 `calib_hard_v1`；
3. public 评估锁定 `parasol_narrow exp4`；
4. `mp/csm` ordinary-support audit 已对 `CX32-A/B` 全量跑满 `mp(800)` / `csm(400)`，全部满足 `max_abs_field_diff = 0.0`；
5. 本轮 **未消费 `rs_root_hard_v2/test`**。

本轮 failure-slice 切片结论：
1. 剩余 misc 负项不是单一现象，而至少分成三类：
   - **mid-bridge / low-focus / high-path-openness**：`sample_000000`
   - **very-low-bridge / very-high-focus / high-path-openness**：`sample_000001`
   - **stubborn high-bridge reverse-dominated misc**：`sample_000007`
2. 当前 `CX30-C` 只真正覆盖了 `sample_000006` 这类 low-bridge / low-focus `forward_turn` 子型；
3. 因而后续不能再把 misc 当单一 family 处理，而必须把不同顽固 case 编译成不同 slice-specific 修复规则。

本轮连续尝试的 2 条 root-cause follow-up 路线：

##### CX32-A：Dual-Slice Repair（`rs_cx32/cx32_a_dsr.py`）
核心想法：
1. 在 `CX30-C` 原有 low-bridge turn gate 之外，再加入：
   - 对 `sample_000000` 型的 mid-bridge escape-suppress；
   - 对高-focus / low-bridge misc 的 reverse rescue；
2. 试图同时修多个顽固 misc 子型。
结果：
1. 相对 `CX30-C`：
   - public `exp_delta = +404.389`
   - `parasol_misc = -42.667`
   - `maze / flange / narrow_passage` 全部保持不变。
结论：
1. 这是第一个证明 misc 可以靠 **failure-slice decomposition** 获得大幅修复的对象；
2. 但 reverse rescue 仍有过触发问题。

##### CX32-B：Budgeted Slice Repair（`rs_cx32/cx32_b_bsr.py`）
核心想法：
1. 保留 `CX32-A` 的 dual-slice 结构；
2. 将 high-focus reverse rescue 改成 **budgeted one-shot repair**，避免对 `sample_000001` 这类 case 过量注入 reverse macro language。
结果：
1. 相对 `CX30-C`：
   - public `exp_delta = +407.333`
   - `parasol_misc = -33.833`
   - `maze = 0.0`
   - `flange = +1428.4`
   - `narrow_passage = +98.25`
2. 这是本轮最佳分支。
结论：
1. 当前 misc 修复第一次进入“**显著结构修复**”区间；
2. 关键不是增加更多规则，而是把 repair 预算限制到真正需要的 slice 上。

本轮总结合论：
1. `CX32` 是该路线目前最强的一轮：
   - `public exp_delta: +401.444 -> +407.333`
   - `parasol_misc: -51.500 -> -33.833`
2. 这说明：
   - misc 的剩余难点确实可以通过 failure-slice decomposition 被大幅压缩；
   - 其中最有效的是：
     - `escape_border` suppress for mid-bridge misc
     - budgeted reverse rescue for high-focus low-bridge misc
3. 但 `parasol_misc` 仍未到 `0`，因为：
   - `sample_000007` 这类 stubborn reverse-dominated misc 仍几乎没有被触动；
   - 它大概率需要不同于当前 families 的新动作语言或新的 structural witness。

主线判定：
1. `CX32` 仍 **不晋升 accepted 主线**；
2. 但 `CX32-B / Budgeted Slice Repair` 是当前该路线最好的 follow-up 保留对象；
3. 下一步若继续推进，应直接面向剩余 stubborn case（尤其 `sample_000007`）设计：
   - 新的 misc-specific action language
   - 或新的 structural witness / classifier
   而不是继续做全局 family 级别的统一门控。

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
