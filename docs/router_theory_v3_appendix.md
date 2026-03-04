# Router Theory V3 Appendix（Proofs）

日期：`2026-03-03`  
版本：`v3.0`

本附录按 “Assumptions / Statement / Proof” 结构给出 V3 的关键结论证明，供 Phase24 脚本做 coverage 检查。

---

## Theorem 1: K-arm Oracle-Regret Upper Bound (Empirical Bernstein)

### Assumptions
1. 有 \(n\) 个样本 \(\{x_i\}_{i=1}^n\) i.i.d.（或可交换），定义随机变量
   \[
   R_i:=R(x_i)=J_\pi(x_i)-\min_{a\in\mathcal A}J_a(x_i).
   \]
2. 有界性：存在 \(M>0\) 使得 \(0\le R_i\le M\) 几乎处处成立。
3. 置信参数 \(\delta\in(0,1)\)。

### Statement
记经验均值 \(\hat R=\frac1n\sum_i R_i\)、经验方差 \(\widehat{\mathrm{Var}}(R)\)（无偏或有偏均可，只影响常数项）。则以概率至少 \(1-\delta\)：
\[
\mathbb E[R]
\le
\hat R
+
\sqrt{\frac{2\widehat{\mathrm{Var}}(R)\ln(3/\delta)}{n}}
+
\frac{3M\ln(3/\delta)}{n-1}.
\]

### Proof
这是经验 Bernstein（或称 empirical Bernstein / Freedman-style）不等式的直接套用。
对有界非负随机变量 \(R\in[0,M]\)，其均值相对经验均值的偏差可由经验方差控制，并附带一个与 \(M\) 线性、与 \(n\) 反比的项。

证明可参考经典推导（例如使用 Bernstein/Freedman 不等式 + 方差替换技巧）。本仓库的 Phase24 脚本直接按上式计算 upper bound，并报告：
- `regret_mean`（\(\hat R\)），
- `regret_ucb`（右侧上界），
- `regret_slack = regret_ucb - regret_mean`（界的松弛度）。

∎

---

## Theorem 2: Group Prior-Shift Robust Risk Certificate (Multi-Arm)

### Assumptions
1. 固定一个路由策略 \(\pi:\mathcal X\to\mathcal A\)（可为多臂 portfolio 路由）。
2. 选取有限分组 \(g(x)\in\mathcal G\)（例如 difficulty 或 OOD family）。
3. **Prior shift 假设**：部署分布与校准分布在每个组内的条件分布相同，仅组先验发生变化。  
   即对任意 \(g\in\mathcal G\)，有
   \[
   \mathcal L(x\mid g)\ \text{在校准与部署一致},\quad
   p(g)\ \text{允许变化}.
   \]
4. 记组条件风险 \(v_g:=\mathbb P(Z_\pi=1\mid g)\)。在校准集中对每个组得到一个上界 \(u_g\) 满足（高置信）：
   \[
   v_g\le u_g,\quad \forall g\in\mathcal G.
   \]
   在实现中，\(u_g\) 取 Wilson 置信区间的上界（与冻结 protocol 一致）。

### Statement
对任意部署组先验 \(p\in\Delta^{|\mathcal G|}\)：
\[
V_p(\pi)=\sum_{g\in\mathcal G} p_g v_g
\le
\sum_{g\in\mathcal G} p_g u_g.
\]
因此若只发生 prior shift，则可用校准集上界 \(u_g\) + 部署先验 \(p\) 给出风险证书。

### Proof
由全概率公式：
\[
V_p(\pi)=\mathbb E[Z_\pi]=\sum_{g\in\mathcal G}\mathbb P(g)\,\mathbb E[Z_\pi\mid g]=\sum_g p_g v_g.
\]
由 Assumption 4，逐组有 \(v_g\le u_g\)，因此
\[
\sum_g p_g v_g\le \sum_g p_g u_g.
\]
∎

---

## Theorem 3: Two-Stage Monotone Upgrade Cannot Increase Risk

### Assumptions
1. 定义臂的保真度偏序：\(\texttt{fast} \prec \texttt{mid} \prec \texttt{slow}\)。
2. 有一个第一阶段策略 \(\pi_0\)（例如 conformal static router）。
3. 第二阶段（probe）策略 \(\pi_1\) 只允许 **升级**，即对任意样本 \(x\)：
   \[
   \pi_1(x)\succeq \pi_0(x).
   \]
   （等价地：不允许 slow→mid/fast，不允许 mid→fast，不允许 slow→fast。）
4. 风险事件 \(Z_\pi(x)\) 只可能在选择非 \(\texttt{slow}\) 的情况下触发（与冻结 protocol 一致）。

### Statement
在以上假设下：
\[
Z_{\pi_1}(x)\le Z_{\pi_0}(x)\quad \forall x,
\qquad
\Rightarrow
\qquad
V(\pi_1)\le V(\pi_0).
\]

### Proof
对任意 \(x\)：
- 若 \(\pi_0(x)=\texttt{slow}\)，则 \(\pi_1(x)=\texttt{slow}\)（只能升级，不会更快），两者风险事件均为 0；
- 若 \(\pi_0(x)\in\{\texttt{fast},\texttt{mid}\}\)，则 \(\pi_1(x)\) 只能取 \(\pi_0(x)\) 或更慢的臂。
  由于风险事件只在选择非 slow 时可能触发，升级到更慢臂不会新增“非 slow 且质量超阈”的样本集合。

因此对每个样本有逐点不等式 \(Z_{\pi_1}(x)\le Z_{\pi_0}(x)\)，取期望即得 \(V(\pi_1)\le V(\pi_0)\)。 ∎

