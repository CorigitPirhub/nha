# P0-CX11 Design Scout V1

Status: `design-scout / no-code`
Date: `2026-03-11`

## 1. Why `CX11` Is Needed

`CX10-D-Selective` 的最终结果已经把当前失败机理进一步钉死：

- `CX10-D / RS-LAS` 的正向信号并没有完全消失，`exp4` 上 `narrow_passage` 仍有 `+98.75` 的局部正项；
- 但一旦 sketch 被错误地施加到 `flange`，就会出现灾难性负项（`-522.8`），并且这种误伤足以吞掉全部收益；
- 本轮新增的 `Family-Aware Abstention Guard` 虽然把 overall overhead 压到了 `0.149726`，但 `exp4` overall `exp_delta = -145.222`，`flange exp_delta` 仍为负，且 `narrow_passage` 的正项也没被保住。

这说明 `CX10` 的核心瓶颈已经从：

> “如何把语义编译得更便宜？”

转变为：

> “如何在 instance-level 上**可靠地知道什么时候应该 defer / abstain**，并且只在 token truly valid 的时候才执行 sketch？”

因此 `CX11` 的重点不应再是继续做更复杂的 sketch 生成器，而应转向：

1. **更鲁棒的 sketch token 表示**：让 token 自带可验证语义，而不是仅凭 scene-level 相似性触发；
2. **learning-to-defer / calibrated abstention**：把“是否使用 sketch”本身升格为主学习对象；
3. **token-level verification**：不是预测“像不像 narrow_passage”，而是验证“当前 token 在当前几何下是否真的成立”。

## 2. Literature Scan

### 2.1 Sketch / Program Robustness

1. **RT-Trajectory: Robotic Task and Motion Planning via Hierarchical Sketches** (2025, arXiv)
   - Link: <https://arxiv.org/abs/2503.22195>
   - 启发：sketch 不应只是 waypoint list，而应是带层级语义的 task-motion scaffold；
   - 局限：其 sketch 主要服务长程任务分解，不直接约束 nonholonomic bottleneck token 的几何有效性。

2. **Combined Task and Motion Planning via Sketch Decompositions** (OpenReview)
   - Link: <https://openreview.net/forum?id=ojc4aWQfP2>
   - 启发：将长程规划压缩为 sketch/decomposition 是合理的，但 sketch 必须与后续可执行验证强绑定；
   - 局限：更偏 symbolic task skeleton，而不是 local maneuver token validity。

**批判性结论**：
- 现有 sketch 工作证明了“先给 sketch，再让底层 planner 补完”是对的；
- 但对本项目真正缺失的，不是 sketch 本身，而是 **token validity**：
  - `reverse-setup-right` 在当前 gate 几何下是否真的成立？
  - 当前 corridor 是否支持 `thread-right` 而不是 `thread-left`？
- 换句话说，`CX11` 需要的是 **verifiable sketch token**，而不是更花哨的 sketch generator。

### 2.2 Learning-to-Defer / Selective Abstention

1. **SLTD: Learning to Defer for Sequential Decision-Making under Uncertainty** (2024, arXiv)
   - Link: <https://arxiv.org/abs/2402.01830>
   - 启发：defer 不应只看单点置信度，而应建模 sequential setting 中 defer 的长期代价；
   - 局限：面向一般 sequential decision-making，尚未针对 planner-side intervention 的 cheap verifier 结构。

2. **Beyond Confidence: Trustworthy Learning-to-Defer via Conformal Prediction Sets** (2023, arXiv)
   - Link: <https://arxiv.org/abs/2307.04993>
   - 启发：单一 confidence 往往不足以做可信 defer；需要 calibrated set / coverage-aware abstention；
   - 局限：主要讨论分类/决策系统的可信 defer，没有 sketch token 的几何支持测试。

3. **Learning to Defer to Multiple Experts: Integrating Uncertainty in Machine Teaching** (2024, arXiv)
   - Link: <https://arxiv.org/abs/2410.06435>
   - 启发：不必只在“apply sketch / fallback baseline”二元之间切换，也可以做多 expert defer；
   - 局限：当前项目的 experts 不是人类/黑箱模型，而是不同 intervention template，需要结构化接口。

4. **Selective Omniprediction and Fair Abstention** (OpenReview)
   - Link: <https://openreview.net/forum?id=BoYGLpNXZd>
   - 启发：选择性 abstention 的核心不是“多做一点预测”，而是 **识别 support boundary**；
   - 局限：面向泛化预测理论，不直接给出 motion-planning token validity 的实现模板。

**批判性结论**：
- `CX10-D-Selective` 失败的根本原因，不是 guard 太轻，而是 guard 只学了“像不像 narrow family”，没有学“当前 sketch token 是否落在可靠支持域内”；
- 因而 `CX11` 必须把 `defer` 设计成**一等公民**：
  - defer score 要校准；
  - defer 逻辑要 support-aware；
  - defer 的对象最好是 token / template，而不是整个 scene 粗分类。

## 3. Problem Reframing for `CX11`

`CX11` 的问题不再是：

> 如何生成更强的 sketch？

而是：

> 如何为每个 sketch token 构建 **可校准的有效性判别 + 可验证的 defer 机制**，使错误干预在进入 planner 前就被拦住？

这意味着 `CX11` 的默认策略必须是：

- **baseline first**；
- **token only when verified**；
- **defer whenever support is weak**。

## 4. Frozen Candidate Directions

### CX11-A: `RS-RST` — Robust Sketch Tokenization

**类型**：`typed sketch token redesign`

