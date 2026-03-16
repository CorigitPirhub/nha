# P0-CX12 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-11`

## 1. Scope and Protocol

本轮严格遵守 `design-scout only` 约束：

- **没有**训练新模型；
- **没有**跑新的 full benchmark；
- 只复用了上一轮已锁定的 `CX10-D` / `CX11` 产物与 `calib_hard_v1`、`parasol_narrow` 的已有输出；
- 只做特征提取、失败机理诊断与候选路线冻结。

辅助产物位于：
- `outputs/rs_p0cx12_design_scout_v1/public_feature_rows.csv`
- `outputs/rs_p0cx12_design_scout_v1/worst_public_flange_top5.csv`
- `outputs/rs_p0cx12_design_scout_v1/best_public_narrow_top5.csv`
- `outputs/rs_p0cx12_design_scout_v1/feature_overlap_public_flange_vs_narrow.csv`

## 2. Data Coverage Reality Check

### 2.1 `calib_hard_v1` 本身不足以完成 “top-5 flange worst” 诊断

`calib_hard_v1` 的 split 非常小：

- `calib_train`: `n=10`，其中 **没有 `flange`**；
- `calib_val`: `n=7`，其中只有 **1 个 `flange`**，`2` 个 `narrow_passage`。

因此，用户要求的“在 `calib_hard_v1` 中调出 `top 5 worst flange cases`”在字面上是**做不到的**：

- `flange` 样本数只有 `1`；
- 同时，`calib_hard_v1` 内也**没有正向的 `narrow_passage` 样本**可以与之构成“失败 vs 成功”的有意义对比。

### 2.2 本轮采用的诊断策略

为了不伪造数据口径，本轮做法是：

1. **先如实报告 `calib_hard_v1` 的 coverage 限制**；
2. 再使用**上一轮已锁定的 `CX10-D` public `exp4` 输出**做补充诊断：
   - 取 `parasol_narrow/test` 中 `flange` 的最差 `5` 个样本；
   - 取 `narrow_passage` 中 `CX10-D` 表现最好的样本；
3. 明确说明：
   - 这部分 public 诊断**只用于 failure analysis / design scout**；
   - **不用于调参**，也**不作为通过门槛的正式验证**。

## 3. Failure Case Diagnostic

### 3.1 `calib_hard_v1` 内部信号

在 `calib_hard_v1` 上，`CX10-D` 的 family evidence 本身就很稀薄：

- 唯一 `flange` case 在 `calib_val` 上基本是 **tie**；
- 两个 `narrow_passage` case 的 `exp_delta` 分别约为 `-3` 和 `-138`；
- 也就是说，**`calib_hard_v1` 内并不存在 “明显正向 narrow vs 明显负向 flange” 的干净对照组**。

这也是为什么 `CX10-D-Selective` 在 dev 上只能学到一个很粗糙的 family proxy——训练集里根本没有足够的 `flange` 正/负对照去学更细的判别边界。

### 3.2 public `exp4` 中真正的失败与成功样本

#### Worst `flange` failures under locked `CX10-D`

来自 `outputs/rs_p0cx12_design_scout_v1/worst_public_flange_top5.csv`：

- `sample_000015.npz`: `exp_delta = -2640.0`（灾难性失败）
- `sample_000014.npz`: `exp_delta = 0.0`
- `sample_000016.npz`: `exp_delta = 0.0`
- `sample_000017.npz`: `exp_delta = 0.0`
- `sample_000013.npz`: `exp_delta = +26.0`

**关键读法**：
- `flange` 并不是“整族都坏”；
- 真正的问题是：**存在少数 catastrophic flange instances**，它们会在整体均值上主导负结论。

#### Best `narrow_passage` cases under locked `CX10-D`

来自 `outputs/rs_p0cx12_design_scout_v1/best_public_narrow_top5.csv`：

- `sample_000005.npz`: `exp_delta = +395.0`
- 其余 `narrow_passage` 样本基本都是 `0.0`

**关键读法**：
- `narrow_passage` 的正向 sketch signal 也不是整个 family 都有；
- 它同样是**少量 instance-specific positive signal**。

因此，`CX10` / `CX11` 的根本误区已经很明确：

> 决策对象不是“family”，而是“某些特定几何状态下的 token validity”。

