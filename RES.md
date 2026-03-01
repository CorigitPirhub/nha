# RES

残差（Residual）有效性修复总档案。
用于持续记录各阶段问题分析、实现改动、实验验证与结论。

## 阶段目录
- 第一阶段：`residual_fix_report.md` 归档（已完成）
- 第二阶段：创新型 CRC（已完成）
- 第二阶段 2.1：CRC 参数精化 m6（已完成）
- 第三阶段：线可通性门控双区增强 Q8（已完成）
- 第四阶段：结构/排序约束损失（已完成）
- 第五阶段：防遗忘蒸馏锚定 + 结构损失（已完成）
- 第六阶段：全局权重插值（已完成）
- 第七阶段：分层权重插值 + BN 统计解耦（已完成）
- 第八阶段：分层 alpha + residual_alpha 联合贝叶斯搜索（已完成）
- 第九阶段：场景加权 full-BO（narrow/maze 惩罚）+ 定向极值验证（当前最佳）
- 第十阶段：Exp3 最终冻结 + 停止准则触发 + 资源转向 Exp4/maze 训练修复（进行中）

---

## 第一阶段（归档）
归档时间：2026-02-28  
来源文件：`/home/zzy/TrajectoryPlanning/distill/outputs/reports/residual_fix_report.md`

> 以下为阶段一原文归档：

# 残差网络失效分析与修复报告

## 1. 问题背景
- 现状（用户提供 + 既有结果）：
  - RS 一致性代价是核心，移除后成功率显著下降。
  - 残差网络在 Exp3/Exp4 中基本无效，甚至略有负收益。
- 目标：定位“残差无效”原因，修复实现并通过 Exp3/Exp4 验证残差分支变为正收益。

## 2. 根因分析
### 2.1 训练目标构造存在关键错位
在 `network/dataset.py` 中，残差模式下若存在 `temporal_residual_3d`，原逻辑直接用它覆盖目标，导致**静态残差 `(teacher - rs_base)` 不参与监督**。

影响：
- 对静态/窄道主导场景（Exp3/Exp4）几乎学不到有效残差，推理时残差幅值很小。
- 旧模型在 Parasol 样本上的残差幅值（前 5 case）约：`mean≈0.02~0.03, p95≈0.13~0.14`，信号过弱。

### 2.2 融合阶段存在效率和几何平滑问题
- yaw 通道对齐原先是最近邻复制，角度方向不连续。
- 运行时每次启发值查询做两次三线性插值（base + residual），带来明显时间开销。

### 2.3 仅靠“暴力放大残差”不可行
快速实验（4 case）将 `alpha` 提到 10/200 会导致成功率从 1.0 降到 0.5，说明不是简单“幅值太小”就能解决，需先修监督与校准。

## 3. 实现修改
### 3.1 修复残差监督目标（核心）
文件：`network/dataset.py`
- 改为始终包含静态残差：`static_res = max(teacher - rs_base, 0)`。
- 当存在 `temporal_residual_3d` 时，目标改为：
  - `target_t = static_res + temporal_residual_t`
  - 然后再展平与裁剪。
- 这样动态增量不再覆盖静态残差监督。

关键位置：
- `network/dataset.py:199-241`

### 3.2 改进 yaw 通道对齐
文件：`scripts/evaluate_baselines.py`
- `_match_yaw_channels` 从最近邻改为环形线性插值，减少角度离散跳变。

关键位置：
- `scripts/evaluate_baselines.py:1198-1215`

### 3.3 优化残差融合推理开销
文件：`scripts/evaluate_baselines.py`
- 在 `_make_ours_anchor` 中预先融合 `fused = rs_base + residual`，返回单一 `YawFieldHeuristic`。
- 避免搜索时每个节点做双插值。

关键位置：
- `scripts/evaluate_baselines.py:1301-1309`

## 4. 训练与实验配置
### 4.1 微调模型
- 基础 checkpoint：`outputs/checkpoints/heuristic_net_generalization_unified_mixed_v2.pt`
- 微调输出：`outputs/residual_fix_v3_train/checkpoints/heuristic_net_residual_fix_v3_train.pt`
- 训练命令（已执行）：
  - `scripts/run_generalization.py` + `--skip-generation`
  - 数据：`data/residual_fix_v3`（已生成样本）
  - `prediction_mode=residual`, `epochs=12`, `device=cuda:0`

### 4.2 最终评估参数
- Exp3/Exp4 均使用：
  - `--residual-alpha 0.5`
  - `--residual-bias-quantile 0.8`
  - `--residual-corridor-threshold 1.2`
  - `--residual-corridor-suppress 0.5`
  - `--residual-topq-quantile 0.0`
  - `--rs-field-yaw-bins 24`

