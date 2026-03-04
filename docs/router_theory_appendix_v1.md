# Router Theory V1 Appendix（完整证明）

## A. 记号
设样本 \(x_i\) 独立同分布（或在分层内同分布），策略 \(\pi\) 给出 `fast/slow` 决策。定义
\[
Z_\pi(x_i)=\mathbf{1}\{\pi(x_i)=\texttt{fast}\land \Delta L_{\text{rel}}(x_i)>\epsilon_{\text{rel}}\}\in\{0,1\}.
\]
记 \(V(\pi)=\mathbb{E}[Z_\pi]\)。

---

## B. 定理 1 证明（有限样本违约率上界）
**命题**：对固定 \(\pi\)，在 \(n\) 个样本上 \(K=\sum_i Z_\pi(x_i)\)，\(\hat V=K/n\)。Wilson 上侧置信界 \(U_W(K,n;\alpha)\) 满足在置信度 \(1-\alpha\) 下
\[
V(\pi)\le U_W(K,n;\alpha).
\]

**证明**：
1. \(Z_\pi(x_i)\) 是 Bernoulli 随机变量，参数为 \(p=V(\pi)\)。  
2. \(K\sim \text{Binomial}(n,p)\)。  
3. Wilson 区间是对二项比例 \(p\) 的经典近似置信区间，由 score test 反演得到。  
4. 因此在名义置信度 \(1-\alpha\) 下，\(p\) 落在该区间内，上侧边界即满足
   \[
   p\le U_W(K,n;\alpha).
   \]
5. 代回 \(p=V(\pi)\) 即得。证毕。  

---

## C. 定理 2 证明（Probe 单调安全性）
**命题**：若
\[
\{x:\pi_p(x)=\texttt{fast}\}\subseteq \{x:\pi_c(x)=\texttt{fast}\},
\]
则
\[
V(\pi_p)\le V(\pi_c).
\]

**证明**：
1. 对任意 \(x\)，若 \(\pi_p(x)=\texttt{fast}\)，则由子集关系必有 \(\pi_c(x)=\texttt{fast}\)。  
2. 因此逐点有
   \[
   Z_{\pi_p}(x)
   =\mathbf{1}\{\pi_p(x)=\texttt{fast}\land \Delta L_{\text{rel}}(x)>\epsilon\}
   \le
   \mathbf{1}\{\pi_c(x)=\texttt{fast}\land \Delta L_{\text{rel}}(x)>\epsilon\}
   =Z_{\pi_c}(x).
   \]
3. 对两侧取期望即得
   \[
   V(\pi_p)\le V(\pi_c).
   \]
证毕。  

---

## D. 定理 3 证明（分层先验修正）
**命题**：难度分层 \(d\) 下，若 \(V_d(\pi)=\mathbb{E}[Z_\pi\mid d]\)，目标先验 \(p_{\text{tar}}(d)\) 已知，则
\[
V_{\text{tar}}(\pi)=\sum_d p_{\text{tar}}(d)V_d(\pi).
\]
估计量
\[
\hat V_{\text{tar}}(\pi)=\sum_d p_{\text{tar}}(d)\hat V_d(\pi),\quad
\hat V_d=\frac{1}{n_d}\sum_{i:d_i=d}Z_\pi(x_i),
\]
在分层条件分布稳定时是无偏（或一致）估计。

**证明**：
1. 由全期望公式，
   \[
   V_{\text{tar}}(\pi)=\mathbb{E}_{d\sim p_{\text{tar}}}\big[\mathbb{E}[Z_\pi\mid d]\big]
   =\sum_d p_{\text{tar}}(d)V_d(\pi).
   \]
2. 在每个分层 \(d\) 内，\(\hat V_d\) 是 Bernoulli 均值估计，满足 \(\mathbb{E}[\hat V_d]=V_d\)（或在轻微偏离 i.i.d. 时一致）。  
3. 线性组合保持无偏（或一致）：
   \[
   \mathbb{E}[\hat V_{\text{tar}}]
   =\sum_d p_{\text{tar}}(d)\mathbb{E}[\hat V_d]
   =\sum_d p_{\text{tar}}(d)V_d
   =V_{\text{tar}}.
   \]
证毕。  

---

## E. 误差分解不等式推导
由定义
\[
V_{\text{tar}}(\pi_p)=V_{\text{eval}}(\pi_p)+\Delta_{\text{shift}},
\quad
\Delta_{\text{shift}}=V_{\text{tar}}(\pi_p)-V_{\text{eval}}(\pi_p).
\]
对 \(V_{\text{eval}}(\pi_p)\) 加减 \(V_{\text{eval}}(\pi_c)\)：
\[
V_{\text{tar}}(\pi_p)
=V_{\text{eval}}(\pi_c)-\big(V_{\text{eval}}(\pi_c)-V_{\text{eval}}(\pi_p)\big)+\Delta_{\text{shift}}.
\]
再由定理 1：
\[
V_{\text{eval}}(\pi_p)\le U_W(\pi_p)
\Rightarrow
0\le U_W(\pi_p)-V_{\text{eval}}(\pi_p)=:\text{slack}.
\]
并用 \(|\Delta_{\text{shift}}|\) 上界绝对偏移，得到
\[
V_{\text{tar}}(\pi_p)
\le
V_{\text{eval}}(\pi_c)
-\underbrace{\big(V_{\text{eval}}(\pi_c)-V_{\text{eval}}(\pi_p)\big)}_{\text{safety gain}}
+\underbrace{\text{slack}}_{\text{finite-sample}}
+|\Delta_{\text{shift}}|.
\]
证毕。  

---

## F. 与代码对应
`scripts/run_router_phase11_theory.py` 对应实现：
1. 定理 1：逐 seed 计算 Wilson 上界与 `probe` 实测违约率 gap；  
2. 定理 2：验证 `probe_fast_subset_of_conf` 与 `probe_violation<=conf_violation`；  
3. 定理 3：用 `router_phase9_public_v1` 的 difficulty 先验修正 `router_mixed_v1` 风险；  
4. 误差分解：逐 seed 验证 `decomp_lhs_target_risk <= decomp_rhs_upper`。  

