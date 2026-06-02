# -*- coding: utf-8 -*-
"""
A4 · 회피가능성 라벨러 (오라벨 민감도)

하한 u는 외부 라벨(RSS·LFR·over-critical)로 주기로 했다(A1·A2).
실제 라벨은 완벽하지 않으므로:
  (1) 라벨 잡음 tau (u_lab = clip(u + N(0,tau)))의 용량-반응
  (2) 체계적 치우침 delta (u_lab = u·(1+delta); -1이면 u=0 무시)의 용량-반응
  (3) 현실적 잡음(tau=0.05)에서 전략 비교:
      하드 고정 / u=0 무시 / 자유 추정 / soft 사전(라벨을 사전 중심으로)
손상 지표: 표준화 강건성 theta*·난이도 b*의 RMSE (반복 평균 ± 표준오차).
출력: research/assets/a1/a4_*.png + a4_results.json
"""
import json
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit, logit
from scipy.stats import pearsonr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ---------------- 설계 (A1 최종안) ----------------
N_AV, N_G = 30, 8
C = np.array([0., 1., 2., 3., 4.])
K = 30
I, G, L = np.meshgrid(np.arange(N_AV), np.arange(N_G), np.arange(len(C)),
                      indexing="ij")
I, G, L = I.ravel(), G.ravel(), L.ravel()
cc = C[L]

def draw_truth(rng):
    return dict(theta=rng.normal(0, 1, N_AV),
                beta=rng.normal(-1.2, 1.0, N_G),
                gamma=rng.lognormal(np.log(0.5), 0.30, N_G),
                a=rng.lognormal(np.log(1.0), 0.40, N_G),
                u=rng.beta(2.0, 18.0, N_G))

def simulate(t, rng):
    eta = t["a"][G] * (t["beta"][G] + t["gamma"][G]*cc - t["theta"][I])
    p = t["u"][G] + (1 - t["u"][G]) * expit(eta)
    return rng.binomial(K, p)

# ---------------- 적합 (u 처리 4방식) ----------------
def neg_logpost(x, y, mode, u_arg):
    k = 0
    th = x[k:k+N_AV]; k += N_AV
    be = x[k:k+N_G]; k += N_G
    lg = x[k:k+N_G]; k += N_G
    la = x[k:k+N_G]; k += N_G
    ga, a = np.exp(lg), np.exp(la)
    if mode in ("free", "soft"):
        zu = x[k:k+N_G]; u = expit(zu); k += N_G
    elif mode == "fix":
        u = u_arg
    else:                                  # zero
        u = np.zeros(N_G)
    eta = a[G] * (be[G] + ga[G]*cc - th[I])
    p = u[G] + (1 - u[G]) * expit(eta)
    p = np.clip(p, 1e-9, 1 - 1e-9)
    ll = np.sum(y*np.log(p) + (K-y)*np.log1p(-p))
    lp = -0.5*np.sum(th**2) - 0.5*np.sum((be/3.)**2) \
         - 0.5*np.sum(((lg-np.log(0.6))/1.)**2) - 0.5*np.sum((la/1.)**2)
    if mode == "free":
        lp += -0.5*np.sum(((zu + 2.0)/2.0)**2)
    elif mode == "soft":                   # 라벨을 사전 중심으로 (logit 공간)
        z0 = logit(np.clip(u_arg, 1e-3, 0.97))
        lp += -0.5*np.sum(((zu - z0)/0.75)**2)
    return -(ll + lp)

def fit(y, mode, u_arg=None, seed=0):
    r = np.random.default_rng(seed)
    extra = N_G if mode in ("free", "soft") else 0
    n = N_AV + 3*N_G + extra
    x0 = np.concatenate([np.zeros(N_AV), np.zeros(N_G),
                         np.full(N_G, np.log(0.6)), np.zeros(N_G),
                         np.full(extra, -2.0)])
    x0 = x0 + 0.01*r.normal(size=n)
    res = minimize(neg_logpost, x0, args=(y, mode, u_arg), method="L-BFGS-B",
                   options=dict(maxiter=4000, maxfun=200000))
    x = res.x
    th = x[:N_AV]; be = x[N_AV:N_AV+N_G]
    ga = np.exp(x[N_AV+N_G:N_AV+2*N_G]); a = np.exp(x[N_AV+2*N_G:N_AV+3*N_G])
    m, kk = th.mean(), th.std()
    return (th-m)/kk, (be-m)/kk, ga/kk, a*kk

def damage(t, th_e, be_e, ga_e):
    """표준화 참값 대비 RMSE (theta*, b*)."""
    m, kk = t["theta"].mean(), t["theta"].std()
    th_s = (t["theta"]-m)/kk
    b_t = ((t["beta"][:, None] + t["gamma"][:, None]*C[None, :]) - m)/kk
    b_e = be_e[:, None] + ga_e[:, None]*C[None, :]
    return (float(np.sqrt(np.mean((th_e-th_s)**2))),
            float(np.sqrt(np.mean((b_e-b_t.reshape(N_G, -1))**2))))

R = 10                                     # 조건당 반복
# 짝지은 비교: 모든 조건이 같은 참값·데이터(rep 기준)를 마주하고,
# 라벨 잡음만 조건별 별도 난수로 준다. 조건 간 차이 = 순수 전략·라벨 효과.
TRUTHS, DATAS = [], []
for rep in range(R):
    rng = np.random.default_rng(7000 + rep)
    t = draw_truth(rng)
    TRUTHS.append(t)
    DATAS.append(simulate(t, rng))

