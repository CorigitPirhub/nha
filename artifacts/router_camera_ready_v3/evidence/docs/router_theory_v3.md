# Router Theory V3：多臂 Portfolio + 两阶段 Probe + 先验偏移下的可验证证书

状态：`draft-for-step9`  
版本：`v3.0`  
日期：`2026-03-03`

本版本把 V2 的“分层先验偏移风险证书 + regret 上界”扩展到：
1) **多臂（K≥3）portfolio 路由**（Phase23），  
2) **两阶段（Static conformal → Probe flip）** 的安全组合（Phase9/Phase21），  
3) **仅先验偏移（prior shift）** 场景下的可验证风险上界（difficulty / OOD family 分组）。

> 重要：V3 的目标不是追求“最强理论假设”，而是把 **论文中可写的 guarantee** 做到
> “脚本可复现逐条验证”，并清楚标注在什么条件下可能失效（见 Limitations）。

---

## 1. 设置与符号

多臂集合 \(\mathcal A=\{\texttt{fast},\texttt{mid},\texttt{slow}\}\)（可推广到 \(K>3\)）。以 \(\texttt{slow}\) 为 reference，定义：

- 相对质量损失
  \[
  \Delta L_{\mathrm{rel}}^{(a)}(x)=\frac{L_a(x)-L_{\texttt{slow}}(x)}{\max(L_{\texttt{slow}}(x),10^{-6})}.
  \]
- 风险事件（冻结 protocol：\(\epsilon_{\mathrm{rel}}=0.015\)）：
  \[
  Z_\pi(x)=\mathbf 1\{\pi(x)\neq \texttt{slow}\ \land\ \Delta L_{\mathrm{rel}}^{(\pi(x))}(x)>\epsilon_{\mathrm{rel}}\}.
  \]
  风险 \(V(\pi)=\mathbb E[Z_\pi]\)，目标上界 \(\alpha=0.05\)。
- 联合代价（冻结口径）：
  \[
  J_\pi(x)=T_{\pi(x)}(x)/T_{\mathrm{ref}}+\beta\cdot \max(\Delta L_{\mathrm{rel}}^{(\pi(x))}(x),0).
  \]

---

## 2. V3 级别结论（摘要版）

完整证明见 `docs/router_theory_v3_appendix.md`，脚本验证见 Phase24。

### Theorem 1：K 臂 Oracle-regret 的有限样本上界（可验证）
对任意固定策略 \(\pi\)，定义单样本 regret：
\[
R(x)=J_\pi(x)-\min_{a\in\mathcal A}J_a(x)\in[0,M].
\]
则在 i.i.d.（或可交换）样本上，可用经验 Bernstein 型不等式给出
\(\mathbb E[R]\) 的高置信上界，并在脚本中输出 **bound slack**（上界与经验均值的差距）。

### Theorem 2：分组 prior-shift 下的多臂风险鲁棒证书（可验证）
对任意分组 \(g(x)\in\mathcal G\)（difficulty、OOD family 等），若部署仅发生 **先验偏移**
（组内条件分布不变），则用校准集上每组风险上界 \(u_g\) 可得到：
\[
V_{p}(\pi)\le \sum_{g\in\mathcal G} p_g\,u_g,
\]
并可对 \(p\) 的不确定集（例如 \(\ell_1\) 球）给出鲁棒上界。脚本在 **每个 seed、每个 OOD family** 上逐条验证
“empirical ≤ bound”。

### Theorem 3：两阶段（Probe 只升级到更慢臂）的风险单调性
若第二阶段只允许 \(\texttt{fast}\to\texttt{mid/slow}\)、\(\texttt{mid}\to\texttt{slow}\) 的升级，
则风险不会增加：\(V(\pi_{\mathrm{probe}})\le V(\pi_{\mathrm{static}})\)。脚本在 Phase9 的
`conformal_strict_v2` vs `probe_strict_v2` 上验证。

---

## 3. 可验证协议（Phase24）

运行：`scripts/run_router_phase24_theory_v3.py`

验证对象：
1) **Phase23（Portfolio Router）**：读取 `outputs/router_phase23_portfolio_v1/seeds/seed_*/{calib,test}_decisions.parquet`  
2) **Phase9（Probe 单调性）**：读取 `outputs/router_phase9_bench_v1/router_eval_relaxed2_allseed/.../conformal_strict_v2` 与 `probe_strict_v2`。

输出：
- `outputs/router_phase24_theory_v3/stats.json`
- `outputs/router_phase24_theory_v3/seed_checks.csv`
- `outputs/router_phase24_theory_v3/shift_bounds.csv`
- `outputs/router_phase24_theory_v3/probe_monotone.csv`
- `reports/router_phase24_theory_v3.md`

---

## 4. Limitations（必须写在论文里）
1. **Theorem 2 的 prior-shift 假设**：若组内条件分布也发生变化（covariate/label shift），则上界可能失效；脚本会在报告中列出最接近失败的组与 slack。  
2. **Regret 上界的 M 依赖**：当 \(J\) 的尾部很重或上界 M 取值过保守时，上界可能变松；我们用 Phase24 的 `bound_gap_reasonable` 量化这一点。  
3. **两阶段单调性不保证 J 单调**：升级到更慢臂可能增加时延，导致 \(J\) 增大；因此 V3 只对风险给出单调保证。