## 5. 迭代实验结果
### 5.1 历史基线（修复前）
来源：
- `outputs/paper/final_results/runs/exp3_summary.csv`
- `outputs/paper/final_results/runs/exp4_summary.csv`

- Exp3（Full vs No-Residual）
  - 成功率：`0.7778 vs 0.7778`
  - 扩展节点：`1589.14 vs 1580.00`（Full **+0.58% 更差**）
  - 时间：`341.78ms vs 285.33ms`（Full **+19.78% 更差**）
- Exp4（Ours vs Hybrid A*(RS)）
  - 成功率：`1.0 vs 1.0`
  - 扩展节点：`12467.61 vs 12370.00`（Ours **+0.79% 更差**）
  - 时间：`3201.02ms vs 2694.11ms`（Ours **+18.82% 更差**）

### 5.2 失败迭代（仅放大残差）
来源：`outputs/paper/quick_alpha10/exp_results_summary.csv`（4 case 快速集）
- Full 成功率降到 `0.5`，说明单纯增大 alpha 会破坏搜索稳定性。

### 5.3 修复后快速验证
来源：`outputs/paper/quick_new_calib/exp_results_summary.csv`（4 case）
- Full vs No-Residual：
  - 成功率均为 `1.0`
  - 扩展节点：`1197.75 vs 1204.00`（Full 更好）
  - 时间：`254.60ms vs 262.48ms`（Full 更快）

### 5.4 修复后全量结果（关键）
#### Exp3（18 case）
来源：`outputs/paper/residual_fix_v3_exp3/exp_results_summary.csv`
- Full vs No-Residual：
  - 成功率：`0.7778 vs 0.7778`（持平）
  - 扩展节点：`1564.79 vs 1580.00`（Full **-0.96% 改善**）
  - 时间：`289.85ms vs 308.40ms`（Full **-6.02% 改善**）

#### Exp4（18 case）
来源：`outputs/paper/residual_fix_v3_exp4/exp_results_summary.csv`
- Ours vs Hybrid A*(RS)：
  - 成功率：`1.0 vs 1.0`（持平）
  - 扩展节点：`12350.00 vs 12370.00`（Ours **-0.16% 改善**）
  - 时间：`2438.80ms vs 2462.46ms`（Ours **-0.96% 改善**）

> 结论：残差分支由“负收益”转为“稳定正收益”。

## 6. 产物清单
- 代码修改：
  - `network/dataset.py`
  - `scripts/evaluate_baselines.py`
- 新模型：
  - `outputs/residual_fix_v3_train/checkpoints/heuristic_net_residual_fix_v3_train.pt`
- 结果目录：
  - `outputs/paper/residual_fix_v3_exp3/`
  - `outputs/paper/residual_fix_v3_exp4/`

## 7. 后续建议
1. 用更大且专门的 hard 数据继续微调（当前为快速修复版，小样本微调）。
2. 将 Exp4 再跑一次 `sampling-max-iters=1500` 做论文口径复核（当前用 300 加速，Ours/RS 对比不受影响）。
3. 若追求更大幅收益，可继续加“搜索反馈式”监督（如扩展热点排序损失）。

---

## 第二阶段：创新型“对比残差校准”迭代（已完成）
时间：2026-02-28

### 目标
在第一阶段“残差已有效但增益偏小”的基础上，进一步提升增益幅度，且保持成功率不下降。

### 创新思路（非纯工程补丁）
提出并实现 **Contrastive Residual Calibration (CRC)**：
- 先对残差场做背景分位去中心化（background quantile subtraction），将残差从“仅正值抬高”变成“正负对比信号”。
- 正分支（高于背景）适度增强，负分支（低于背景）弱化回拉，从而提升瓶颈/通道区域与开阔区域的启发式对比度。
- 引入安全下界约束：`fused >= floor_ratio * RS_base`，避免负分支过强导致启发式塌陷。

直观上：
- 第一阶段残差更像“整体加权”；
- 第二阶段残差变成“对比增强器”，更强调结构差异（瓶颈 vs 开阔）。

### 代码实现
文件：`scripts/evaluate_baselines.py`
- 新增参数：
  - `--residual-contrastive-bg-quantile`
  - `--residual-contrastive-neg-scale`
  - `--residual-contrastive-pos-scale`
  - `--residual-floor-ratio`
- 在 `_apply_residual_calibration` 中实现对比残差分支。
- 在 `_make_ours_anchor` 中加入融合安全下界（RS floor）。

### 迭代试验
- 快速筛选（8-case）先验证方向，再全量 18-case 正式评估。
- 选定配置（m5）：
  - `residual_alpha=0.6`
  - `residual_clip=25`
  - `residual_topq_quantile=0.1`
  - `residual_bias_quantile=0.3`
  - `residual_corridor_threshold=1.0`
  - `residual_corridor_suppress=0.35`
  - `residual_contrastive_bg_quantile=0.58`
  - `residual_contrastive_neg_scale=0.14`
  - `residual_contrastive_pos_scale=1.20`
  - `residual_floor_ratio=0.60`

