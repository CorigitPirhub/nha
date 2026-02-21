# 基于代价一致性与残差学习的神经启发式 Hybrid A* 规划器

生成日期：2026-02-21

## 1. 整体架构图

```mermaid
flowchart LR
    A[环境输入<br/>occupancy + start/goal + map config]

    subgraph OFF[离线训练阶段]
        B[场景与地图生成<br/>env/map_generator.py:generate_scene*]
        C[ESDF计算<br/>env/esdf.py:compute_esdf]
        D[教师信号生成<br/>env/teacher.py:compute_nonholonomic_teacher]
        E[RS一致性基线场<br/>env/dataset_builder.py:_derive_rs_base_3d]
        F[数据集构建与落盘<br/>env/dataset_builder.py:generate_*_split]
        G[数据加载/目标构造<br/>network/dataset.py:HeuristicFieldDataset]
        H[网络训练<br/>network/train.py:train_network]
        I[模型权重<br/>outputs/checkpoints/heuristic_net.pt]
    end

    subgraph ON[在线规划阶段]
        J[加载任务样本<br/>scripts/evaluate.py 或 scripts/run_demo.py]
        K[RS缓存查询<br/>env/reeds_shepp.py:load_rs_field_cache]
        L[缓存未命中则计算RS场<br/>env/reeds_shepp.py:compute_reeds_shepp_field]
        M[神经残差推理<br/>network/inference.py:NeuralHeuristicPredictor.predict_residual_field]
        N[残差融合<br/>h = h_rs + alpha * max(Delta h, 0)]
        O[启发式对象封装<br/>planner/heuristics.py:ResidualYawFieldHeuristic]
        P[Hybrid A*搜索<br/>planner/hybrid_astar.py:HybridAStarPlanner.plan]
        Q[最终轨迹输出<br/>path(x,y,yaw)]
    end

    A --> B --> C --> D --> E --> F --> G --> H --> I
    A --> J
    I --> M
    J --> K
    K -->|hit| N
    K -->|miss| L --> N
    J --> M --> N --> O --> P --> Q
    L --> O
```

## 2. 详细设计说明

### 2.1 核心设计哲学：解析引导 + 神经修正

本系统不是让网络“从零学习完整启发式”，而是采用分解式架构：

1. 解析基线由 Reeds-Shepp 一致性代价提供，负责几何可达性与非完整约束主结构。
2. 神经网络只学习环境相关残差，负责补偿障碍物分布、狭窄通道等解析项未显式建模的信息。

对应实现：

- 解析基线：`env/reeds_shepp.py:compute_reeds_shepp_field`
- 残差预测：`network/inference.py:NeuralHeuristicPredictor.predict_residual_field`
- 融合执行：`planner/evaluate.py:evaluate_benchmark`（残差分支）

### 2.2 选择该设计的原因

- 纯神经直接拟合绝对代价场，目标函数跨度大、场形态复杂，易欠拟合或局部低估。
- 纯解析启发式（Euclidean/Dubins/RS）不利用局部环境纹理，无法提前感知“哪里虽然可达但搜索代价高”。
- 分解后，网络学习任务从“拟合绝对值”降为“拟合修正量”，优化更稳定，且保留了解析方法的可解释与保底能力。

### 2.3 Reeds-Shepp Teacher 与 Planner 代价一致性

一致性通过共享同一组代价参数实现：

- Planner边代价：`planner/hybrid_astar.py:HybridAStarPlanner._edge_cost`
- RS一致性代价：`env/reeds_shepp.py:path_cost_consistent`
- 参数绑定：`env/reeds_shepp.py:RSConsistentCostConfig.from_configs`

两侧共用 `reverse_penalty`、`steer_penalty`、`steer_change_penalty`、`step_size`、`wheel_base`、`max_steer` 等参数，避免“Teacher和Planner优化目标不一致”。代码中还提供了对齐验证：`tests/test_teacher_alignment.py:test_teacher_alignment_cases`。

## 3. 逐层运行逻辑拆解（自顶向下）

