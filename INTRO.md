# 基于代价一致性与残差学习的神经启发式 Hybrid A* 规划器

修改日期：2026-02-23

## 1. 整体架构图

```mermaid
flowchart LR
    A[环境输入<br/>occupancy/start/goal/车辆参数]

    subgraph OFF[离线训练阶段]
        B[场景生成<br/>env/map_generator.py:generate_scene<br/>env/map_generator.py:generate_scene_from_category]
        C[ESDF构建<br/>env/esdf.py:compute_esdf]
        D[教师信号生成<br/>env/teacher.py:compute_nonholonomic_teacher]
        E[数据集构建与落盘<br/>env/dataset_builder.py:generate_dataset_split]
        F[数据加载<br/>network/dataset.py:HeuristicFieldDataset]
        G[神经网络训练<br/>network/train.py:train_network]
        H[模型权重<br/>outputs/checkpoints/*.pt]
    end

    subgraph ON[在线规划阶段]
        I[规划任务输入<br/>scripts/evaluate.py:main<br/>scripts/run_demo.py:main]
        J[RS缓存查询<br/>env/reeds_shepp.py:load_rs_field_cache]
        K[缓存未命中时计算RS场<br/>env/reeds_shepp.py:compute_reeds_shepp_field]
        L[残差推理<br/>network/inference.py:NeuralHeuristicPredictor.predict_residual_field]
        M[启发式融合<br/>h = h_rs + alpha * max(Delta h, 0)<br/>planner/heuristics.py:ResidualYawFieldHeuristic]
        N[Hybrid A*搜索<br/>planner/hybrid_astar.py:HybridAStarPlanner.plan]
        O[最终轨迹输出<br/>path(x, y, yaw)]
    end

    A --> B --> C --> D --> E --> F --> G --> H
    A --> I
    H --> L
    I --> J
    J -->|hit| M
    J -->|miss| K --> M
    I --> L --> M --> N --> O
    I --> N
```

## 2. 详细设计说明

本系统采用“解析引导 + 神经修正”的残差学习架构。核心思想不是让网络直接回归完整启发式，而是先用解析方法给出强先验，再让网络只学习环境相关修正量。

- 解析引导：由 `env/reeds_shepp.py:compute_reeds_shepp_field` 生成 RS 一致性基线场，保证非完整约束几何可达性与代价主结构。
- 神经修正：由 `network/inference.py:NeuralHeuristicPredictor.predict_residual_field` 预测残差，仅补偿障碍物分布、狭窄通道、动态风险等解析项缺失信息。
- 安全融合：在评测与规划调用链 `planner/evaluate.py:evaluate_benchmark` 中执行 `max(Delta h, 0)` 和 `residual_alpha` 缩放，再通过 `planner/heuristics.py:ResidualYawFieldHeuristic` 注入搜索器。

选择该设计的原因如下。

- 纯神经直接拟合绝对代价场时，目标尺度大、场结构复杂，容易出现欠拟合或低估误差。
- 纯解析启发式（Euclidean/Dubins/RS）对环境障碍感知不足，尤其在窄道、死胡同、动态风险区域不够敏感。
- 残差分解将学习问题从“全量代价回归”降为“局部修正回归”，训练更稳，且保留了解析基线的可解释性与保底性能。

Reeds-Shepp Teacher 与 Planner 的代价一致性由同一参数族保证。

- 规划边代价：`planner/hybrid_astar.py:HybridAStarPlanner._edge_cost`。
- 教师代价积分：`env/reeds_shepp.py:path_cost_consistent`。
- 参数对齐入口：`env/reeds_shepp.py:RSConsistentCostConfig.from_configs`。

统一参数包含 `reverse_penalty`、`steer_penalty`、`steer_change_penalty`、`step_size`、`wheel_base`、`max_steer`，避免“教师优化目标”与“在线搜索目标”不一致。

## 3. 逐层运行逻辑拆解

### 层次 1：启动入口

`scripts/run_demo.py:main` 的主流程：

1. 构造固定基准数据：`env/dataset_builder.py:generate_benchmark_split`（train/val/test）。
2. 训练网络：`network/train.py:train_network`，输出 checkpoint 与训练日志。
3. 统一评测：`planner/evaluate.py:evaluate_benchmark`，执行 Euclidean/Dubins/RS-Consistent/Ours 对比。
4. 可视化与动画：`utils/visualization.py:save_search_tree_comparison`、`utils/visualization.py:save_search_progress_animation`。
5. 输出结果：`outputs/logs/demo_summary.json` 与提交表。

`scripts/evaluate.py:main` 的主流程：

1. 加载模型：`network/inference.py:NeuralHeuristicPredictor`。
2. 调用 `planner/evaluate.py:evaluate_benchmark` 执行标准评测。
3. 写出摘要、散点图、搜索树/场对比图和可选动画。

### 层次 2：规划器核心（Hybrid A* 搜索循环）

`planner/hybrid_astar.py:HybridAStarPlanner.plan`：