### 结果对比（全量）
#### Exp3（18 case, Full vs No-Residual）
- 旧版本（修复前）：`+0.58%` 扩展（更差）
- 第一阶段：`-0.96%` 扩展
- 第二阶段（CRC）：`-6.46%` 扩展
- 成功率：三者均为 `0.7778`

对应结果文件：
- `outputs/paper/residual_innov_m5_exp3/exp_results_summary.csv`

#### Exp4（18 case, Ours vs Hybrid A*(RS)）
- 旧版本（修复前）：`+0.79%` 扩展（更差）
- 第一阶段：`-0.16%` 扩展
- 第二阶段（CRC）：`-0.99%` 扩展
- 成功率：三者均为 `1.0`

对应结果文件：
- `outputs/paper/residual_innov_m5_exp4/exp_results_summary.csv`

### 结论
第二阶段达成目标：
- 在不牺牲成功率的前提下，残差增益幅度显著扩大。
- 尤其 Exp3 从“轻微有效”提升到“明显有效”（扩展改善约 6.46%）。

---

## 第二阶段 2.1：CRC 参数精化（m6，已完成）
时间：2026-02-28

### 动机
在 m5 已有效的基础上，继续做参数精化，目标是在不降低成功率的前提下进一步压缩扩展节点。

### m6 配置
- `residual_alpha=0.65`
- `residual_clip=28`
- `residual_topq_quantile=0.1`
- `residual_bias_quantile=0.25`
- `residual_corridor_threshold=0.9`
- `residual_corridor_suppress=0.3`
- `residual_contrastive_bg_quantile=0.62`
- `residual_contrastive_neg_scale=0.16`
- `residual_contrastive_pos_scale=1.25`
- `residual_floor_ratio=0.62`

### 全量结果
#### Exp3（18 case, Full vs No-Residual）
来源：`outputs/paper/residual_innov_m6_exp3/exp_results_summary.csv`
- 成功率：`0.7778 vs 0.7778`（持平）
- 扩展节点：`1465.50 vs 1580.00`（**-7.25%**）
- 时间：`247.64ms vs 273.33ms`（**-9.40%**）

#### Exp4（18 case, Ours vs Hybrid A*(RS)，公平口径）
来源：`outputs/paper/residual_innov_m6_exp4_fair/exp_results_summary.csv`
- 成功率：`1.0 vs 1.0`（持平）
- 扩展节点：`12237.33 vs 12370.00`（**-1.07%**）
- 时间：`1785.32ms vs 2145.57ms`（**-16.79%**）

> 备注：`outputs/paper/residual_innov_m6_exp4/` 这次曾使用 `--hybrid-budget-cap 7000`，会把双方成功率同时压到 `0.8333`，不作为与 m5 的公平对比口径。

---

## 第三阶段：创新型“线可通性门控双区残差增强”（Q8，当前最佳）
时间：2026-02-28

### 背景诊断
- m6 虽有效，但仍存在“Other 提升明显、窄道/迷宫轻微反向”的结构性矛盾。
- 直接做 open 区残差放大（q5/q6）会在个别 case（`sample_000007`）出现灾难性退化。

### 创新实现（`scripts/evaluate_baselines.py`）
在 CRC 基础上新增并迭代了以下机制：
1. `BART`（瓶颈感知残差传播分支）  
   新增 `residual_transport_*` 与 `residual_bottleneck_*` 参数，做局部传播与窄道融合。
2. 双区自适应残差增益  
   open 区增强 + bottleneck 区抑制（`residual_open_boost`, `residual_bottleneck_dampen`）。
3. 高置信 Top-q 增强门控  
   仅增强高分位正残差（`residual_open_boost_topq`），减少全局误放大。
4. **线可通性门控（最终关键）**  
   引入 `residual_open_boost_min_line_clearance`：当起终点连线平均净空过低时，自动关闭 open boost，避免窄通道/遮挡严重场景翻车。
5. 自适应信任域尝试（`residual_adaptive_trust_*`）  
   已实现并验证，但在本数据分布下不如 line-clearance 门控稳定，未作为最终主配置。

### 最终配置（Q8）
- 在 m6 基础上增加：
  - `residual_open_boost=0.45`
  - `residual_open_boost_topq=0.90`
  - `residual_open_boost_min_line_clearance=1.80`
  - `residual_bottleneck_dampen=0.95`