def run_condition(label_fn, mode, tag_seed):
    """label_fn(t, rng) -> u_lab. 같은 R개 데이터에 적합해 평균·표준오차."""
    dth, dbb = [], []
    for rep in range(R):
        t, y = TRUTHS[rep], DATAS[rep]
        lrng = np.random.default_rng(9000 + tag_seed*100 + rep)
        u_lab = None if label_fn is None else label_fn(t, lrng)
        th_e, be_e, ga_e, _ = fit(y, mode, u_lab, seed=rep)
        d1, d2 = damage(t, th_e, be_e, ga_e)
        dth.append(d1); dbb.append(d2)
    dth, dbb = np.array(dth), np.array(dbb)
    return (dth.mean(), dth.std()/np.sqrt(R),
            dbb.mean(), dbb.std()/np.sqrt(R))

results = {}

# ---- (1) 라벨 잡음 용량-반응 ----
taus = [0.0, 0.025, 0.05, 0.10, 0.15]
noise_curve = []
for ti, tau in enumerate(taus):
    f = (lambda tau: lambda t, rng:
         np.clip(t["u"] + rng.normal(0, tau, N_G), 0.0, 0.45))(tau)
    noise_curve.append(run_condition(f, "fix", 10+ti))
    print(f"잡음 tau={tau}: theta* RMSE {noise_curve[-1][0]:.3f}")
results["noise"] = dict(taus=taus, curve=noise_curve)

# ---- (2) 체계적 치우침 용량-반응 ----
deltas = [-1.0, -0.5, 0.0, 0.5, 1.0]      # -1 = u 무시(0), +1 = 2배 과대
bias_curve = []
for di, d in enumerate(deltas):
    f = (lambda d: lambda t, rng:
         np.clip(t["u"]*(1.0+d), 0.0, 0.45))(d)
    bias_curve.append(run_condition(f, "fix", 30+di))
    print(f"치우침 delta={d:+.1f}: theta* RMSE {bias_curve[-1][0]:.3f}")
results["bias"] = dict(deltas=deltas, curve=bias_curve)

# ---- (3) 전략 비교 (현실적 잡음 tau=0.05) ----
noisy = lambda t, rng: np.clip(t["u"] + rng.normal(0, 0.05, N_G), 0.0, 0.45)
strategies = [
    ("fix label\n(hard)",  "fix",  noisy),
    ("ignore\n(u=0)",      "zero", None),
    ("free\n(data only)",  "free", None),
    ("soft prior\n(label)", "soft", noisy),
]
strat = []
for si, (nm, mode, f) in enumerate(strategies):
    strat.append((nm,) + run_condition(f, mode, 50+si))
    print(f"전략 {nm.replace(chr(10),' ')}: theta* RMSE {strat[-1][1]:.3f}")
results["strategies"] = [(s[0].replace("\n", " "),) + s[1:] for s in strat]

with open("analysis/a1-identifiability/a4_results.json", "w",
          encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

# ---------------- 그림 ----------------
plt.rcParams.update({"font.size": 11, "figure.dpi": 140})
fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.2))

ax = axes[0]
m1 = [c[0] for c in noise_curve]; s1 = [c[1] for c in noise_curve]
m2 = [c[2] for c in noise_curve]; s2 = [c[3] for c in noise_curve]
ax.errorbar(taus, m1, yerr=s1, marker="o", color="#2563eb", label="theta* RMSE")
ax.errorbar(taus, m2, yerr=s2, marker="s", color="#16a34a", label="b* RMSE")
ax.set_xlabel("label noise sd (tau, on u scale)")
ax.set_ylabel("RMSE vs truth")
ax.set_title("random label noise", fontsize=11)
ax.legend(fontsize=9)

ax = axes[1]
m1 = [c[0] for c in bias_curve]; s1 = [c[1] for c in bias_curve]
m2 = [c[2] for c in bias_curve]; s2 = [c[3] for c in bias_curve]
ax.errorbar(deltas, m1, yerr=s1, marker="o", color="#2563eb", label="theta* RMSE")
ax.errorbar(deltas, m2, yerr=s2, marker="s", color="#16a34a", label="b* RMSE")
ax.axvline(0, color="#999", lw=.8)
ax.set_xticks(deltas)
ax.set_xticklabels(["-100%\n(ignore)", "-50%", "0", "+50%", "+100%"])
ax.set_xlabel("systematic label bias (relative)")
ax.set_title("under- / over-labeling", fontsize=11)
ax.legend(fontsize=9)

ax = axes[2]
names = [s[0] for s in strat]
v1 = [s[1] for s in strat]; e1 = [s[2] for s in strat]
v2 = [s[3] for s in strat]; e2 = [s[4] for s in strat]
xs = np.arange(len(names)); wd = 0.36
ax.bar(xs - wd/2, v1, wd, yerr=e1, color="#2563eb", label="theta* RMSE",
       capsize=3)
ax.bar(xs + wd/2, v2, wd, yerr=e2, color="#16a34a", label="b* RMSE",
       capsize=3)
ax.set_xticks(xs); ax.set_xticklabels(names, fontsize=8.5)
ax.set_title("strategies under realistic noise (tau=0.05)", fontsize=11)
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig("research/assets/a1/a4_labeler.png", bbox_inches="tight")
print("저장: research/assets/a1/a4_labeler.png")
