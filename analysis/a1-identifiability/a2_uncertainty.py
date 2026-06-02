# -*- coding: utf-8 -*-
"""
A2 · 추정 절차 확정 (불확실성 정량화 + coverage 검증)

A1과 같은 모델(식 6, u는 외부 라벨로 고정)에서:
  (1) Laplace 근사: MAP 주변의 2차 근사로 사후 공분산을 얻고 95% 구간 생성
  (2) 중요도 표본(IS) 검증: Laplace 표본에 사후/근사 가중치를 줘
      유효표본수(ESS)로 근사의 질을 진단, IS-보정 구간과 비교
  (3) coverage 반복 실험: 참값·데이터를 새로 뽑아 R회 반복,
      95% 구간이 참값을 실제로 95% 덮는지 (θ*, b*, a*, c50)
척도 자유 처리: 추정량과 참값 모두 각자의 θ 모멘트로 표준화한 양(*)을 비교.
출력: research/assets/a1/a2_*.png + analysis/a1-identifiability/a2_results.json
"""
import json
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------- 설계 (A1 최종안과 동일) ----------------
N_AV, N_G = 30, 8
C = np.array([0., 1., 2., 3., 4.])
K = 30

I, G, L = np.meshgrid(np.arange(N_AV), np.arange(N_G), np.arange(len(C)),
                      indexing="ij")
I, G, L = I.ravel(), G.ravel(), L.ravel()
cc = C[L]
NP = N_AV + 3 * N_G          # theta, beta, log gamma, log a  (u 고정)

def draw_truth(rng):
    return dict(
        theta=rng.normal(0, 1, N_AV),
        beta=rng.normal(-1.2, 1.0, N_G),
        gamma=rng.lognormal(np.log(0.5), 0.30, N_G),
        a=rng.lognormal(np.log(1.0), 0.40, N_G),
        u=rng.beta(2.0, 18.0, N_G),
    )

def simulate(t, rng):
    eta = t["a"][G] * (t["beta"][G] + t["gamma"][G] * cc - t["theta"][I])
    p = t["u"][G] + (1 - t["u"][G]) * expit(eta)
    return rng.binomial(K, p)

def neg_logpost(x, y, u_fix):
    th = x[:N_AV]
    be = x[N_AV:N_AV+N_G]
    lg = x[N_AV+N_G:N_AV+2*N_G]
    la = x[N_AV+2*N_G:]
    ga, a = np.exp(lg), np.exp(la)
    eta = a[G] * (be[G] + ga[G] * cc - th[I])
    p = u_fix[G] + (1 - u_fix[G]) * expit(eta)
    p = np.clip(p, 1e-9, 1 - 1e-9)
    ll = np.sum(y * np.log(p) + (K - y) * np.log1p(-p))
    lp = -0.5*np.sum(th**2) - 0.5*np.sum((be/3.)**2) \
         - 0.5*np.sum(((lg-np.log(0.6))/1.)**2) - 0.5*np.sum((la/1.)**2)
    return -(ll + lp)

def fit_map(y, u_fix, seed=0):
    r = np.random.default_rng(seed)
    x0 = np.concatenate([np.zeros(N_AV), np.zeros(N_G),
                         np.full(N_G, np.log(0.6)), np.zeros(N_G)])
    x0 = x0 + 0.01 * r.normal(size=NP)
    res = minimize(neg_logpost, x0, args=(y, u_fix), method="L-BFGS-B",
                   options=dict(maxiter=4000, maxfun=200000))
    return res.x

def hessian(f, x, h=5e-4):
    """중심차분 Hessian (f: 스칼라 함수)."""
    n = len(x); H = np.zeros((n, n))
    hi = h * np.maximum(1.0, np.abs(x))
    f0 = f(x)
    # 대각
    for i in range(n):
        e = np.zeros(n); e[i] = hi[i]
        H[i, i] = (f(x+e) - 2*f0 + f(x-e)) / hi[i]**2
    # 비대각
    for i in range(n):
        for j in range(i+1, n):
            ei = np.zeros(n); ei[i] = hi[i]
            ej = np.zeros(n); ej[j] = hi[j]
            H[i, j] = H[j, i] = (f(x+ei+ej) - f(x+ei-ej)
                                 - f(x-ei+ej) + f(x-ei-ej)) / (4*hi[i]*hi[j])
    return H