1. 若未提供锚点启发式，默认使用 `planner/heuristics.py:euclidean_heuristic`。
2. 通过 `planner/heuristics.py:compose_guidance` 统一成 `(anchor, guided)` 查询接口。
3. 可选 warm-start（guided 模式）后，进入主搜索 `HybridAStarPlanner._search`。

`planner/hybrid_astar.py:HybridAStarPlanner._search` 关键步骤：

1. 用 `open_heap` 与 `anchor_heap` 维护优先队列，优先级由 `HybridAStarPlanner._priority` 给出。
2. 节点弹出后执行过期条目过滤、界限剪枝、重复扩展剪枝。
3. 终止判断由 `HybridAStarPlanner._is_goal`；最优性收敛由 `HybridAStarPlanner._peek_min_anchor`。
4. 后继展开使用 `self.motion_primitives`，状态传播由 `HybridAStarPlanner._simulate`，碰撞/越界由 `HybridAStarPlanner._state_is_valid`。
5. 边代价由 `HybridAStarPlanner._edge_cost` 计算，离散键由 `HybridAStarPlanner._state_key` 编码。
6. 搜索完成后，路径由 `HybridAStarPlanner._reconstruct_path` 回溯输出。

“RS 缓存 + 网络残差”的启发式组合位置在评测封装层，而不是 `HybridAStarPlanner._search` 内部：

- 缓存键与查询：`env/reeds_shepp.py:make_rs_field_cache_key`、`env/reeds_shepp.py:load_rs_field_cache`。
- 未命中计算：`env/reeds_shepp.py:compute_reeds_shepp_field`（`cost_mode="planner_consistent"`）。
- 残差推理：`network/inference.py:NeuralHeuristicPredictor.predict_residual_field`。
- 融合封装：`planner/heuristics.py:ResidualYawFieldHeuristic`。
- 注入搜索：`planner/evaluate.py:_run_method` -> `planner/hybrid_astar.py:HybridAStarPlanner.plan`。

### 层次 3：启发式计算（Heuristics + Inference）

`planner/heuristics.py`：

- `euclidean_heuristic`、`dubins_heuristic` 提供解析启发式。
- `YawFieldHeuristic.__call__` 对 3D 场做 yaw-aware 插值。
- `ResidualYawFieldHeuristic.__call__` 执行 `base + residual` 查询。
- 两者都依赖 `utils/common.py:trilinear_interpolate_yaw`，支持连续状态 `(x,y,yaw)` 的插值。

`network/inference.py`：

- `NeuralHeuristicPredictor.__init__` 读取 checkpoint，调用 `network/model.py:build_model` 构建网络。
- `NeuralHeuristicPredictor._build_input` 组装输入通道：`occupancy`、归一化 ESDF、目标高斯、目标 yaw 正余弦，并可拼接动态风险与车辆上下文。
- `NeuralHeuristicPredictor.predict_residual_field` 完成前向推理、尺度还原、时序切片提取与残差后处理。
- `NeuralHeuristicPredictor.predict_field` 在绝对预测模式下输出完整启发式；残差模式下可由 `NeuralHeuristicPredictor.compute_rs_analytical_base_field` 补基线。

### 层次 4：底层支撑（环境建模、碰撞检测、RS代价）

环境建模：

- 地图与任务采样：`env/map_generator.py:generate_scene`、`env/map_generator.py:generate_scene_from_category`。
- 距离场构建：`env/esdf.py:compute_esdf`。

教师信号与时序扩展：

- 主入口：`env/teacher.py:compute_nonholonomic_teacher`。
- 2D 基础场：`env/teacher.py:compute_2d_dijkstra_field`。
- 3D 非完整教师：`env/teacher.py:_compute_teacher_3d_core`。
- 动态时序残差：`env/teacher.py:_dynamic_occupancy_at_step` + `return_temporal_residual` 分支。

碰撞检测与 RS 一致性代价：

- 状态可行性：`planner/hybrid_astar.py:HybridAStarPlanner._state_is_valid`（ESDF 插值 + 车辆净空阈值）。
- RS 一致性积分：`env/reeds_shepp.py:path_cost_consistent`。
- 一致性最短代价：`env/reeds_shepp.py:shortest_path_cost_consistent_with_path`。
- RS 场缓存：`env/reeds_shepp.py:save_rs_field_cache` / `env/reeds_shepp.py:load_rs_field_cache`。

## 4. 关键创新点的数学表达

### 4.1 代价一致性教师信号（RS Consistent Teacher）

对任意状态 \(s\) 到目标 \(g\)，定义 RS 候选路径集合 \(\mathcal{P}_{rs}(s,g)\)。路径 \(\pi\) 由分段 \(j\) 构成，每段离散步长为 \(\Delta s_{j,i}\)，方向 \(d_j \in \{+1,-1\}\)，转角 \(\delta_j\)。

\[
h_{rs}(s)=\min_{\pi \in \mathcal{P}_{rs}(s,g)} \sum_{j}\sum_{i} c_{j,i}
\]

\[
c_{j,i}
=
\Delta s_{j,i}
\Big[1+(\lambda_{rev}-1)\mathbf{1}(d_j=-1)+\lambda_{steer}\frac{|\delta_j|}{\delta_{max}}\Big]
+\mathbf{1}(i=1)\lambda_{\Delta steer}\frac{|\delta_j-\delta_{j-1}|}{\delta_{max}}\Delta s_{j,i}
\]

