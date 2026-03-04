# Router Theory V2：风险-时延联合路由的可证明上界（Step 1）

状态：`draft-for-step1`  
版本：`v2.0`  
日期：`2026-03-02`

## 1. 统一优化问题
定义单样本状态 \(x\) 上的两种代价：
1. 质量风险事件：\(Z_\pi(x)=\mathbf{1}\{\pi(x)=\texttt{fast}\land \Delta L_{\text{rel}}(x)>\epsilon\}\)  
2. 时延-质量联合代价：\(J_\pi(x)=T_\pi(x)+\beta L_\pi(x)\)

目标是学习路由策略 \(\pi\)：
\[
\min_{\pi}\ \mathbb{E}[J_\pi]
\quad
\text{s.t.}
\quad
V(\pi):=\mathbb{E}[Z_\pi]\le \alpha.
\]

其中 \(\epsilon=1.5\%\)，\(\alpha=0.05\)。

## 2. 核心定理（新增）

### Theorem A：分层先验偏移下的风险鲁棒上界
设难度分层 \(d\in\{\texttt{easy,medium,hard}\}\)，每层真实风险为 \(v_d\)。对每层以有限样本估计得到单侧置信上界 \(u_d\)（本文采用 Wilson 上界）。  
则对任意目标先验 \(p\in\Delta^3\)：
\[
V_p(\pi)=\sum_d p_d v_d \le \sum_d p_d u_d.
\]

进一步，若部署先验仅知位于不确定集
\[
\mathcal U_\rho=\{p\in\Delta^3:\|p-p_0\|_1\le \rho\},
\]
则有鲁棒证书：
\[
\sup_{p\in\mathcal U_\rho}V_p(\pi)\le \sup_{p\in\mathcal U_\rho}\sum_d p_d u_d.
\]

### Theorem B：相对 Oracle 的联合代价遗憾上界
定义单样本遗憾：
\[
R(x)=J_\pi(x)-\min\{J_{\texttt{fast}}(x),J_{\texttt{slow}}(x)\}\in[0,M].
\]
在 \(n\) 个 i.i.d. 样本上，记经验均值 \(\hat R\)、经验方差 \(\widehat{\mathrm{Var}}(R)\)。  
则以置信度 \(1-\delta\) 有：
\[
\mathbb E[R]
\le
\hat R
+
\sqrt{\frac{2\widehat{\mathrm{Var}}(R)\ln(3/\delta)}{n}}
+
\frac{3M\ln(3/\delta)}{n-1}.
\]

该式给出路由策略相对最优开关策略的可验证上界。

## 3. 验证协议（与 Step 1 对齐）
1. 使用 `router_phase9_bench_v1/router_eval_relaxed2_allseed` 的 5 seeds。  
2. 每个 seed 在 OOD map families（按 `map_id`）上验证 `empirical <= theory_upper`。  
3. 在 \(\mathcal U_\rho\) 上执行先验扰动网格验证 `shift_robust_bound_hold`。  
4. 输出 pooled 风险上界 gap，验收阈值 `<=1%`。

## 4. 产物
1. 运行脚本：`scripts/run_router_theory_v2.py`  
2. 输出目录：`outputs/router_theory_v2/`  
3. 报告：`reports/router_theory_v2.md`  
4. 完整证明：`docs/router_theory_v2_appendix.md`