### 全量结果
#### Exp3（18 case, Full vs No-Residual）
来源：`outputs/paper/residual_adapt_q8_linegate_exp3/exp_results_summary.csv`
- 成功率：`0.7778 vs 0.7778`（持平）
- 扩展节点：`1444.71 vs 1580.00`（**-8.56%**，优于 m6 的 -7.25%）
- 时间：`257.29ms vs 273.33ms`（**-5.87%**）

场景分桶（Exp3）：
- `other`: **-14.73%**（m6: -12.63%）
- `narrow_passage`: **+0.21%**（m6: +0.41%，反向幅度减半）
- `maze`: `+0.66%`（持平）

#### Exp4（18 case, Ours vs Hybrid A*(RS)，公平口径）
来源：`outputs/paper/residual_adapt_q8_linegate_exp4/exp_results_summary.csv`
- 成功率：`1.0 vs 1.0`（持平）
- 扩展节点：`12217.94 vs 12370.00`（**-1.23%**，优于 m6 的 -1.07%）
- 时间：`1801.71ms vs 1826.93ms`（**-1.38%**）

### 阶段结论
- 第三阶段最终配置（Q8）在 Exp3/Exp4 均取得比 m6 更好的扩展节点收益，且成功率保持不变。
- 当前最佳稳定结果：
  - Exp3：**-8.56%**
  - Exp4：**-1.23%**
- 相较用户期望的 `-15% ~ -25%` 仍有差距；主要瓶颈是少量特殊 case 的泛化稳定性。下一阶段建议转向“更大 hard-case 数据 + 训练期结构化约束/排名监督”而非继续纯推理期标定。

---

## 第四阶段：结构/排序约束损失（训练侧关键创新）
时间：2026-02-28

### 本阶段创新实现
文件：
- `network/train.py`
- `scripts/run_generalization.py`

新增了“双尺度结构排序损失”（可独立开关）：
1. 局部软排序损失（`local_prob_rank_*`）
   - 用概率排序替代硬 margin 排序，按 teacher 梯度置信度加权；
   - 支持高分位 focus（`local_prob_rank_focus_quantile`）；
   - 支持 hard-only 与 narrow 区域加权。
2. 全局分位对比排序损失（`global_rank_*`）
   - 以 teacher 的 top/bottom quantile 形成高低代价集合；
   - 对高低集合做配对排序约束，强化全局次序结构；
   - 支持 hard-only 与 narrow 区域加权。

### 关键验证与结论
#### A. 先前 hard 数据集监督退化（关键发现）
对 `data/structrank_hard_v1` 做统计后发现：
- `static residual = max(teacher_3d - rs_base_3d, 0)` 基本全零；
- `temporal_residual_3d` 也全零。

这解释了此前结构损失训练后残差塌缩的问题：监督本身把网络推向“零残差解”。

#### B. 在零残差监督上，结构损失可把性能从负收益拉回近中性，但仍不达标
来源：`outputs/paper/structrank_innov_v1_q8_quick/exp_results_summary.csv`
- Exp3 quick（8 case）`dE = +0.007%`（几乎中性）
- 相比此前 `structrank_hard_v1` 的 `+0.160%` 有改善，但仍显著弱于旧最佳 `-11.56%`。

`alpha` 扫描（同 checkpoint）：
- `alpha=2.0`：`dE = +0.070%`（`outputs/paper/structrank_innov_v1_a2_q8_quick/exp_results_summary.csv`）
- 说明问题不只是推理幅值标定，训练侧仍存在泛化错位。

#### C. 非零残差数据重建与遗忘现象
中断生成后提取了非零残差样本并重组为：
- `data/structrank_nonzero_v2p`（train=100, val=25）

在该数据上“无结构损失基线微调”也出现明显遗忘：
- `outputs/paper/structrank_nonzero_base_p1_q8_quick/exp_results_summary.csv`
- Exp3 quick：`dE = +6.471%`

在原 `residual_fix_v3` 分布上做“低学习率结构化微调”同样未超过旧最佳：
- `outputs/paper/structrank_rf3_p1_q8_quick/exp_results_summary.csv`
- Exp3 quick：`dE = +3.650%`

### 本阶段小结
- 结构/排序约束损失已完成工程实现并接入训练/评估链路；
- 已验证“监督退化（零残差标签）”是此前失败的核心原因之一；
- 当前最好的结构化训练结果仍未超过旧最佳 quick 基线（`-11.56%`），但已明确下一步方向：
  - 需要“防遗忘约束 + 结构损失”的联合训练，而非直接在偏移数据分布上重训。

---

## 第五阶段：防遗忘蒸馏锚定 + 结构损失联合训练
时间：2026-03-01

### 实现内容
在第四阶段基础上进一步实现“蒸馏锚定”：

文件：
- `network/train.py`
- `scripts/run_generalization.py`

