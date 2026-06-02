# -*- coding: utf-8 -*-
"""
A1 · 식별가능성 점검 (parameter recovery study)

method.html 식 (6) 그대로:
    P(Y=1) = u_G + (1 - u_G) * sigmoid( a_G * (beta_G + gamma_G * c - theta_pi) )

참값을 알고 모의 응답을 만든 뒤 MAP으로 추정해,
  (1) u를 고정(RSS 라벨 가정)했을 때 theta / b(item) / a / c50 복원
  (2) u를 자유 추정했을 때 u의 식별이 약한지
  (3) AV를 강한 절반 / 약한 절반으로 갈라 따로 보정해도
      b-hat이 일치하는지(표본불변), 반면 충돌률 순위는 흔들리는지
를 확인한다. 출력: research/assets/a1/*.png + 콘솔 지표.
"""
import json
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import pearsonr, spearmanr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(20260602)

# ---------------- 설계 ----------------
# 1차 실행 교훈: 전체 충돌률이 0.78로 치우치면 약한 AV 집단의 칸이
# 천장(전부 충돌)에 붙어 문항 정보가 사라진다. 충돌률이 중간 범위에
# 걸치도록 기본 난이도를 낮추고 표본을 키운다.
N_AV = 30                       # AV (수험생)
N_G = 8                         # 생성기 (출제자)
C = np.array([0., 1., 2., 3., 4.])   # severity 수준
K = 30                          # 칸당 반복 (reactivity: 같은 칸도 매번 다른 전개)

# ---------------- 참값 ----------------
theta_t = rng.normal(0, 1, N_AV)
beta_t  = rng.normal(-1.2, 1.0, N_G)             # 생성기 기본 난이도
gamma_t = rng.lognormal(np.log(0.5), 0.30, N_G)  # severity 기울기 (>0)
a_t     = rng.lognormal(np.log(1.0), 0.40, N_G)  # 변별력 (생성기마다 다름)
u_t     = rng.beta(2.0, 18.0, N_G)               # 회피불가 하한 (평균 ~0.10)

# 칸 인덱스: (AV i, 생성기 g, severity 수준 l)
I, G, L = np.meshgrid(np.arange(N_AV), np.arange(N_G), np.arange(len(C)),
                      indexing="ij")
I, G, L = I.ravel(), G.ravel(), L.ravel()
cc = C[L]

def p_model(theta, beta, gamma, a, u):
    eta = a[G] * (beta[G] + gamma[G] * cc - theta[I])
    return u[G] + (1.0 - u[G]) * expit(eta)

p_true = p_model(theta_t, beta_t, gamma_t, a_t, u_t)
y = rng.binomial(K, p_true)          # 칸별 충돌 횟수 (이항)

print(f"설계: {N_AV} AV x {N_G} G x {len(C)} severity x {K}회 = "
      f"{N_AV*N_G*len(C)*K:,} 응답, 전체 충돌률 {y.sum()/(len(y)*K):.3f}")

# ---------------- MAP 적합 ----------------
def unpack(x, n_av, fix_u=None):
    k = 0
    theta = x[k:k+n_av]; k += n_av
    beta  = x[k:k+N_G];  k += N_G
    gamma = np.exp(x[k:k+N_G]); k += N_G
    a     = np.exp(x[k:k+N_G]); k += N_G
    if fix_u is None:
        u = expit(x[k:k+N_G]); k += N_G
    else:
        u = fix_u
    return theta, beta, gamma, a, u

def neg_logpost(x, y, I_, G_, cc_, K_, n_av, fix_u=None):
    k = 0
    theta = x[k:k+n_av]; k += n_av
    beta  = x[k:k+N_G];  k += N_G
    lg    = x[k:k+N_G];  k += N_G
    la    = x[k:k+N_G];  k += N_G
    gamma, a = np.exp(lg), np.exp(la)
    if fix_u is None:
        zu = x[k:k+N_G]; u = expit(zu); k += N_G
    else:
        u = fix_u
    eta = a[G_] * (beta[G_] + gamma[G_] * cc_ - theta[I_])
    p = u[G_] + (1.0 - u[G_]) * expit(eta)
    p = np.clip(p, 1e-9, 1 - 1e-9)
    ll = np.sum(y * np.log(p) + (K_ - y) * np.log1p(-p))
    # 사전: theta ~ N(0,1) (위치·척도 고정), 나머지는 약한 정규화
    lp = -0.5 * np.sum(theta**2)
    lp += -0.5 * np.sum((beta / 3.0)**2)
    lp += -0.5 * np.sum(((lg - np.log(0.6)) / 1.0)**2)
    lp += -0.5 * np.sum((la / 1.0)**2)
    if fix_u is None:
        lp += -0.5 * np.sum(((zu + 2.0) / 2.0)**2)
    return -(ll + lp)