**核心想法**：
1. 将当前 `CX10-D` 的 macro sketch 从“mode tag”升级为带约束的 typed token，例如：
   - `pre_reverse(right, pocket>=τ, heading_gap>=τ)`；
   - `thread(right, corridor_band=[a,b], exit_visibility>=τ)`；
2. 每个 token 在执行前必须通过一组 cheap predicate checks；
3. 任一 predicate 失败则整 token abstain，直接回退 `CX3-D`。

**如何继承 `CX8-D` 的有效语义**：
- 保留 `reverse-setup -> thread-through` 的多步语义；
- 但不再把它编码成“裸 mode”，而是编码成带几何前提的 token。

**为什么比 `CX10-D` 更稳**：
- `CX10-D` 失败在于 sketch token 太粗，`flange` 也能错误命中；
- `RS-RST` 通过 token-side predicates 明确要求“必须真的有 setup pocket / corridor support / exit signature”，否则不触发。

**理论抓手**：
- sketch token 从 latent suggestion 升级为 `token + verifier`，本质上是 **specification-constrained planning hint**；
- 在线成本仍是 `O(K)` token checks，而不是 per-successor 推理。

**主要风险**：
- token schema 设计不好会过于僵硬；
- 若 predicates 太强，可能把全部正项也一起关掉。

---

### CX11-B: `RS-LDS` — Learning-to-Defer Sketcher

**类型**：`instance-specific defer controller`

**核心想法**：
1. 不再先预测“该用哪个 sketch”，而是先预测“当前是否值得把 control 权交给 sketch expert”；
2. experts 至少包含：
   - `accepted CX3-D`；
   - `CX10-D sketch`；
   - 可选的 `safe-template subset`；
3. defer head 输出 calibrated defer score，只在 coverage 足够时才启用 sketch expert。

**如何继承 `CX8-D` 的有效语义**：
- 不丢掉 `CX10-D` 的 sketch branch；
- 但把主学习对象从 sketch content 改为 **expert selection / defer decision**。

**为什么比 `CX10-D-Selective` 更稳**：
- 当前 selective guard 只是浅层 family proxy；
- `RS-LDS` 明确以 “wrong intervention cost” 为训练目标，直接学习“什么时候必须回退 baseline”。

**理论抓手**：
- learning-to-defer + conformal calibration；
- 在线仅需 `O(1)` defer score + branch select。

**主要风险**：
- 若 dev-only defer labels 噪声太大，可能学到“过度 abstain”；
- 需要重新定义 expert cost / defer loss。

---

### CX11-C: `RS-CSV` — Counterfactual Sketch Verifier

**类型**：`proposal-verifier architecture`

**核心想法**：
1. 继续使用 `CX10-D` 当前 sketch generator 作为 proposal；
2. 新增一个极便宜的 verifier，不判断 family，而是判断：
   - token 落地后是否改善 local anchor progress；
   - setup pocket 是否足够；
   - thread token 是否与 corridor handedness 一致；
3. 只有 proposal 与 verifier 同时为正时才真正注入 sketch bias。

**如何继承 `CX8-D` 的有效语义**：
- proposal 仍来自现有 sketch / bundle semantics；
- verifier 负责把 `CX8-D Heavy` 中隐含的 counterfactual validity 显式化。

**为什么比 `CX10-D-Selective` 更稳**：
- 现有 guard 在 scene-level 做 family proxy；
- `RS-CSV` 改为 token-level 的局部反事实校验，更贴近 `CX8-D Heavy` 的真正成功机制。

**理论抓手**：
- proposal-verifier 分解；
- online 复杂度为少量 token checks 与局部 analytic tests，仍接近常数级。

**主要风险**：
- verifier 若与真实 improvement 相关性不够，会退化成无效拒绝器；
- 需要构建更细的 token-level counterfactual dataset。

## 5. Recommended Order

推荐顺序：`CX11-B -> CX11-C -> CX11-A`

1. **先做 `CX11-B / RS-LDS`**：
   - 最直接命中本轮失败机理：instance-level defer 学得不够；
   - 对现有 `CX10-D` 代码复用最多，最低风险。
2. **再做 `CX11-C / RS-CSV`**：
   - 若单纯 defer 仍不够，下一步就该把“为什么 safe”变成 token-level verifier；
   - 它最贴近 `CX8-D Heavy` 的反事实语义。
3. **最后做 `CX11-A / RS-RST`**：
   - 这是更大规模的 token redesign；
   - 方法创新最高，但 schema 设计成本也最高，应放在 `B/C` 之后。

## 6. Minimum Acceptance Bar

`CX11` 任一路线若要进入下一阶段严格验证，至少需要：

1. 在 `public exp4` 上满足：
   - `exp_delta > 0`；
   - `mean_time_overhead_ratio < 0.30`；
   - `flange exp_delta >= 0`；
2. 在 `mp/csm` 上与 accepted `CX3-D` 保持 ordinary-support 一致或近似一致；
3. 默认存在 `defer / abstain-by-default`；
4. 不重新引入 per-successor 深模型推理。

## 7. Final Recommendation

`CX10` 的失败说明：

- 单纯把 semantic sketch 编译出来还不够；
- **真正决定成败的是：能否在 instance/token 级别可信地 defer。**

因此 `CX11` 的冻结主命题应是：

> **Verify or defer every sketch token.**

也就是说，下一轮不应再单独优化 sketch generator，而应围绕：

- token robustness；
- calibrated defer；
- counterfactual verifier；

这三者去重建一条真正稳健的、不会在 `flange` 误伤的 low-cost semantic intervention 路线。
