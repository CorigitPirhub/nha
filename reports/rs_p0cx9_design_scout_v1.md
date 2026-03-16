# P0-CX9 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-09`

## 1. 问题重构

### 1.1 从 `CX8` 得到的核心事实

`CX8-D / RS-BCA` 的重型版已经证明：
- **瓶颈区域识别 + 特定多步 maneuver 语义** 是有效的；
- 真正有价值的不是“逐 successor 的微操”，而是“在关键区域做正确的多步战略决策”；
- 但一旦把这套语义放在 `Hybrid A*` 的 successor loop 内逐节点逐 primitive 执行，计算开销会随着 `N_expand × |A|` 爆炸。

因此，`CX8` 的失败不是“语义无效”，而是：

> 有效语义被放在了错误的计算层级上。

### 1.2 `CX9` 的问题定义

`CX9` 不再问“如何继续在 successor 层做更快的 bundle arbitration”，而是问：

> 如何把 **瓶颈识别 + bundle 策略** 这种有效语义，提升到 **region-level / state-cluster-level / episode-level**，使其以近似查表或一次性推理的成本执行？

换句话说，`CX9` 要解决的不是纯搜索加速，而是：

> **如何让搜索在关键区域做出正确决策，且不承担高昂的实时推理成本。**

### 1.3 复杂度视角

设：
- `N` 为搜索扩展节点数；
- `A` 为每个节点的 primitive 数；
- `C_phi` 为一次复杂语义模块推理代价；
- `C_lookup` 为一次轻量查表或常数级判定代价。

则：
- `CX8` 重型 successor arbitration 的 online 代价近似为 `O(N · A · C_phi)`；
- `CX9` 希望达到的形式是：
  - 一次性 scene-level / region-level 推理 `O(C_scene)`，外加
  - online lookup `O(N · C_lookup)`，其中 `C_lookup << A · C_phi`。

理想状态下，`CX9` 应把“语义计算”从每个 successor 的内层循环中拿出去，只保留：
- **一次性生成的战略策略**；或
- **稀疏区域上的条件规则**；或
- **少量关键窗口上的离线重分析**。

## 2. 相关文献脉络与批判性分析

### 2.1 学习搜索引导：从 heuristic 到 policy-guided search

1. `Learning Heuristic Search via Imitation` (CoRL 2018)
   - Link: <https://proceedings.mlr.press/v87/chitnis18a.html>
2. `Neural A* Search by Differentiable Priority Queue` (ICML 2021)
   - Link: <https://proceedings.mlr.press/v139/yonetani21a.html>
3. `Policy-Guided Heuristic Search with Guarantees` (2021)
   - Link: <https://arxiv.org/abs/2103.11505>
4. `Hybrid Search for Efficient Planning with Completeness Guarantees` (2023)
   - Link: <https://arxiv.org/abs/2310.12819>

**批判性结论**：
- 这些工作说明“学习 + 搜索骨架保留”是有效方向；
- 但它们大多仍把学习模块放在 **priority / heuristic / subgoal proposal** 这一层；
- 对当前项目来说，真正未被充分开发的空档，不是“再学一个更强 heuristic”，而是 **如何把多步 maneuver 语义压缩成低成本的高层策略对象**。

### 2.2 子目标与层级策略：把局部微操上提为战略决策

1. `Learning over Subgoals for Efficient Navigation of Structured, Unknown Environments` (CoRL 2018)
   - Link: <https://proceedings.mlr.press/v87/huang18a.html>
2. `Hierarchical Imitation Learning with Vector Quantized Models` (ICML 2023)
   - Link: <https://proceedings.mlr.press/v202/simsek23a.html>
3. `Hybrid Search for Efficient Planning with Completeness Guarantees` (2023)
   - Link: <https://arxiv.org/abs/2310.12819>

**批判性结论**：
- 子目标/层级方法的价值在于：把长程决策变成少量 strategic choices；
- 但现有工作通常把“子目标”视为几何 waypoint，而不是 **带 maneuver 语义的瓶颈策略**；
- `CX9` 的机会就在于：把 `CX8-D` 成功的“reverse-setup / forward-thread”语义，升级成 **subgoal-conditioned maneuver program**，而不是只给一个坐标点。

### 2.3 抽象与上下文特异决策：region-level / cluster-level 才是低成本语义承载层

1. `Context-Aware Motion Prediction and Planning` (CoRL 2021)
   - Link: <https://proceedings.mlr.press/v164/perez-dattari22a.html>
2. `Hierarchical Imitation Learning with Vector Quantized Models` (ICML 2023)
   - Link: <https://proceedings.mlr.press/v202/simsek23a.html>
3. `Self-Supervised Learning of Scene-Graph Representations for Robotic Sequential Manipulation Planning` (CoRL 2021)
   - Link: <https://proceedings.mlr.press/v164/driess22a.html>