### 层次 1：启动入口（`scripts/run_demo.py` 与 `scripts/evaluate.py`）

`scripts/run_demo.py:main` 端到端串联 5 步：

1. 调用 `env/dataset_builder.py:generate_benchmark_split` 生成固定 A/B/C 基准集。
2. 调用 `network/train.py:train_network` 训练 `network/model.py:TinyUNet`。
3. 构造 `network/inference.py:NeuralHeuristicPredictor`，调用 `planner/evaluate.py:evaluate_benchmark` 进行四方法评测。
4. 输出搜索树与场可视化（`utils/visualization.py:*`）。
5. 写出 `demo_summary.json`、`final_submission_table.csv` 等日志。

`scripts/evaluate.py:main` 是纯评测入口：

1. 加载 checkpoint 到 `NeuralHeuristicPredictor`。
2. 调用 `evaluate_benchmark` 统一评估 Euclidean / Dubins / RS-Consistent / Ours。
3. 输出摘要与对比图。

### 层次 2：规划器核心（`planner/hybrid_astar.py`）

`planner/hybrid_astar.py:HybridAStarPlanner.plan`：

1. 若未传 anchor，则默认 `planner/heuristics.py:euclidean_heuristic`。
2. 用 `planner/heuristics.py:compose_guidance` 生成 `(anchor, guided)` 二元启发式接口。
3. 主搜索进入 `HybridAStarPlanner._search`。

`HybridAStarPlanner._search` 核心循环：

1. 用 `open_heap` + `anchor_heap` 维护主优先级与最小 anchor 下界。
2. 每次弹出节点后，先做多重剪枝：过期优先级、界限剪枝、重复扩展剪枝。
3. 展开动作来自 `self.motion_primitives`（前进/倒车 x 五档转角）。
4. 后继状态由 `HybridAStarPlanner._simulate` 逐步积分并做碰撞检查。
5. 边代价由 `HybridAStarPlanner._edge_cost` 计算。
6. 启发式在 `h_pair(nx, ny, nyaw)` 处调用，实际值来源于层次 3 构建的 heuristic 对象。
7. 终止条件：`HybridAStarPlanner._is_goal` 满足后，再用 `HybridAStarPlanner._peek_min_anchor` 检查最优性界。

关于“RS缓存 + 残差预测”的结合位置：

- 组合逻辑不在 `hybrid_astar.py` 内，而是在 `planner/evaluate.py:evaluate_benchmark` 构造 `anchor_fn` 后注入 `planner.plan(...)`。

### 层次 3：启发式计算（`planner/heuristics.py` + `network/inference.py`）

`planner/evaluate.py:evaluate_benchmark` 在 Ours 分支执行：

1. 用 `env/reeds_shepp.py:make_rs_field_cache_key` 生成键。
2. 先 `load_rs_field_cache`，未命中则 `compute_reeds_shepp_field(..., cost_mode="planner_consistent")` 再 `save_rs_field_cache`。
3. 调用 `NeuralHeuristicPredictor.predict_residual_field` 得到残差场。
4. 残差后处理：`pred_residual = max(pred_residual, 0) * residual_alpha`。
5. 封装 `planner/heuristics.py:ResidualYawFieldHeuristic(base_field_3d=rs_cons_field, residual_field_3d=pred_residual)`。

`planner/heuristics.py` 的实际查询机制：

- `YawFieldHeuristic.__call__` 与 `ResidualYawFieldHeuristic.__call__` 最终调用 `utils/common.py:trilinear_interpolate_yaw` 对 `(x,y,yaw)` 连续状态做三线性（含 yaw 环形）插值。

`network/inference.py:NeuralHeuristicPredictor` 推理细节：

1. `_build_input` 构造 5 通道输入：`occupancy, normalized_esdf, goal_gaussian, sin(goal_yaw), cos(goal_yaw)`。
2. `TinyUNet` 输出与地图同分辨率的多 yaw-bin 残差。
3. 结果按地图对角线尺度反归一化到米制代价。

### 层次 4：底层支撑（`env/` 环境、碰撞与 RS 代价）