def laplace_cov(xmap, y, u_fix):
    f = lambda x: neg_logpost(x, y, u_fix)
    H = hessian(f, xmap)
    H = 0.5 * (H + H.T)
    w, V = np.linalg.eigh(H)
    w = np.maximum(w, 1e-6)
    return (V / w) @ V.T

def laplace_draws(xmap, cov, S, rng):
    Lc = np.linalg.cholesky(cov + 1e-10*np.eye(NP))
    return xmap[None, :] + rng.normal(size=(S, NP)) @ Lc.T

def rwm_chains(xmap, cov, y, u_fix, n_chain=4, n_iter=200000, burn=40000,
               thin=20, seed=0):
    """전처리 랜덤워크 Metropolis: 제안 N(0, s^2 * Sigma_Laplace).
    번인 동안 Robbins-Monro로 수용률 0.234에 맞춰 s를 적응시킨다."""
    Lc = np.linalg.cholesky(cov + 1e-10*np.eye(NP))
    logpost = lambda z: -neg_logpost(z, y, u_fix)
    chains, accs = [], []
    for ch in range(n_chain):
        rng = np.random.default_rng(seed + 100 + ch)
        x = xmap + 0.3 * (Lc @ rng.normal(size=NP))
        lp = logpost(x)
        s = 2.38 / np.sqrt(NP)
        keep = []
        acc = 0
        for it in range(n_iter):
            prop = x + s * (Lc @ rng.normal(size=NP))
            lpp = logpost(prop)
            if np.log(rng.random()) < lpp - lp:
                x, lp = prop, lpp
                a = 1
            else:
                a = 0
            if it < burn:                      # 적응
                s = s * np.exp(0.5 * (a - 0.234) / np.sqrt(1 + it/50))
            else:
                acc += a
                if (it - burn) % thin == 0:
                    keep.append(x.copy())
        chains.append(np.array(keep))
        accs.append(acc / (n_iter - burn))
    return chains, accs

def split_rhat(chains):
    """split-R-hat (스칼라별), 최댓값 반환. chains: 체인별 (n, q) 배열 목록."""
    segs = []
    for c in chains:
        h = len(c) // 2
        segs += [c[:h], c[h:2*h]]
    segs = np.array(segs)                      # (m, n, q)
    n = segs.shape[1]
    mean_j = segs.mean(axis=1)                 # (m, q)
    B = n * mean_j.var(axis=0, ddof=1)
    W = segs.var(axis=1, ddof=1).mean(axis=0)
    var_hat = (n - 1) / n * W + B / n
    return float(np.sqrt(var_hat / np.maximum(W, 1e-12)).max())

def transform_draws(X):
    """비제약 표본 → 표준화된 양 (θ*, b*(G,c), a*, c50)."""
    th = X[:, :N_AV]
    be = X[:, N_AV:N_AV+N_G]
    ga = np.exp(X[:, N_AV+N_G:N_AV+2*N_G])
    a  = np.exp(X[:, N_AV+2*N_G:])
    m = th.mean(axis=1, keepdims=True)
    k = th.std(axis=1, keepdims=True)
    th_s = (th - m) / k
    b_item = be[:, :, None] + ga[:, :, None] * C[None, None, :]   # (S,G,c)
    b_s = (b_item - m[:, :, None]) / k[:, :, None]
    a_s = a * k
    c50 = (th[:, :, None] - be[:, None, :]) / ga[:, None, :]      # (S,AV,G)
    return th_s, b_s.reshape(len(X), -1), a_s, c50.reshape(len(X), -1)

def true_quantities(t):
    m, k = t["theta"].mean(), t["theta"].std()
    th_s = (t["theta"] - m) / k
    b_item = t["beta"][:, None] + t["gamma"][:, None] * C[None, :]
    b_s = ((b_item - m) / k).ravel()
    a_s = t["a"] * k
    c50 = ((t["theta"][:, None] - t["beta"][None, :])
           / t["gamma"][None, :]).ravel()
    return th_s, b_s, a_s, c50

