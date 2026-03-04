# Router Theory V1: Conformal + Probe 联合策略的有限样本保证

状态：`frozen-draft`  
版本：`v1.0`  
日期：`2026-03-02`

## 1. 设定与记号
我们考虑单次规划样本 \(x\) 的违约事件：
\[
Z_\pi(x)=\mathbf{1}\{\pi(x)=\texttt{fast} \land \Delta L_{\text{rel}}(x)>\epsilon_{\text{rel}}\},
\]
其中 \(\epsilon_{\text{rel}}=1.5\%\)。策略 \(\pi\) 的总体违约率定义为
\[
V(\pi)=\mathbb{E}[Z_\pi].
\]

P8 中的两级策略分别记为：
1. \(\pi_c\)：strict conformal 路由；
2. \(\pi_p\)：probe-then-commit 路由（在 \(\pi_c\) 基础上做二次修正）。

## 2. 主定理

### 定理 1（有限样本违约率上界）
给定任意固定策略 \(\pi\)，在 \(n\) 个 i.i.d. 测试样本上记
\[
K=\sum_{i=1}^{n} Z_\pi(x_i),\quad \hat V=\frac{K}{n}.
\]
令 \(U_W(K,n;\alpha)\) 为 Wilson 单侧（上侧）置信上界（本文用 \(1-\alpha=95\%\)）。则在置信度 \(1-\alpha\) 下，
\[
V(\pi)\le U_W(K,n;\alpha).
\]

在本文 P8/P11 评测中，\(\pi=\pi_p\) 时每个 seed 的上界与实测违约率差值
\[
U_W-\hat V
\]
均不超过 `2%`。

### 定理 2（Probe 单调安全性）
若 probe 阶段仅允许将 conformal 的 `fast` 决策翻转为 `slow`，即
\[
\{x:\pi_p(x)=\texttt{fast}\}\subseteq \{x:\pi_c(x)=\texttt{fast}\},
\]
则必有
\[
V(\pi_p)\le V(\pi_c).
\]
换言之，probe 不会增加违约概率。

### 定理 3（分层部署先验下的选择偏差修正）
记难度分层 \(d\in\{\texttt{easy, medium, hard}\}\)，评测分布先验为 \(p_{\text{eval}}(d)\)，部署目标先验为 \(p_{\text{tar}}(d)\)。若条件分布稳定（同层内分布一致），则
\[
V_{\text{tar}}(\pi)=\sum_d p_{\text{tar}}(d)V_d(\pi),
\]
其中 \(V_d(\pi)=\mathbb{E}[Z_\pi\mid d]\)。对应估计量
\[
\hat V_{\text{tar}}(\pi)=\sum_d p_{\text{tar}}(d)\hat V_d(\pi)
\]
是对部署风险的无偏（或渐近无偏）修正估计。

这给出从 `router_mixed_v1`（均匀难度）到 `router_phase9_public_v1`（非均匀难度）部署分布的可解释修正路径。

## 3. 误差分解（Conformal + Probe 联合）
对目标部署风险，可写为
\[
V_{\text{tar}}(\pi_p)
=V_{\text{eval}}(\pi_p)+\Delta_{\text{shift}},
\]
其中 \(\Delta_{\text{shift}}=V_{\text{tar}}(\pi_p)-V_{\text{eval}}(\pi_p)\)。

再结合定理 1 与定理 2：
\[
V_{\text{tar}}(\pi_p)
\le
V_{\text{eval}}(\pi_c)
-\underbrace{\big(V_{\text{eval}}(\pi_c)-V_{\text{eval}}(\pi_p)\big)}_{\text{safety gain}}
+\underbrace{\big(U_W(\pi_p)-V_{\text{eval}}(\pi_p)\big)}_{\text{finite-sample slack}}
+|\Delta_{\text{shift}}|.
\]

该分解清晰地区分了三类项：
1. `safety gain`：probe 相对 conformal 的安全增益（应为非负）；  
2. `finite-sample slack`：有限样本统计裕度；  
3. `distribution shift`：评测-部署先验差异导致的偏移。  

## 4. 与实验的一致性（P11 校验口径）
P11 使用 `scripts/run_router_phase11_theory.py` 进行 5-seed 自动校验，核心 gate：
1. 5 seeds 完整；
2. `probe` 的理论上界与实测违约率 gap `<=2%`；
3. `probe` 违约率不高于 `conformal`（单调安全）；
4. `probe` 快速集合是 `conformal` 快速集合子集；
5. `OG` 改善方向在 5 seeds 一致为正；
6. 误差分解不等式逐 seed 成立。  

产物路径：
- `outputs/router_phase11_theory_v1/stats.json`
- `outputs/router_phase11_theory_v1/seed_metrics.csv`
- `outputs/router_phase11_theory_v1/difficulty_shift_metrics.csv`
- `reports/router_phase11_theory_v1.md`

## 5. 证明索引
定理 1~3 的完整证明见：
- `docs/router_theory_appendix_v1.md`