def fit(y, I_, G_, cc_, K_, n_av, fix_u=None, seed=0):
    r = np.random.default_rng(seed)
    n = n_av + N_G * (3 if fix_u is not None else 4)
    x0 = np.concatenate([
        np.zeros(n_av), np.zeros(N_G),
        np.full(N_G, np.log(0.6)), np.zeros(N_G),
        ([] if fix_u is not None else np.full(N_G, -2.0)),
    ]) + 0.01 * r.normal(size=n)
    res = minimize(neg_logpost, x0,
                   args=(y, I_, G_, cc_, K_, n_av, fix_u),
                   method="L-BFGS-B",
                   options=dict(maxiter=4000, maxfun=200000))
    return unpack(res.x, n_av, fix_u), res

def metrics(est, true):
    r = pearsonr(est, true)[0]
    rmse = float(np.sqrt(np.mean((est - true)**2)))
    return r, rmse

def standardize(theta, beta, gamma, a):
    """척도 고정: 모델은 a(b-theta) 곱만 식별하므로 (a를 1/k배, theta·b를
    k배 해도 우도 동일) 추정 후 theta-hat을 평균 0·표준편차 1로 되돌리고
    b·a를 그에 맞춰 변환한다. c50 = (theta-beta)/gamma 는 이 변환에 불변."""
    m, k = theta.mean(), theta.std()
    return (theta - m) / k, (beta - m) / k, gamma / k, a * k

results = {}

# ---- (1) u 고정 (RSS 라벨로 안 것처럼) ----
(thE, beE, gaE, aE, uE), r1 = fit(y, I, G, cc, K, N_AV, fix_u=u_t)
thE, beE, gaE, aE = standardize(thE, beE, gaE, aE)
b_item_t = beta_t[:, None] + gamma_t[:, None] * C[None, :]   # (G, c)별 난이도
b_item_e = beE[:, None] + gaE[:, None] * C[None, :]
c50_t = (theta_t[:, None] - beta_t[None, :]) / gamma_t[None, :]
c50_e = (thE[:, None] - beE[None, :]) / gaE[None, :]
results["ufix"] = {
    "theta": metrics(thE, theta_t),
    "b_item": metrics(b_item_e.ravel(), b_item_t.ravel()),
    "a": metrics(aE, a_t),
    "c50": metrics(c50_e.ravel(), c50_t.ravel()),
}

# ---- (2) u 자유 추정 ----
(thF, beF, gaF, aF, uF), r2 = fit(y, I, G, cc, K, N_AV, fix_u=None)
thF, beF, gaF, aF = standardize(thF, beF, gaF, aF)
b_item_f = beF[:, None] + gaF[:, None] * C[None, :]
results["ufree"] = {
    "theta": metrics(thF, theta_t),
    "b_item": metrics(b_item_f.ravel(), b_item_t.ravel()),
    "a": metrics(aF, a_t),
    "u": metrics(uF, u_t),
}