def wq(x, w, qs):
    """가중 분위수."""
    o = np.argsort(x); xs, ws = x[o], w[o]
    cw = np.cumsum(ws)
    return np.interp(qs, cw, xs)

# ============ (1)(2) 단일 데이터: Laplace vs MCMC 대조 ============
rng = np.random.default_rng(20260602)
t0 = draw_truth(rng)
y0 = simulate(t0, rng)
xmap = fit_map(y0, t0["u"])
cov0 = laplace_cov(xmap, y0, t0["u"])
XL = laplace_draws(xmap, cov0, S=20000, rng=rng)

# 참고: 결합밀도 중요도표본(IS)은 54차원에서 ESS~10/20000으로 붕괴
# (차원의 저주). 그래서 검증은 전처리 RWM MCMC로 한다.
chains, accs = rwm_chains(xmap, cov0, y0, t0["u"])
rhat_raw = split_rhat(chains)
# 보고 대상인 표준화 양(theta*, b*, a*, c50)에 대한 R-hat:
# 척도 자유 방향(a <-> theta·b 맞교환)은 사전으로만 약하게 고정되어
# 원시 모수에서는 느리게 움직이지만, 표준화 양은 그 방향에 불변이다.
tchains = []
for c in chains:
    td = transform_draws(c)
    tchains.append(np.hstack(td))
rhat_std = split_rhat(tchains)
XM = np.vstack(chains)
print(f"MCMC: 4체인 x 160k(thin 20) = {len(XM):,} 표본, "
      f"수용률 {np.mean(accs):.3f}, "
      f"split-Rhat 원시 {rhat_raw:.3f} / 표준화 양 {rhat_std:.4f}")

names = ["theta*", "b*", "a*", "c50"]
tru = true_quantities(t0)
dL = transform_draws(XL)
dM = transform_draws(XM)
single = {"rhat_raw": rhat_raw, "rhat_std": rhat_std,
          "acc": float(np.mean(accs))}
for nm, dl, dm, tv in zip(names, dL, dM, tru):
    loL, hiL = np.percentile(dl, [2.5, 97.5], axis=0)
    loM, hiM = np.percentile(dm, [2.5, 97.5], axis=0)
    single[nm] = dict(
        cover_L=float(np.mean((tv >= loL) & (tv <= hiL))),
        cover_M=float(np.mean((tv >= loM) & (tv <= hiM))),
        width_ratio_LM=float(np.mean((hiL - loL) / (hiM - loM))),
        endpoint_r=float(np.corrcoef(np.r_[loL, hiL], np.r_[loM, hiM])[0, 1]),
    )
print(json.dumps(single, indent=2))

# 그림 1: theta caterpillar (Laplace 구간 vs 참값) + Laplace/MCMC 폭 비교
fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.6),
                         gridspec_kw=dict(width_ratios=[1.5, 1]))
ax = axes[0]
th_sL = dL[0]
order = np.argsort(tru[0])
lo = np.percentile(th_sL, 2.5, axis=0)[order]
hi = np.percentile(th_sL, 97.5, axis=0)[order]
md = np.percentile(th_sL, 50, axis=0)[order]
tv = tru[0][order]
xs = np.arange(N_AV)
inside = (tv >= lo) & (tv <= hi)
ax.vlines(xs, lo, hi, color="#94a3b8", lw=3, alpha=.9, label="95% interval")
ax.scatter(xs, md, s=14, color="#475569", zorder=3, label="posterior median")
ax.scatter(xs, tv, s=26, color=np.where(inside, "#2563eb", "#dc2626"),
           zorder=4, marker="D", label="true value")
ax.set_xlabel("AV (sorted by true theta*)")
ax.set_ylabel("theta* (standardized)")
ax.set_title(f"theta*: 95% intervals vs truth "
             f"({inside.sum()}/{N_AV} covered)", fontsize=11)