## 4. Feature Comparison: Why Current Features Fail

### 4.1 当前特征空间存在强重叠

对比 `worst flange top-5` 与 `best narrow_passage`，当前 `CX10-D` / `CX11` 实际可用的特征呈现出明显饱和和重叠：

1. **局部 clearance 几乎完全相同**
   - `flange mean = 0.5`
   - `narrow mean = 0.5`（只看有 gate 的样本时）
   - 说明“当前位置可行”并不等于“当前 sketch token 合法”。

2. **corridor width 几乎完全相同**
   - `flange mean ≈ 1.0`
   - `narrow mean ≈ 1.0`
   - 这意味着当前 `morph_width / corridor_width` 更像“有通道”指标，而不是“通道是否会把你送进 flange trap”。

3. **heading-to-goal 基本饱和**
   - 两组样本中有 gate 的 case 上，`heading_to_goal_cos ≈ 1.0`
   - 说明“朝向目标”本身并不能区分“真出口”与“假出口 pocket”。

4. **RS / bottleneck 代理量也高度饱和**
   - `bottleneck ≈ 1.0`；
   - `scene_hard`、`scene_misc`、`scene_bridge` 的区间重叠都很大；
   - `feature_overlap_public_flange_vs_narrow.csv` 中：
     - `scene_hard` 的 normalized overlap `≈ 0.83`
     - `scene_misc` 的 normalized overlap `≈ 0.95`
     - `scene_bridge` 的 normalized overlap `≈ 0.91`

5. **当前 escape/progress 特征几乎失效**
   - `reverse_escape = 0.0`
   - `forward_escape = 0.0`
   - 当前提取方式没有提供可用的 token-level exit discrimination。

### 4.2 最关键的对照：catastrophic flange 与 best narrow 几乎“同像”

把最糟 `flange` case `sample_000015` 与最优 `narrow_passage` case `sample_000005` 对比：

- 两者都有：
  - `top_gate_score = 1.0`
  - `top_gate_inner_mode = 2`
  - `clearance = 0.5`
  - `corridor_width ≈ 1.0`
  - `heading_to_goal_cos = 1.0`
  - `bottleneck ≈ 1.0`
- 但结果一个是 `-2640`，一个是 `+395`

这直接说明：

> 当前特征空间只能识别“这里像个 bottleneck”，却识别不了“这个 bottleneck 对应的是可穿越窄通道，还是 flange-style 假出口陷阱”。

### 4.3 当前真正缺失的特征是什么？

基于上述重叠，本轮判断当前缺的不是更复杂的分类头，而是**新的几何判别量**：

1. **Local Trap Detection**
   - 当前特征知道“局部窄”，但不知道“窄口后面是不是 pocket/trap”；
   - 需要显式测量：
     - 入口后方 pocket 面积；
     - 出口是否真实存在；
     - 局部 free-space 是否呈“前窄后宽的死胡同侧袋”结构。

2. **Exit Visibility / Exit Reachability**
   - 当前特征没有测“沿 sketch token 继续走，是否真的能看到/接近出口”；
   - 需要显式测量：
     - gate 前向视线上的最小 clearance；
     - 沿目标方向的短程 free-ray 长度；
     - token 所指向方向是否存在可持续 anchor decrease。

3. **Search-State Evidence**
   - 当前全部决策几乎只看静态几何；
   - 但 catastrophic flange 更像是“静态上像窄口、动态上会把搜索带进局部困境”的 case；
   - 因此需要补入：
     - open-list entropy / branching collapse；
     - 局部重复扩展；
     - 当前阶段是否真的进入 bottleneck stall。

## 5. CX12 Candidate Directions

### CX12-A: `RS-GHF` — Geometry-Aware Hard Filter

**类型**：`explicit geometric predicate filter`

**核心想法**：
1. 不再先学 defer head；
2. 直接为 sketch activation 设计一组 cheap、显式的几何谓词：
   - `exit_visibility >= τ_exit`
   - `goal_ray_clearance >= τ_goal`
   - `trap_score <= τ_trap`
   - `pocket_to_exit_ratio <= τ_ratio`
3. 只有全部通过时才允许激活 sketch。