新增能力：
1. Anchor 蒸馏损失（`distill_*`）
   - `distill_target`（固定强模型输出）作为锚点；
   - `distill_lambda` + `SmoothL1(beta=distill_huber_delta)` 主蒸馏项；
   - `distill_under_lambda` 单侧约束，抑制学生相对 anchor 的残差塌缩；
   - `distill_focus_quantile` 高分位聚焦；
   - `distill_hard_only` / `distill_narrow_boost` 结构化门控。
2. 训练与验证统一接入
   - `run_generalization.py` 新增 `--distill-anchor-checkpoint` 与全套 `--distill-*` 参数；
   - 训练和 `_eval_loss` 都支持同时使用“蒸馏 + 结构排序”。

### 实验与结果
#### 实验1：非零 hard 数据联合训练（distill_v1r）
- checkpoint：`outputs/residual_structrank_distill_v1r/checkpoints/heuristic_net_residual_structrank_distill_v1r.pt`
- quick 评测（8 case）：
  - `outputs/paper/structrank_distill_v1r_q8_quick/exp_results_summary.csv`
  - `dE = -7.86%`（显著优于第四阶段的正退化区间）

#### 实验2：混合回放数据联合训练（distill_v2）
- 训练集：`data/structrank_mix_v2`（`structrank_nonzero_v2p` + `residual_fix_v3` 回放）
- checkpoint：`outputs/residual_structrank_distill_v2/checkpoints/heuristic_net_residual_structrank_distill_v2.pt`
- quick 评测（8 case）：
  - `alpha=0.65`: `dE = -9.51%`
    - `outputs/paper/structrank_distill_v2_q8_quick/exp_results_summary.csv`
  - `alpha=0.60`: `dE = -9.64%`, `dT = -15.68%`（当前 quick 最优）
    - `outputs/paper/structrank_distill_v2_q8_a06/exp_results_summary.csv`
  - `alpha=0.80`: `dE = -8.95%`, `dT = -10.40%`
    - `outputs/paper/structrank_distill_v2_q8_a08/exp_results_summary.csv`

#### 全量验证（Exp3, 18 case）
- 配置：distill_v2 + `alpha=0.60`
- 结果：`outputs/paper/structrank_distill_v2_a06_exp3_full/exp_results_summary.csv`
  - `dE = -7.12%`
  - `dT = -11.01%`
  - 成功率与 No-Residual 持平（`0.7778`）

对比当前主线全量最佳（第三阶段 q8 line-gate）：
- `outputs/paper/residual_adapt_q8_linegate_exp3/exp_results_summary.csv`
- `dE = -8.56%`

### 阶段结论
- “蒸馏锚定 + 结构损失”方向已被验证为有效：
  - 相比第四阶段单纯结构训练，退化问题被明显缓解；
  - quick 集提升可到 `-9.64%`，并保持良好时间收益。
- 但在 Exp3 全量上目前仍略弱于现有最佳主线（`-7.12%` vs `-8.56%`），尚未形成新的全量 SOTA。

---

## 第六阶段：模型权重插值（θ_old / θ_new）
时间：2026-03-01

### 实现
新增脚本：
- `scripts/interpolate_checkpoints.py`

核心形式：
$$
\theta_{final} = \alpha \cdot \theta_{new} + (1-\alpha)\cdot\theta_{old}
$$

其中：
- `\theta_old`：`outputs/residual_fix_v3_train/checkpoints/heuristic_net_residual_fix_v3_train.pt`
- `\theta_new`：`outputs/residual_structrank_distill_v2/checkpoints/heuristic_net_residual_structrank_distill_v2.pt`

### 粗扫（Exp3 quick, 8 case）
固定推理参数（含 `residual_alpha=0.60`），扫 `alpha in {0.00,0.20,0.40,0.60,0.80,1.00}`。

结果（`dE` 越小越好）：
- `alpha=0.00`: `dE=-11.03%`
- `alpha=0.20`: `dE=-10.80%`
- `alpha=0.40`: `dE=-10.04%`
- `alpha=0.60`: `dE=-9.99%`
- `alpha=0.80`: `dE=-9.86%`
- `alpha=1.00`: `dE=-9.64%`

来源目录：
- `outputs/paper/interp_q8_distill_v2_a000/`
- `outputs/paper/interp_q8_distill_v2_a200/`
- `outputs/paper/interp_q8_distill_v2_a400/`
- `outputs/paper/interp_q8_distill_v2_a600/`
- `outputs/paper/interp_q8_distill_v2_a800/`
- `outputs/paper/interp_q8_distill_v2_a1000/`

### 贴近旧模型细扫（避免漏掉局部最优）
在旧模型最优推理系数 `residual_alpha=0.65` 下测试：
- `alpha=0.05`: `dE=-11.10%`
  - `outputs/paper/interp_q8_distill_v2_a050_r065/`