ax.legend(fontsize=8, loc="upper left")
ax = axes[1]
wL_all, wM_all, cols = [], [], []
palette = {"theta*": "#2563eb", "b*": "#16a34a", "c50": "#9333ea"}
for nm, dl, dm in zip(names, dL, dM):
    if nm == "a*":
        continue
    loL, hiL = np.percentile(dl, [2.5, 97.5], axis=0)
    loM, hiM = np.percentile(dm, [2.5, 97.5], axis=0)
    wL_all.append(hiL - loL); wM_all.append(hiM - loM)
    cols += [palette[nm]] * dl.shape[1]
wL_all = np.concatenate(wL_all); wM_all = np.concatenate(wM_all)
lim = [0, max(wL_all.max(), wM_all.max()) * 1.06]
ax.plot(lim, lim, color="#bbb", lw=1)
ax.scatter(wM_all, wL_all, s=14, c=cols, alpha=.6)
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("MCMC interval width")
ax.set_ylabel("Laplace interval width")
ax.set_title(f"Laplace vs MCMC (split-Rhat: std qty {rhat_std:.3f})\n"
             "blue theta*, green b*, purple c50", fontsize=10.5)
fig.tight_layout()
fig.savefig("research/assets/a1/a2_single.png", bbox_inches="tight")

# ================= (3) coverage 반복 실험 =================
R = 40
S = 4000
cov_counts = {nm: [0, 0] for nm in names}
zscores = {nm: [] for nm in names}
for rep in range(R):
    rr = np.random.default_rng(1000 + rep)
    t = draw_truth(rr)
    yy = simulate(t, rr)
    xm = fit_map(yy, t["u"], seed=rep)
    cv = laplace_cov(xm, yy, t["u"])
    Xr = laplace_draws(xm, cv, S=S, rng=rr)
    drs = transform_draws(Xr)
    trs = true_quantities(t)
    for nm, draws, tv in zip(names, drs, trs):
        lo = np.percentile(draws, 2.5, axis=0)
        hi = np.percentile(draws, 97.5, axis=0)
        cov_counts[nm][0] += int(np.sum((tv >= lo) & (tv <= hi)))
        cov_counts[nm][1] += len(tv)
        mu = draws.mean(axis=0)
        sd = draws.std(axis=0)
        zscores[nm].append((mu - tv) / sd)

coverage = {nm: c[0]/c[1] for nm, c in cov_counts.items()}
z_pool = {nm: np.concatenate(v) for nm, v in zscores.items()}
z_stats = {nm: dict(mean=float(z.mean()), sd=float(z.std()))
           for nm, z in z_pool.items()}
results = dict(single=single, coverage=coverage, z_stats=z_stats, R=R)
print(json.dumps(dict(coverage=coverage, z_stats=z_stats), indent=2))

# 그림 2: coverage 막대 + z-점수 보정 진단
fig, axes = plt.subplots(1, 2, figsize=(10.6, 4.3))
ax = axes[0]
vals = [coverage[nm] for nm in names]
ax.bar(names, vals, color="#2563eb", width=0.55, alpha=.85)
ax.axhline(0.95, color="#dc2626", lw=1.5, ls="--", label="nominal 95%")
for i, v in enumerate(vals):
    ax.text(i, v + 0.012, f"{v:.3f}", ha="center", fontsize=10)
ax.set_ylim(0.80, 1.02)
ax.set_ylabel("empirical coverage of 95% intervals")
ax.set_title(f"coverage over {R} replications (Laplace, u fixed)",
             fontsize=11)
ax.legend(fontsize=9)
ax = axes[1]
zz = np.concatenate([z_pool[nm] for nm in names])
xs = np.linspace(-4, 4, 200)
ax.hist(zz, bins=60, range=(-4, 4), density=True,
        color="#94a3b8", alpha=.8, label="pooled z-scores")
ax.plot(xs, np.exp(-xs**2/2)/np.sqrt(2*np.pi), color="#dc2626", lw=1.6,
        label="N(0,1)")
ax.set_xlabel("(posterior mean - true) / posterior sd")
ax.set_title(f"calibration: pooled z (mean {zz.mean():.2f}, "
             f"sd {zz.std():.2f})", fontsize=11)
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig("research/assets/a1/a2_coverage.png", bbox_inches="tight")

with open("analysis/a1-identifiability/a2_results.json", "w",
          encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("저장: research/assets/a1/a2_single.png, a2_coverage.png")