环境建模：

- `env/map_generator.py:generate_scene` / `generate_scene_from_category` 生成 random/narrow/parking/deadend 场景。
- `env/esdf.py:compute_esdf` 生成米制有符号距离场。

数据与教师：

- `env/teacher.py:compute_nonholonomic_teacher` 生成 `teacher_2d + teacher_3d`。
- `env/dataset_builder.py:generate_dataset_split` / `generate_benchmark_split` 落盘 `occupancy/esdf/teacher_3d/rs_base_3d/...`。

碰撞检测与状态有效性：

- `planner/hybrid_astar.py:HybridAStarPlanner._state_is_valid` 使用 ESDF（`utils/common.py:bilinear_interpolate`）判断 `d > vehicle_clearance`。

RS 代价计算：

- `env/reeds_shepp.py:path_cost_consistent` 对 RS 分段路径进行步进积分，复现 planner 的倒车与转向代价。
- `env/reeds_shepp.py:shortest_path_cost_consistent_with_path` 在候选 RS 路径中取最小一致性代价。

## 4. 关键创新点的数学表达

### 4.1 代价一致性教师信号（RS-Consistent Teacher）

设 RS 路径由分段 \(j=1,\dots,J\) 组成，第 \(j\) 段长度为 \(L_j\)，离散为 \(n_j\) 步，\(\Delta s_j=L_j/n_j\)。则：

\[
h_{rs}(s)=\sum_{j=1}^{J}\sum_{i=1}^{n_j} c_{j,i}
\]

\[
c_{j,i}=
\rho_{\text{dir}}(d_j)\,\Delta s_j
\;+\;\lambda_{\text{steer}}\frac{|\delta_j|}{\delta_{\max}}\Delta s_j
\;+\;\mathbf{1}_{i=1}\lambda_{\Delta\text{steer}}\frac{|\delta_j-\delta_{j-1}|}{\delta_{\max}}\Delta s_j
\]

\[
\rho_{\text{dir}}(d_j)=
\begin{cases}
1,& d_j=+1\ (\text{前进})\\
\lambda_{\text{rev}},& d_j=-1\ (\text{倒车})
\end{cases}
\]

其中：

- \(\lambda_{\text{rev}}\): 倒车惩罚（`reverse_penalty`）
- \(\lambda_{\text{steer}}\): 转向幅值惩罚（`steer_penalty`）
- \(\lambda_{\Delta\text{steer}}\): 转向变化惩罚（`steer_change_penalty`）
- \(\delta_{\max}\): 最大转角

该表达对应实现 `env/reeds_shepp.py:path_cost_consistent`，并与 `planner/hybrid_astar.py:HybridAStarPlanner._edge_cost` 同构。

### 4.2 残差学习架构

\[
h(s)=h_{rs}(s)+\alpha\cdot\max(\Delta h_{\theta}(s),0)
\]

变量含义：

- \(h_{rs}(s)\)：解析 RS 一致性基线启发式
- \(\Delta h_{\theta}(s)\)：网络预测残差
- \(\alpha\)：残差增益（`residual_alpha`）
- \(\max(\cdot,0)\)：非负约束，避免残差削弱解析下界

对应实现：`planner/evaluate.py:evaluate_benchmark`（残差分支）+ `planner/heuristics.py:ResidualYawFieldHeuristic`。

### 4.3 加权 MSE Loss 与“防低估”设计

训练损失（`network/train.py:_masked_loss`）：

\[
\mathcal{L}
=
\frac{\sum_{b,c,u,v} w_{b,c,u,v}\,\beta_{b,c,u,v}\,(\hat y_{b,c,u,v}-y_{b,c,u,v})^2}
{\sum_{b,c,u,v} w_{b,c,u,v}+\varepsilon}
\]

\[
\beta_{b,c,u,v}=
\begin{cases}
\lambda_{\text{under}}, & \hat y_{b,c,u,v}<y_{b,c,u,v}\\
1, & \text{otherwise}
\end{cases}
\]