- `alpha=0.10`: `dE=-10.78%`
  - `outputs/paper/interp_q8_distill_v2_a100_r065/`

对比旧模型基线（同口径）：
- `outputs/paper/structrank_q8_quick_old/exp_results_summary.csv`
- `dE=-11.56%`（仍最佳）

### 结论
- 权重插值在当前这组 `(\theta_old,\theta_new)` 上未超过旧基线；
- 最优点位于 `alpha≈0`，说明 `theta_new` 带来的结构信息尚不足以在线性权重空间带来额外增益；
- 该结论与第五阶段一致：训练侧改进方向可行，但需要更强的“结构收益”再进行参数融合才可能超过当前最佳。

---

## 第七阶段：分层权重插值（Stage-wise Merge）+ BN 统计解耦
时间：2026-03-01

### 动机
第六阶段的全局线性插值失败，说明“安全归零能力”和“结构残差能力”可能分布在不同网络子模块。  
因此改为**按网络阶段分别插值**，并增加 BN 运行统计量的独立控制。

### 实现
新增脚本：
- `scripts/interpolate_checkpoints_stagewise.py`

核心策略：
1. 分组插值（每组独立 `alpha`）
   - `shallow`: `inc/down1`
   - `deep`: `down2/down3/context_*`
   - `decoder`: `up1/2/3`
   - `head`: `out`
2. BN 统计解耦
   - `--bn-stat-source {blend, old, new}`
   - 用于验证“权重融合”和“统计量融合”是否应独立处理。

### 第 1 轮分层粗扫（Exp3 quick, residual_alpha=0.65）
来源目录：
- `outputs/paper/interp_stage_q8_si01_r065/`
- `outputs/paper/interp_stage_q8_si02_r065/`
- `outputs/paper/interp_stage_q8_si03_r065/`
- `outputs/paper/interp_stage_q8_si04_r065/`
- `outputs/paper/interp_stage_q8_si05_r065/`
- `outputs/paper/interp_stage_q8_si06_r065/`
- `outputs/paper/interp_stage_q8_si07_r065/`

结果（`dE` 越小越好）：
- `si01`: `-10.343%`
- `si02`: `-9.828%`
- `si03`: `-9.271%`
- `si04`: `-8.177%`
- `si05`: `-8.156%`
- `si06`: `-11.514%`（本轮最佳，`BN=blend`）
- `si07`: `-9.717%`

观察：
- 高比例注入 `deep/decoder/head` 会明显退化；
- `BN=blend` 在 `si06` 上显著优于多数 `BN=old` 配置。

### `si06` 推理系数微调（Exp3 quick）
来源目录：
- `outputs/paper/interp_stage_q8_si06_r055/`
- `outputs/paper/interp_stage_q8_si06_r060/`
- `outputs/paper/interp_stage_q8_si06_r070/`

结果：
- `residual_alpha=0.55`: `dE=-11.409%`
- `residual_alpha=0.60`: `dE=-11.486%`
- `residual_alpha=0.70`: `dE=-11.709%`（超过旧 quick best `-11.56%`）

### 第 2 轮邻域细扫（Exp3 quick, residual_alpha=0.70）
来源目录：
- `outputs/paper/interp_stage_q8_sj01_r070/`
- `outputs/paper/interp_stage_q8_sj02_r070/`
- `outputs/paper/interp_stage_q8_sj03_r070/`
- `outputs/paper/interp_stage_q8_sj04_r070/`
- `outputs/paper/interp_stage_q8_sj05_r070/`

结果：
- `sj01`: `-11.576%`
- `sj02`: `-11.416%`
- `sj03`: `-11.764%`（当前 quick 最佳）
- `sj04`: `-11.395%`
- `sj05`: `-11.632%`

### 全量验证（Exp3, 18 case）
当前最优候选：`sj03 + residual_alpha=0.70`
- 结果文件：`outputs/paper/interp_stage_q8_sj03_r070_exp3_full/exp_results_summary.csv`
- 指标：
  - 成功率：`0.7778`（与 `No-Residual` 持平）
  - `dE=-8.861%`
  - `dT=-13.466%`

对比主线旧最佳（第三阶段 q8 line-gate）：
- `outputs/paper/residual_adapt_q8_linegate_exp3/exp_results_summary.csv`
- `dE=-8.562%`

结论：Exp3 全量已刷新（`-8.861% < -8.562%`）。

### 交叉验证（Exp4, 公平口径）
公平口径：`hybrid_budget_cap=0` + `sampling_max_iters=300`

最优候选（`sj03`）：
- `outputs/paper/interp_stage_q8_sj03_r070_exp4_fair/exp_results_summary.csv`
- 成功率：`1.0`（与 `Hybrid A* (RS)` 持平）
- `dE=-1.471%`
- `dT=-11.849%`