**批判性结论**：
- 这些工作共同指出：复杂决策往往应该在 **抽象状态 / 场景图 / 语义单元** 层做；
- 当前项目如果继续把 bundle 语义放在 successor 级，就会重复 `CX8` 的代价灾难；
- 因而 `CX9` 必须找到一个新的承载对象：
  - region label；
  - state-cluster mode；
  - strategic scene graph node；
  - 或 bottleneck window。

### 2.4 Motion Primitive 与 Maneuver Library：真正有用的是“结构化策略对象”，不是每个动作都单独判断

1. `Probably Approximately Correct Vision-Based Planning using Motion Primitives` (CoRL 2021)
   - Link: <https://arxiv.org/abs/2002.12852>
2. `Policy Optimization to Learn Adaptive Motion Primitives in Path Planning with Dynamic Obstacles` (2022)
   - Link: <https://arxiv.org/abs/2212.14307>
3. `Incremental Generalized Hybrid A*` (2025)
   - Link: <https://arxiv.org/abs/2508.13392>

**批判性结论**：
- 非完整约束规划中的真正自由度并不高，很多高难 case 的关键在于：
  - 何时进入某类 maneuver family；
  - 何时需要 reverse-setup；
  - 何时保持 thread-through；
- 这意味着 `CX9` 不应继续把“干预单位”定义为单个 primitive，而应上提到：
  - maneuver family；
  - bundle tag；
  - 或条件策略模板。

### 2.5 一次性先验 / 两阶段干预：重推理应放在搜索循环外

1. `Neural MP: A Generalist Neural Motion Planner` (2024)
   - Link: <https://arxiv.org/abs/2409.05864>
2. `DiffusionSeeder: Seeding Motion Optimization with Diffusion for Rapid Motion Planning` (2024)
   - Link: <https://arxiv.org/abs/2410.16727>

**批判性结论**：
- 最近高性能 motion planning 趋势越来越明确：
  - 学习模块负责 **一次性 proposal / seed / prior**；
  - 主规划器负责在线约束满足；
- 这与 `CX9` 的方向高度一致：
  - 把 bundle 语义挪到搜索前或搜索外；
  - 在线阶段只做查表或 sparse trigger。

## 3. 从 `CX8` 到 `CX9` 的设计原则

`CX9` 的统一原则：

1. **语义保留**：必须继承 `CX8-D` 已被验证有效的核心语义：
   - 瓶颈识别；
   - 特定 bundle / maneuver family；
   - reverse-setup 这类多步战略动作。
2. **层级上提**：不再把策略对象放在 successor 级，而要上提到：
   - region；
   - state cluster；
   - bottleneck window；
   - 或 scene-level program。
3. **低成本执行**：重推理最多允许：
   - 每张地图一次；
   - 每条轨迹一次；
   - 或每个稀疏窗口一次；
   不允许重新回到 `O(N · A · C_phi)`。
4. **anchor 保留**：任何 `CX9` 候选都必须保留 accepted `CX3-D` 的 fallback 语义，不允许破坏其诚实 claim boundary。
5. **实现可行**：必须能在现有 `rs_cx` + `planner` 框架下实现，不依赖新的大型训练生态或完全不同的求解器。

## 4. 冻结候选路线

### CX9-A：RS-SBM — Strategic Bundle Map

- **类型**：`region-level strategic map / offline once-per-scene module`
- **核心想法**：
  1. 离线或一次性地把场景分解为少量“战略区域”；
  2. 每个区域绑定一个 bundle tag，例如 `neutral / forward-thread-left / forward-thread-right / reverse-setup-left / reverse-setup-right`；
  3. 在线搜索时，节点只需查询自己所在区域的 tag，再对对应 primitive family 加一个固定 bias。
- **如何继承 `CX8-D` 的成功语义**：
  - `CX8-D` 证明瓶颈处需要特定 maneuver family；
  - `CX9-A` 只是把这个“在哪儿触发哪种 bundle”的知识，从 successor-level classifier 提升成 **region-level semantic atlas**。
- **理论抓手**：
  - 计算复杂度：一次性建图 `O(C_scene)`，在线 query `O(1)`；
  - 信息瓶颈：把大量局部动作决策压缩为少量 region labels，若 bottleneck 主要由少数关键区域决定，则损失最小化可集中在这些 labels 上。
- **预期优势轴**：
  - 保留 `CX8-D` 在 `flange / maze / narrow bottleneck` 上的正向趋势；
  - 在线开销显著低于 successor-level arbitration。
- **最相关工作与差异**：
  - 相关：`Learning over Subgoals...`、`Hierarchical Imitation Learning with Vector Quantized Models`；
  - 差异：这些工作学习的是 generic subgoal 或 abstract latent code，而 `RS-SBM` 学的是 **带 nonholonomic maneuver 语义的区域图谱**，区域标签直接对应 `CX8-D` 的 bundle 策略，而非通用 waypoint。