**理论抓手**：
- 这是 hard safety filter，而不是软概率分类；
- 在线复杂度可保持在 `O(K · C_geom)`，其中 `K` 是少量 token，`C_geom` 是廉价几何测量。

**预期优势**：
- 最直接针对 `flange` catastrophic false positive；
- 比 `CX11-B` 更不容易学成 over-defer，因为它不是按 family proxy 全关，而是按 trap predicate 精确拦截。

**主要风险**：
- 若谓词阈值过严，会继续把 `narrow_passage` 正项一起滤掉；
- 需要先把 `exit_visibility / trap_score` 这些新特征定义清楚。

---

### CX12-B: `RS-CSA` — Contrastive Sketch Adjustment

**类型**：`positive/negative sketch composition`

**核心想法**：
1. 放弃 “要么用 sketch，要么不用” 的二元决策；
2. 允许在高风险 flange-like states 上施加 **negative sketch**：
   - 不是直接回退 baseline；
   - 而是显式压制当前有害的 `reverse/thread` token；
3. 在 positive `narrow_passage` states 上继续叠加正向 sketch。

**理论抓手**：
- 这相当于把 intervention 从 binary gate 升级为 signed adjustment；
- 允许 “局部减法” 而不是全局 abstain，从而更有希望保住 sparse positive signal。

**预期优势**：
- 有机会避免 `CX11` 那种“消害也消益”的 over-defer；
- 更贴合当前 evidence：`flange` 的问题不是“绝不能动”，而是“某类 token 动错了”。

**主要风险**：
- 设计空间更大，验证复杂度更高；
- 若 negative sketch 定义不清，会重新走向 `CX10-D` 式误干预。

---

### CX12-C: `RS-SSG` — Search-State Gating

**类型**：`search-state conditional activation`

**核心想法**：
1. 将 sketch activation 的依据从静态几何扩展到搜索状态；
2. 只有在搜索已经表现出局部困境时才允许 sketch 激活，例如：
   - open-list entropy 降低；
   - accepted successor ratio 连续下降；
   - anchor progress 停滞；
3. 静态几何只提供先验候选，真正触发由 search-state evidence 决定。

**理论抓手**：
- 这是从 `state-only intervention` 转向 `state × search-dynamics intervention`；
- 在线依然不需要深模型，只需要 planner hook 的 cheap counters。

**预期优势**：
- 直接针对 `flange` 的“初始阶段像窄口、搜索展开后才显露为 trap”问题；
- 也更有希望保住 `narrow_passage` 的正项，因为真正的狭窄通道通常会伴随持续的 search bottleneck 证据。

**主要风险**：
- 需要额外维护 search-state 统计量；
- 若触发过晚，可能 miss 掉 sketch 最有效的 setup 时机。

## 6. Recommended Order

推荐顺序：`CX12-A -> CX12-C -> CX12-B`

1. **先做 `CX12-A / RS-GHF`**
   - 最低风险；
   - 最直接对应本轮诊断结论：现有特征缺的是 trap / exit discrimination；
   - 最适合作为 “能否用显式几何谓词把 catastrophic flange cases 拦掉” 的第一发验证。

2. **再做 `CX12-C / RS-SSG`**
   - 如果单靠静态几何仍分不开，就把触发条件提升到 search-state；
   - 这是最有希望同时保住 `narrow_passage` 正项的中风险路线。

3. **最后做 `CX12-B / RS-CSA`**
   - 最有潜力打破 “消害=消益” 的二元困境；
   - 但也是设计与调试成本最高的一条，因此放在后序。

## 7. Final Recommendation

本轮诊断给出的核心结论是：

> `Flange` 与 `Narrow Passage` 在当前 `CX10/CX11` 使用的特征空间里存在高度重叠，尤其在 `clearance / corridor width / heading-to-goal / bottleneck` 这些主特征上几乎饱和重合。

因此：

- `CX11` 失败不是因为 defer 思路本身错了；
- 而是因为 **defer / verify 所依据的特征没有足够区分度**；
- 下一轮必须显式补入：
  - `local trap detection`
  - `exit visibility / exit reachability`
  - `search-state stall evidence`

也就是说，`CX12` 的主命题不应是：

> 再做一个更聪明的 defer head

而应是：

> **Give the gate the right evidence.**

当前首选执行入口：`CX12-A / RS-GHF`。