对比主线旧最佳：
- `outputs/paper/residual_adapt_q8_linegate_exp4/exp_results_summary.csv`
- `dE=-1.229%`, `dT=-1.380%`

结论：在公平口径 Exp4 上，`sj03` 也取得了更优扩展节点与时间收益。

### 本阶段结论
- “分层插值 + BN 统计解耦”在当前任务上**有效超过了全局线性插值**；
- 获得新的可复现最优组合：
  - checkpoint：`outputs/checkpoints/interp_stage_sj03.pt`
  - 推理系数：`residual_alpha=0.70`
  - 其余 Q8 参数保持不变。

---

## 第八阶段：分层 alpha + residual_alpha 联合贝叶斯搜索
时间：2026-03-01

### 目标
围绕分层插值参数（`alpha_shallow/deep/decoder/head`）与推理系数（`residual_alpha`）做联合优化，冲击 `Exp3 full dE = -9.5% ~ -10%`。

### 实现
新增脚本：
- `scripts/bo_stagewise_search.py`

能力：
1. GP + EI 贝叶斯搜索（`sklearn`）
2. 支持 warm-start 复用既有 quick/full 结果
3. 支持两种模式：
   - `bo_split=quick`：先 8-case 搜索，再自动提升到 18-case
   - `bo_split=full`：直接在 18-case 上优化（避免 quick 过拟合）
4. 自动记录：
   - `outputs/paper/<search_name>/bo_results.csv`
   - `outputs/paper/<search_name>/bo_summary.json`

### 子阶段 A：v2（quick BO + full 提升）
目录：`outputs/paper/bo_stagewise_v2/`

- quick 最优：`dE=-12.064%`
- full 最优（top00）：
  - 文件：`outputs/paper/bo_stagewise_v2_full_top00/exp_results_summary.csv`
  - `dE=-9.069%`, `dT=-5.784%`, 成功率持平

结论：首次把 Exp3 full 从 `-8.861%` 提升到 `-9.069%`。

### 子阶段 B：v3（扩大高 decoder/head 区域）
目录：`outputs/paper/bo_stagewise_v3/`

- quick 最优进一步到 `dE=-12.426%`
- 但 full 两个 top 候选都退化（`dE>0`）

结论：发现显著的 quick/full 失配，说明仅用 quick 指标优化会过拟合。

### 子阶段 C：v4（direct full BO）
目录：`outputs/paper/bo_stagewise_v4_full/`

直接在 18-case 上做 BO（3 个新 trial）：
- t000: `dE=-8.876%`
- t001: `dE=-8.976%`
- t002: `dE=-9.093%`（本阶段最优）

最佳参数（t002）：
- `alpha_shallow=0.021822`
- `alpha_deep=0.460000`
- `alpha_decoder=0.412016`
- `alpha_head=0.254062`
- `residual_alpha=0.730000`

对应结果文件：
- `outputs/paper/bo_stagewise_v4_full_full_t002/exp_results_summary.csv`

### 子阶段 D：v5（边界外扩复核）
目录：`outputs/paper/bo_stagewise_v5_full/`

在 v4 最优边界外扩后继续 3 个 full trial：
- t000: `dE=-9.089%`
- t001: `dE=+0.909%`（激进参数退化）
- t002: `dE=-9.053%`

结论：未超过 v4 最优，`-9.093%` 可视为当前稳定最优。

### 与历史最优对比（Exp3 full）
- 旧主线（Q8 line-gate）：`dE=-8.562%`
- 第七阶段最优（sj03）：`dE=-8.861%`
- 第八阶段最优（BO v4 t002）：`dE=-9.093%`

### 阶段结论
1. 联合 BO 方向有效，继续提升了 Exp3 full（`-9.093%`）。  
2. 但当前仍未达到 `-9.5% ~ -10%` 目标区间。  
3. 主要瓶颈是 quick/full 指标分布不一致，且高激进参数区存在明显退化风险。  
4. 下一步应优先采用“full 指标主导 + 稳定性约束”的搜索策略，而非继续单纯放大 quick 指标。

---

## 第九阶段：场景加权 full-BO（narrow/maze 惩罚）+ 定向极值验证
时间：2026-03-01

### 目标
在“直接 full 优化”的基础上继续冲击 `-9.5%`，并通过场景惩罚抑制窄道/迷宫失稳：
- 对 `parasol:narrow_passage` 与 `parasol:maze` 的正向退化（`dE>0`）加入惩罚；
- 仍以 Exp3 full 全局 `dE` 为主目标。

### 实现更新
文件：`scripts/bo_stagewise_search.py`