其中：

- \(\lambda_{rev}\)：倒车惩罚，对应 `reverse_penalty`。
- \(\lambda_{steer}\)：转向幅值惩罚，对应 `steer_penalty`。
- \(\lambda_{\Delta steer}\)：转向变化惩罚，对应 `steer_change_penalty`。

该式在实现上对应 `env/reeds_shepp.py:path_cost_consistent`，并与 `planner/hybrid_astar.py:HybridAStarPlanner._edge_cost` 保持同构。

### 4.2 残差学习启发式

\[
h(s)=h_{rs}(s)+\alpha \cdot \max(\Delta h_\theta(s), 0)
\]

变量含义：

- \(h_{rs}(s)\)：RS 一致性解析基线。
- \(\Delta h_\theta(s)\)：网络预测残差。
- \(\alpha\)：残差增益，对应 `residual_alpha`。
- \(\max(\cdot,0)\)：非负约束，避免残差削弱解析先验。

### 4.3 加权 MSE Loss 与防低估机制

设像素/体素索引为 \(u\)，预测为 \(\hat y_u\)，教师为 \(y_u\)，掩码为 \(m_u\)，综合权重为 \(w_u\)。加权 MSE 写为：

\[
\mathcal{L}_{wmse}
=
\frac{\sum_{u} m_u w_u a_u (\hat y_u-y_u)^2}{\sum_{u} m_u w_u+\epsilon}
\]

\[
a_u = 1 + (\lambda_{under}-1)\mathbf{1}(\hat y_u<y_u)
\]

\[
w_u = w_u^{loss}\cdot w_u^{sample}
\]

其中 \(\lambda_{under}>1\) 会放大低估误差；在 `network/train.py:_masked_loss` 中，Hard 样本可用更高 `hard_underestimation_weight`，Standard 样本可退化为对称 MSE（避免过度保守）。该设计的目的是降低启发式低估导致的无效扩展风险。

## 5. 实现对比：Ours vs Baselines

| 方法 | 核心启发式 | 关键代码路径 | 环境感知 | 代价一致性 | GPU推理 | 复用模块 | 独有模块 |
|---|---|---|---|---|---|---|---|
| Euclidean | 直线距离 | `planner/heuristics.py:euclidean_heuristic` | 否 | 否 | 否 | `planner/hybrid_astar.py:HybridAStarPlanner` | 无 |
| Dubins | 固定最小转弯半径解析场 | `env/dubins.py:compute_dubins_field` + `planner/heuristics.py:YawFieldHeuristic` | 否 | 否 | 否 | 同一搜索器、同一评测管线 | Dubins 场生成 |
| RS-Consistent Analytical | 带惩罚项的 RS 解析场 | `env/reeds_shepp.py:compute_reeds_shepp_field(cost_mode="planner_consistent")` | 否 | 是 | 否 | 同一搜索器、同一缓存机制 | `path_cost_consistent` 代价积分 |
| Ours | RS 基线 + CNN 残差修正 | `network/inference.py:NeuralHeuristicPredictor.predict_residual_field` + `planner/heuristics.py:ResidualYawFieldHeuristic` | 是 | 是 | 是 | 完全复用 RS 基线与 Hybrid A* 主干 | 残差网络、残差后处理、GPU推理 |

复用与独有关系可总结为：

- 四种方法共享 `planner/hybrid_astar.py:HybridAStarPlanner`，保证搜索主体公平。
- Ours 复用 RS-Consistent 的解析先验，只新增“残差预测 + 融合”链路。
- RS 缓存 `env/reeds_shepp.py:make_rs_field_cache_key` / `load_rs_field_cache` / `save_rs_field_cache` 在 RS-Consistent 与 Ours 中共同复用。

## 6. 创新性评估与结论

与代表性相关方法相比，本实现的本质差异如下。

- 相比 Neural A* / VIN：这类方法多在离散 2D 栅格上直接学习代价或策略；本实现针对非完整车辆状态 \((x,y,yaw)\)，并保留解析 RS 先验作为搜索锚点。
- 相比 MPNet：MPNet 更偏端到端路径提议，本实现不替代搜索，而是“可解释启发式增强”，在工程上更易与现有 Hybrid A* 系统集成。
- 相比常见 RL 启发式：许多方法优化扩展策略但未显式约束倒车/转向代价一致性；本实现通过 `RSConsistentCostConfig` 在 Teacher 与 Planner 之间实现严格参数同构。

综合判断：

- 在架构设计上，“RS 一致性先验 + 非负残差修正”具有明确方法创新点，且技术路线清晰可解释。
- 在工程落地上，具备完整的数据生成、训练、缓存、推理、评测与可视化闭环，工程成熟度高。
- 以学术标准评估，该工作达到 ICRA/IROS 强竞争水平；冲击 TRO/IJRR 具备基础，但通常仍需要更大规模公开非完整约束基准和更充分的跨方法统计显著性验证来进一步增强说服力。