\[
w_{b,c,u,v}=m_{b,c,u,v}\cdot w^{dist}_{b,c,u,v}\cdot w^{type}_{b}
\]

\[
w^{dist}=\mathrm{clip}\left(\frac{1}{1+d_{2d}/s},\; w_{\min},\;1\right)
\]

其中 \(m\) 是有效像素掩码，\(w^{type}\) 对 C 类样本加权，\(\lambda_{\text{under}}>1\) 对低估误差额外放大，从训练目标上抑制启发式低估风险。

## 5. 实现对比：Ours vs Baselines

| 方法 | 启发式来源 | 关键实现路径 | 环境感知 | 代价一致性 | GPU推理 | 复用模块 | 独有模块 |
|---|---|---|---|---|---|---|---|
| Euclidean | 几何直线距离 | `planner/heuristics.py:euclidean_heuristic` | 否 | 否 | 否 | `planner/hybrid_astar.py:HybridAStarPlanner` | 无 |
| Dubins | 固定转弯半径解析场 | `env/dubins.py:compute_dubins_field` + `planner/heuristics.py:YawFieldHeuristic` | 否 | 否 | 否 | 同一 Hybrid A* 主体 | Dubins 场生成 |
| RS-Consistent Analytical | RS 一致性解析场 | `env/reeds_shepp.py:compute_reeds_shepp_field(cost_mode="planner_consistent")` | 否 | 是 | 否 | 同一 Hybrid A* 主体 | RS 一致性代价积分 |
| Ours | RS 基线 + CNN 残差 | `network/inference.py:NeuralHeuristicPredictor.predict_residual_field` + `planner/heuristics.py:ResidualYawFieldHeuristic` | 是 | 是 | 是 | 完全复用 RS 基线和 Hybrid A* 主体 | 残差分支、模型加载、GPU推理 |

代码复用关系（关键点）：

- 四种方法共享同一搜索器 `planner/hybrid_astar.py:HybridAStarPlanner`，保证比较公平。
- Ours 复用 RS-Consistent 的解析基线，只新增“残差预测与融合”链路。
- RS 缓存模块 `env/reeds_shepp.py:load_rs_field_cache/save_rs_field_cache` 被 RS-Consistent 与 Ours 共同复用。

## 6. 创新性评估与结论

### 6.1 与相关思路的本质差异

对比代表性方向：

1. Neural A*（可微搜索）通常学习 guidance/代价以驱动端到端搜索。
2. MPNet / Motion Planning Networks 倾向直接学习规划策略或连通提议。
3. SaIL 等学习启发式方法侧重学习扩展策略，但不强调非完整约束下的解析代价一致性。
4. VIN 类方法强调可微规划模块，但多数是离散网格决策框架。

本实现的核心差异：

- 不是“直接预测绝对启发式”，而是“在 RS 一致性基线之上预测残差”。
- 显式把倒车惩罚、转向惩罚、转向变化惩罚在 Teacher 与 Planner 中参数绑定，避免训练目标与搜索目标错位。
- 工程上保留解析保底能力（即使网络失配，RS 基线仍可工作），并引入 RS 缓存保证在线时延可控。

### 6.2 结论判断（ICRA/IROS/TRO 视角）

结论：该实现在架构设计、代价一致性和工程落地上达到较高水平，具备 ICRA/IROS 竞争力；若面向 TRO，建议补充更强的理论界限、跨平台实机验证与更大规模泛化实验。

判断依据：

1. 方法层面有清晰且可复现的创新组合：`RS一致性先验 + 非负残差修正`。
2. 代价一致性不是口头假设，而是落实到统一参数与单元测试对齐。
3. 工程完整性较强：数据构建、训练、评估、缓存、可视化链路齐全。

### 6.3 参考对比文献（用于本节评估）

- Neural A*: https://proceedings.mlr.press/v139/yonetani21a.html
- MPNet: https://arxiv.org/abs/1907.06013
- SaIL (Learning Heuristic Search via Imitation): https://proceedings.mlr.press/v78/bhardwaj17a.html
- Value Iteration Networks: https://arxiv.org/abs/1602.02867