### CX9-B：RS-CSP — Conditional Subgoal Program

- **类型**：`scene-level one-shot strategic program`
- **核心想法**：
  1. 给定地图、起点、终点，一次性预测一小段“条件子目标程序”；
  2. 程序中的每个条目不是单纯坐标，而是 `(gate_i, maneuver_tag_i)`；
  3. 在线搜索只需按照程序顺序完成若干段 baseline search。
- **如何继承 `CX8-D` 的成功语义**：
  - `CX8-D` 的本质是“在某个 bottleneck 之前先做 reverse-setup，再 thread through”；
  - `CX9-B` 将该语义从 per-node arbitration 提升为 **once-per-scene 的战略脚本**。
- **理论抓手**：
  - 深度分解：将一段长 horizon search 分解为 `K` 个子问题，在线复杂度从“每个节点都决策”变成“每个阶段只执行固定策略”；
  - 若 bottleneck 数量 `K` 很小，则额外推理成本与 `K` 成正比，而非与 `N_expand` 成正比。
- **预期优势轴**：
  - 解决“需要多步 setup”的 case；
  - 有望把 `narrow_passage` 这类长期依赖显式写进策略，而不是隐式藏在 field 或 priority 里。
- **最相关工作与差异**：
  - 相关：`Learning over Subgoals...`、`Hybrid Search for Efficient Planning with Completeness Guarantees`；
  - 差异：这些方法把 subgoal 当作纯几何目标，而 `RS-CSP` 把 subgoal 升级为 **带 maneuver semantics 的条件程序**，是“策略脚本”而不是“点序列”。

### CX9-C：RS-CPF — Conditional Policy Field

- **类型**：`conditional field structure / coarse state-cluster policy lookup`
- **核心想法**：
  1. 不再输出标量 heuristic correction，而是输出一个离散的 **条件策略场**；
  2. 该场在粗粒度 `(x, y, yaw-cluster)` 上给出当前应采用的 mode，例如 `neutral / thread-left / thread-right / reverse-setup-left / reverse-setup-right`；
  3. 在线节点只需查 coarse cell 的 mode，再用固定模板重排 primitive。
- **如何继承 `CX8-D` 的成功语义**：
  - `CX8-D` 的 bundle semantics 仍然保留，但被存成 **模式场** 而不是 successor classifier；
  - 因而语义仍在，只是变成了 field-like representation。
- **理论抓手**：
  - 这是一个“条件策略”而非“标量值函数”，本质上是 piecewise-constant option policy；
  - 复杂度近似 `O(|G_coarse|)` 的一次性生成 + `O(1)` 在线查询；
  - 若策略模式在区域内保持稳定，则 coarse quantization 的表达损失是可控的。
- **预期优势轴**：
  - 在保留 field-style 低成本执行的同时，恢复 `CX8-D` 丢失的多步策略语义；
  - 与现有 `RS` 主线最自然兼容。
- **最相关工作与差异**：
  - 相关：`Neural A* Search by Differentiable Priority Queue`、`Policy-Guided Heuristic Search with Guarantees`；
  - 差异：现有工作学习的是 scalar heuristic 或 search policy，而 `RS-CPF` 学的是 **可查表的离散 maneuver mode field**，它不是 priority predictor，也不是 cost field，而是条件策略结构。

### CX9-D：RS-BWR — Bottleneck Window Review

- **类型**：`trajectory-level sparse offline review / local replanning trigger`
- **核心想法**：
  1. 先运行 accepted `CX3-D` baseline 一次，得到粗轨迹或 expanded frontier；
  2. 只在少数被识别为 bottleneck 的轨迹窗口上运行 bundle-level semantic review；
  3. 如果窗口被判定需要特殊 maneuver，再触发局部 replan 或局部 mode patch。
- **如何继承 `CX8-D` 的成功语义**：
  - `CX8-D` 的 bundle reasoning 仍保留，但只在 `M` 个 bottleneck windows 上执行，而不是在全部节点上执行；
  - 也就是说，它保留的是“何时需要 reverse-setup / forward-thread”的判断，不保留 per-successor 微操。
- **理论抓手**：
  - 稀疏干预复杂度：总额外代价 `O(M · C_phi)`，其中 `M << N_expand`；
  - 若失败主要由少数瓶颈窗口主导，则 sparse review 比 successor-level intervention 更符合计算预算。
- **预期优势轴**：
  - 适合当前项目已有的 accepted baseline 框架；
  - 最有希望在不改 planner 内核太多的情况下快速验证“语义上提”的可行性。
