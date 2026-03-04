# Router Theory V2 Appendix（完整证明）

## Notation
设 \(x\) 为样本，\(\pi\) 为路由策略，\(\epsilon\) 为质量违约阈值。  
定义违约指示变量：
\[
Z_\pi(x)=\mathbf{1}\{\pi(x)=\texttt{fast}\land \Delta L_{\text{rel}}(x)>\epsilon\}.
\]
定义分层风险 \(v_d=\mathbb E[Z_\pi\mid d]\)。

## Theorem A: Stratified Shift-Robust Risk Upper Bound

### Assumptions
1. 分层集合 \(d\in\{\texttt{easy,medium,hard}\}\)。  
2. 每层风险上界 \(u_d\) 满足 \(v_d\le u_d\)。  
3. 目标先验 \(p\in\Delta^3\)（概率单纯形）。

### Statement
对任意 \(p\in\Delta^3\)：
\[
V_p(\pi)=\sum_d p_d v_d \le \sum_d p_d u_d.
\]
若 \(p\) 仅知在 \(\mathcal U_\rho=\{p\in\Delta^3:\|p-p_0\|_1\le \rho\}\)，则
\[
\sup_{p\in\mathcal U_\rho}V_p(\pi)\le \sup_{p\in\mathcal U_\rho}\sum_d p_d u_d.
\]

### Proof
由假设 2，逐层有 \(v_d\le u_d\)。  
对任意 \(p\in\Delta^3\)，因 \(p_d\ge 0\)，逐项乘以 \(p_d\) 后求和：
\[
\sum_d p_d v_d \le \sum_d p_d u_d.
\]
即得第一式。  
第二式由第一式对 \(p\in\mathcal U_\rho\) 取上确界直接得到：
\[
\sup_{p\in\mathcal U_\rho}V_p(\pi)
\le
\sup_{p\in\mathcal U_\rho}\sum_d p_d u_d.
\]
证毕。

## Theorem B: Oracle-Regret Upper Bound via Empirical Bernstein

### Assumptions
1. \(R(x)=J_\pi(x)-\min\{J_f(x),J_s(x)\}\in[0,M]\)。  
2. \(R_1,\dots,R_n\) 为 i.i.d. 样本。  
3. 记经验均值 \(\hat R\)，经验方差 \(\widehat{\mathrm{Var}}(R)\)。

### Statement
对任意 \(\delta\in(0,1)\)，以置信度至少 \(1-\delta\)：
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
这是经验 Bernstein 不等式在有界随机变量 \(R\in[0,M]\) 上的直接应用。  
将一般形式
\[
\mu \le \hat\mu + \sqrt{\frac{2\hat v\ln(3/\delta)}{n}}+\frac{3b\ln(3/\delta)}{n-1}
\]
中的 \(\mu,\hat\mu,\hat v,b\) 分别替换为
\(\mathbb E[R],\hat R,\widehat{\mathrm{Var}}(R),M\)，即得结论。  
证毕。

## Practical Notes
1. 本项目中 \(u_d\) 采用单侧 Wilson 上界计算。  
2. \(\sup_{p\in\mathcal U_\rho}\sum_d p_du_d\) 采用 simplex 网格近似求解并在脚本中复核。  
3. Theorem B 的经验验证只需检查 `regret_mean <= regret_upper` 是否逐 seed 成立。