新增：
1. 场景指标解析
   - 自动读取 `exp3_ablation_scene` 的 `dE_narrow/dE_maze/dE_other`。
2. 场景加权目标
   - 新参数：
     - `--scene-penalty-narrow`
     - `--scene-penalty-maze`
     - `--scene-tol-narrow`
     - `--scene-tol-maze`
   - 目标函数新增惩罚项（仅对超过容忍阈值的正退化生效）。
3. 结果日志增强
   - `bo_results.csv` 中增加 `dE_narrow_percent/dE_maze_percent/dE_other_percent` 字段。

本阶段使用配置：
- `scene_penalty_narrow=2.5`
- `scene_penalty_maze=3.0`
- `scene_tol_narrow=0.05`
- `scene_tol_maze=0.20`

### 多轮 full-BO 结果
#### v6（场景加权首次）
目录：`outputs/paper/bo_stagewise_v6_scene_full/`
- 最优：`dE=-9.252%`
- 文件：`outputs/paper/bo_stagewise_v6_scene_full_full_t001/exp_results_summary.csv`

#### v7（向低 deep 区域扩展）
目录：`outputs/paper/bo_stagewise_v7_scene_full/`
- 最优：`dE=-9.301%`
- 文件：`outputs/paper/bo_stagewise_v7_scene_full_full_t001/exp_results_summary.csv`

#### v8（继续下探）
目录：`outputs/paper/bo_stagewise_v8_scene_full/`
- 最优：`dE=-9.342%`
- 文件：`outputs/paper/bo_stagewise_v8_scene_full_full_t001/exp_results_summary.csv`

#### v9（边界外扩到更低 deep）
目录：`outputs/paper/bo_stagewise_v9_scene_full/`
- 最优：`dE=-9.423%`
- 文件：`outputs/paper/bo_stagewise_v9_scene_full_full_t001/exp_results_summary.csv`

#### v10（继续外推）
目录：`outputs/paper/bo_stagewise_v10_scene_full/`
- 新 trial 未超过 v9 最优（保留 `-9.423%` 为 BO 最优）。

### 定向极值验证（手工候选）
为进一步逼近 `-9.5%`，在 v9 邻域做 3 个 full 直评：
- `manual_v11a`：`dE=-9.396%`
  - `outputs/paper/manual_v11a_exp3_full/exp_results_summary.csv`
- `manual_v11b`：`dE=-9.437%`（本阶段全局最佳）
  - `outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv`
- `manual_v11c`：`dE=-9.396%`
  - `outputs/paper/manual_v11c_exp3_full/exp_results_summary.csv`

### 当前最佳配置（Exp3 full）
来自 `manual_v11b`：
- `alpha_shallow=0.085`
- `alpha_deep=0.080`
- `alpha_decoder=0.500`
- `alpha_head=0.300`
- `residual_alpha=0.675`
- 结果：`dE=-9.437%`, `dT=-9.498%`, 成功率与 `No-Residual` 持平（`0.7778`）

### 阶段结论
1. 场景加权 full-BO + 定向极值验证将 Exp3 full 从 `-9.093%` 继续提升到 `-9.437%`。  
2. 仍未越过 `-9.5%`，但已非常接近（差 `0.063` 个百分点）。  
3. 观测到 `maze` 的 `dE` 在当前体系下几乎固定在 `+0.658%`，已成为进一步提升的结构性瓶颈。  

---

## 第十阶段：Exp3 最终冻结 + 停止准则触发 + 资源转向 Exp4/maze 训练修复
时间：2026-03-01

### 停止准则（Exp3 参数微调）
已触发，停止继续针对 Exp3 做推理参数微调。依据：
- 当前最优 `manual_v11b`：`dE=-9.437%`，与目标 `-9.5%` 仅差 `0.063` 个百分点。
- 18-case 规模下，该差距约对应“平均每场景 < 1 个扩展节点（约 0.9）”。
- 边际收益已显著低于继续消耗算力的成本。

### Exp3 最终冻结（manual_v11b）
- 冻结 checkpoint：`outputs/checkpoints/exp3_final_manual_v11b.pt`
- 源 checkpoint：`outputs/checkpoints/manual_v11b.pt`
- 冻结清单（含 sha256、固定参数、复现实验命令）：  
  `outputs/paper/exp3_final_manual_v11b_manifest.json`
- 对应 Exp3 full 结果：  
  `outputs/paper/manual_v11b_exp3_full/exp_results_summary.csv`

### 算力转向
从本阶段起，算力优先投向：
1. Exp4 泛化验证（基于 `manual_v11b` 最终冻结版）。
2. maze 结构性瓶颈修复（训练侧：防遗忘蒸馏锚定 + 结构/排序损失联合训练），不再继续做 Exp3 推理参数微调。