- **最相关工作与差异**：
  - 相关：`DiffusionSeeder`、`Neural MP`；
  - 差异：这些工作是在搜索/优化前给 seed 或 plan prior，而 `RS-BWR` 是 **先跑 accepted baseline，再只对少量瓶颈窗口做语义复审**，干预对象更稀疏、更可控。

## 5. 推荐执行顺序

推荐顺序：`CX9-A -> CX9-D -> CX9-B -> CX9-C`

### 为什么先 `CX9-A`
- 它最贴近 `CX8-D` 的成功语义，又把在线成本降到了查表级；
- 若 `region-level semantic atlas` 都无法保留 `CX8-D` 的正向增益，则说明“语义上提”本身就有问题。

### 为什么第二做 `CX9-D`
- 它不要求一次性生成全局程序或全图 mode field；
- 只要当前 baseline 轨迹上确实存在少数关键瓶颈窗口，就可能保留语义收益且显著降低开销。

### 为什么第三做 `CX9-B`
- 它最有希望恢复 `narrow_passage` 的长期依赖收益；
- 但程序生成器的失败风险更高，因此放在 `A/D` 之后。

### 为什么最后做 `CX9-C`
- 它最优雅，也最有潜力成为 paper-facing 主方法；
- 但它需要把 bundle semantics 抽象成条件策略场，设计与验证成本最高，因此最后做。

## 6. 最低验收标准与失败判据

### 最低验收标准

任何 `CX9-*` 候选若要进入下一阶段严格统计验证，至少需要在 `calib_hard_v1` 的 dev-only pilot 上同时满足：

1. `exp_delta > 0`；
2. `success_delta_pp >= 0`；
3. `mean_time_overhead_ratio < 0.30`；
4. 不出现明显 path audit 恶化；
5. 不依赖 per-successor 深度模型推理。

### 失败判据

若某候选出现以下任一情况，则应立即冻结，不再扩大实验面：

1. 在线阶段仍需每个节点或每个 successor 执行深模型推理；
2. 在 dev-only pilot 上 `exp_delta <= 0`；
3. `mean_time_overhead_ratio >= 0.30` 且无法通过一次性 scene-level 预计算解释；
4. 增益只来自单一 family patch，而跨 family 趋势仍为负；
5. 其成功依赖于与 `test` 不一致的协议或特例化规则。

## 7. 最终冻结结论

`P0-CX9` 的核心不是继续做“更强 successor-level arbitration”，而是：

> 将 `CX8-D` 已被证明有效的瓶颈 bundle 语义，上提为 **region-level / window-level / episode-level** 的低成本战略策略对象。

当前最优先候选：
1. `CX9-A / RS-SBM`
2. `CX9-D / RS-BWR`
3. `CX9-B / RS-CSP`
4. `CX9-C / RS-CPF`

这是因为：
- `A/D` 更接近当前框架，可快速验证“语义上提”是否成立；
- `B/C` 则更具方法创新性与 paper potential，但实现成本更高。

## 8. 参考文献（primary sources）

1. Chitnis et al., `Learning Heuristic Search via Imitation`, CoRL 2018. <https://proceedings.mlr.press/v87/chitnis18a.html>
2. Yonetani et al., `Neural A* Search by Differentiable Priority Queue`, ICML 2021. <https://proceedings.mlr.press/v139/yonetani21a.html>
3. Orseau et al., `Policy-Guided Heuristic Search with Guarantees`, 2021. <https://arxiv.org/abs/2103.11505>
4. Shah et al., `Hybrid Search for Efficient Planning with Completeness Guarantees`, 2023. <https://arxiv.org/abs/2310.12819>
5. Huang et al., `Learning over Subgoals for Efficient Navigation of Structured, Unknown Environments`, CoRL 2018. <https://proceedings.mlr.press/v87/huang18a.html>
6. Simsek et al., `Hierarchical Imitation Learning with Vector Quantized Models`, ICML 2023. <https://proceedings.mlr.press/v202/simsek23a.html>
7. Driess et al., `Self-Supervised Learning of Scene-Graph Representations for Robotic Sequential Manipulation Planning`, CoRL 2021. <https://proceedings.mlr.press/v164/driess22a.html>
8. Wang et al., `Probably Approximately Correct Vision-Based Planning using Motion Primitives`, 2021. <https://arxiv.org/abs/2002.12852>
9. Du et al., `Policy Optimization to Learn Adaptive Motion Primitives in Path Planning with Dynamic Obstacles`, 2022. <https://arxiv.org/abs/2212.14307>
10. Chi et al., `Neural MP: A Generalist Neural Motion Planner`, 2024. <https://arxiv.org/abs/2409.05864>
11. Du et al., `DiffusionSeeder: Seeding Motion Optimization with Diffusion for Rapid Motion Planning`, 2024. <https://arxiv.org/abs/2410.16727>
12. Hernandez et al., `Incremental Generalized Hybrid A*`, 2025. <https://arxiv.org/abs/2508.13392>