# ---- (3) 표본불변: 강한 절반 vs 약한 절반 ----
order = np.argsort(theta_t)
weak_idx, strong_idx = order[:N_AV//2], order[N_AV//2:]

def subgroup_fit(idx):
    mask = np.isin(I, idx)
    remap = {old: new for new, old in enumerate(idx)}
    I_sub = np.array([remap[i] for i in I[mask]])
    (th, be, ga, av, uu), _ = fit(y[mask], I_sub, G[mask], cc[mask], K,
                                  len(idx), fix_u=u_t)
    b_sub = be[:, None] + ga[:, None] * C[None, :]
    # 충돌률(naive)도 같은 부분집단에서 계산
    rate = np.zeros((N_G, len(C)))
    for g in range(N_G):
        for l in range(len(C)):
            m = mask & (G == g) & (L == l)
            rate[g, l] = y[m].sum() / (m.sum() * K)
    return b_sub.ravel(), rate.ravel()

b_weak, rate_weak = subgroup_fit(weak_idx)
b_strong, rate_strong = subgroup_fit(strong_idx)
# 부분집단마다 theta 사전이 집단 안에서 0 중심으로 다시 맞춰지므로
# (시험 동등화처럼) item 평균을 빼서 위치를 맞춘 뒤 비교한다
b_weak_a = b_weak - b_weak.mean()
b_strong_a = b_strong - b_strong.mean()
results["invariance"] = {
    "b_pearson": pearsonr(b_weak_a, b_strong_a)[0],
    "b_spearman": spearmanr(b_weak_a, b_strong_a)[0],
    "b_rmse": float(np.sqrt(np.mean((b_weak_a - b_strong_a)**2))),
    "rate_spearman": spearmanr(rate_weak, rate_strong)[0],
    "rate_mean_weak": float(rate_weak.mean()),
    "rate_mean_strong": float(rate_strong.mean()),
}

print(json.dumps(results, indent=2, ensure_ascii=False, default=float))

# ---------------- 그림 ----------------
plt.rcParams.update({"font.size": 11, "figure.dpi": 140})

def scatter(ax, x_, y_, xlabel, ylabel, title, r, rmse):
    lim = [min(x_.min(), y_.min()), max(x_.max(), y_.max())]
    pad = 0.08 * (lim[1] - lim[0]); lim = [lim[0]-pad, lim[1]+pad]
    ax.plot(lim, lim, color="#bbb", lw=1, zorder=1)
    ax.scatter(x_, y_, s=22, alpha=0.75, color="#2563eb", zorder=2)
    ax.set_xlim(lim); ax.set_ylim(lim)
    ax.set_xlabel(xlabel); ax.set_ylabel(ylabel)
    ax.set_title(f"{title}\nr = {r:.3f},  RMSE = {rmse:.3f}", fontsize=11)

# Fig 1: u 고정 복원 (4패널)
fig, axes = plt.subplots(2, 2, figsize=(9.2, 8.6))
m = results["ufix"]
scatter(axes[0,0], theta_t, thE, "true theta", "estimated theta",
        "AV robustness theta (u fixed)", *m["theta"])
scatter(axes[0,1], b_item_t.ravel(), b_item_e.ravel(),
        "true b(G,c)", "estimated b(G,c)",
        "item difficulty b = beta + gamma*c", *m["b_item"])
scatter(axes[1,0], a_t, aE, "true a", "estimated a",
        "discrimination a_G", *m["a"])
scatter(axes[1,1], c50_t.ravel(), c50_e.ravel(),
        "true c50", "estimated c50",
        "severity midpoint c50(pi,G)", *m["c50"])
fig.tight_layout()
fig.savefig("research/assets/a1/a1_recovery_ufix.png", bbox_inches="tight")

# Fig 2: u 식별성 (자유 추정)
fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.4))
mf = results["ufree"]
scatter(axes[0], u_t, uF, "true u", "estimated u",
        "floor u, freely estimated", *mf["u"])
scatter(axes[1], theta_t, thF, "true theta", "estimated theta",
        "theta when u is free", *mf["theta"])
fig.tight_layout()
fig.savefig("research/assets/a1/a1_u_identifiability.png", bbox_inches="tight")

# Fig 3: 표본불변 (충돌률 vs b-hat)
fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.4))
inv = results["invariance"]
ax = axes[0]
lim = [0, 1]
ax.plot(lim, lim, color="#bbb", lw=1)
ax.scatter(rate_weak, rate_strong, s=22, alpha=0.75, color="#dc2626")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("collision rate (weak half)")
ax.set_ylabel("collision rate (strong half)")
ax.set_title(f"naive collision rate per item\nSpearman rho = "
             f"{inv['rate_spearman']:.3f}", fontsize=11)
ax = axes[1]
both = np.concatenate([b_weak_a, b_strong_a])
lim = [both.min()-0.3, both.max()+0.3]
ax.plot(lim, lim, color="#bbb", lw=1)
ax.scatter(b_weak_a, b_strong_a, s=22, alpha=0.75, color="#2563eb")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("b-hat (weak half, mean-anchored)")
ax.set_ylabel("b-hat (strong half, mean-anchored)")
ax.set_title(f"IRT item difficulty b-hat\nPearson r = {inv['b_pearson']:.3f}, "
             f"Spearman rho = {inv['b_spearman']:.3f}", fontsize=11)
fig.tight_layout()
fig.savefig("research/assets/a1/a1_invariance.png", bbox_inches="tight")

with open("analysis/a1-identifiability/a1_results.json", "w",
          encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False, default=float)
print("그림 3장 저장: research/assets/a1/")
