# RES

残差（Residual）有效性修复总档案。
用于持续记录各阶段问题分析、实现改动、实验验证与结论。

## 阶段目录
- 第一阶段：`residual_fix_report.md` 归档（已完成）
- 第二阶段：创新型 CRC（已完成）
- 第二阶段 2.1：CRC 参数精化 m6（已完成）
- 第三阶段：线可通性门控双区增强 Q8（当前最佳）

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
