# -*- coding: utf-8 -*-
"""
A3 · 난이도 공변량 확정 (설명적 IRT 모의 검증)

난이도를 생성기 특징의 함수로 둔다 (De Boeck explanatory IRT):
    beta_G = w · x_G + e_G,   e_G ~ N(0, sigma_e^2)
x_G: 생성기 특징 (실전에서는 Wagner TTR, Yu 복잡도, Tulpule 가치함수 등).

확인할 것:
  (1) 특징 가중치 w와 베이스 난이도 beta가 응답에서 복원되는가
  (2) 응답이 전혀 없는 새 생성기의 난이도를 특징만으로 예측할 수 있는가
      (out-of-sample; 잔차 sigma_e가 예측 정확도의 상한)
  (3) 잔차를 빼면(LLTM: beta = w·x 정확) 무엇이 깨지는가
출력: research/assets/a1/a3_*.png + a3_results.json
"""
import json
import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import pearsonr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rng = np.random.default_rng(20260603)

# ---------------- 설계 ----------------
N_AV = 30
N_G_TR, N_G_TE = 24, 12          # 학습/신규(응답 없음) 생성기
P = 3                            # 특징 수 (서로 상관)
C = np.array([0., 1., 2., 3., 4.])
K = 15

w_true = np.array([0.9, -0.5, 0.3])
SIG_E = 0.35                     # 특징이 설명 못 하는 난이도 잔차

def draw_features(n, rng):
    # 실제 지표들처럼 서로 상관(0.4)이 있는 특징
    R = np.full((P, P), 0.4) + 0.6 * np.eye(P)
    return rng.multivariate_normal(np.zeros(P), R, size=n)

X_tr = draw_features(N_G_TR, rng)
X_te = draw_features(N_G_TE, rng)

theta_t = rng.normal(0, 1, N_AV)
e_tr = rng.normal(0, SIG_E, N_G_TR)
e_te = rng.normal(0, SIG_E, N_G_TE)
beta_tr = -1.2 + X_tr @ w_true + e_tr          # 학습 생성기 난이도
beta_te = -1.2 + X_te @ w_true + e_te          # 신규 생성기 난이도 (참값)
gamma_t = rng.lognormal(np.log(0.5), 0.30, N_G_TR)
a_t     = rng.lognormal(np.log(1.0), 0.40, N_G_TR)
u_t     = rng.beta(2.0, 18.0, N_G_TR)

NG = N_G_TR
I, G, L = np.meshgrid(np.arange(N_AV), np.arange(NG), np.arange(len(C)),
                      indexing="ij")
I, G, L = I.ravel(), G.ravel(), L.ravel()
cc = C[L]

eta = a_t[G] * (beta_tr[G] + gamma_t[G] * cc - theta_t[I])
p = u_t[G] + (1 - u_t[G]) * expit(eta)
y = rng.binomial(K, p)
print(f"설계: {N_AV} AV x {NG} 학습 생성기 x {len(C)} severity x {K}회 = "
      f"{len(y)*K:,} 응답, 충돌률 {y.sum()/(len(y)*K):.3f} · "
      f"신규 생성기 {N_G_TE}개는 응답 없음(특징만)")

# ---------------- 적합 ----------------
# 모수: theta(N_AV), intercept(1), w(P), e(NG), log gamma(NG), log a(NG)
def unpack(x, with_resid=True):
    k = 0
    th = x[k:k+N_AV]; k += N_AV
    b0 = x[k]; k += 1
    w  = x[k:k+P]; k += P
    if with_resid:
        e = x[k:k+NG]; k += NG
    else:
        e = np.zeros(NG)
    ga = np.exp(x[k:k+NG]); k += NG
    a  = np.exp(x[k:k+NG]); k += NG
    return th, b0, w, e, ga, a

def neg_logpost(x, with_resid=True):
    th, b0, w, e, ga, a = unpack(x, with_resid)
    be = b0 + X_tr @ w + e
    eta = a[G] * (be[G] + ga[G] * cc - th[I])
    pp = u_t[G] + (1 - u_t[G]) * expit(eta)
    pp = np.clip(pp, 1e-9, 1 - 1e-9)
    ll = np.sum(y * np.log(pp) + (K - y) * np.log1p(-pp))
    lp = -0.5*np.sum(th**2) - 0.5*(b0/3.)**2 - 0.5*np.sum((w/3.)**2) \
         - 0.5*np.sum(((np.log(ga)-np.log(0.6))/1.)**2) \
         - 0.5*np.sum((np.log(a)/1.)**2)
    if with_resid:
        lp += -0.5*np.sum((e/SIG_E)**2)   # 잔차 사전 (분산은 알려진 것으로)
    return -(ll + lp)

def fit(with_resid=True, seed=0):
    r = np.random.default_rng(seed)
    n = N_AV + 1 + P + (NG if with_resid else 0) + 2*NG
    x0 = np.concatenate([np.zeros(N_AV), [0.], np.zeros(P),
                         np.zeros(NG) if with_resid else [],
                         np.full(NG, np.log(0.6)), np.zeros(NG)])
    x0 = x0 + 0.01 * r.normal(size=n)
    res = minimize(neg_logpost, x0, args=(with_resid,), method="L-BFGS-B",
                   options=dict(maxiter=6000, maxfun=400000))
    return unpack(res.x, with_resid)

def standardize(th, b0, w, e, ga, a):
    m, k = th.mean(), th.std()
    return ((th-m)/k, (b0-m)/k, w/k, e/k, ga/k, a*k)

# (1) 잔차 있는 설명적 IRT
th1, b01, w1, e1, ga1, a1 = standardize(*fit(with_resid=True))
beta1 = b01 + X_tr @ w1 + e1
# (3) 잔차 없는 LLTM (beta = w·x 정확하다고 가정)
th2, b02, w2, e2, ga2, a2 = standardize(*fit(with_resid=False))
beta2 = b02 + X_tr @ w2

res = {}
res["w_true"] = w_true.tolist()
res["w_resid"] = np.round(w1, 3).tolist()
res["w_lltm"] = np.round(w2, 3).tolist()
res["beta_recovery_resid"] = [float(pearsonr(beta1, beta_tr)[0]),
                              float(np.sqrt(np.mean((beta1-beta_tr)**2)))]
res["beta_recovery_lltm"] = [float(pearsonr(beta2, beta_tr)[0]),
                             float(np.sqrt(np.mean((beta2-beta_tr)**2)))]
res["theta_recovery_resid"] = [float(pearsonr(th1, theta_t)[0]),
                               float(np.sqrt(np.mean((th1-theta_t)**2)))]

# (2) 신규 생성기 난이도 예측 (응답 없음, 특징만)
pred_te_resid = b01 + X_te @ w1
pred_te_lltm  = b02 + X_te @ w2
pred_te_mean  = np.full(N_G_TE, beta1.mean())     # 특징 없는 기준선
res["oos_resid"] = [float(pearsonr(pred_te_resid, beta_te)[0]),
                    float(np.sqrt(np.mean((pred_te_resid-beta_te)**2)))]
res["oos_lltm"] = [float(pearsonr(pred_te_lltm, beta_te)[0]),
                   float(np.sqrt(np.mean((pred_te_lltm-beta_te)**2)))]
res["oos_baseline_rmse"] = float(np.sqrt(np.mean((pred_te_mean-beta_te)**2)))
res["oos_ceiling_sigma_e"] = SIG_E
print(json.dumps(res, indent=2, ensure_ascii=False))

# ---------------- 그림 ----------------
plt.rcParams.update({"font.size": 11, "figure.dpi": 140})
fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.3))

# (a) w 복원
ax = axes[0]
xs = np.arange(P)
wd = 0.27
ax.bar(xs - wd, w_true, wd, color="#475569", label="true w")
ax.bar(xs, w1, wd, color="#2563eb", label="explanatory IRT")
ax.bar(xs + wd, w2, wd, color="#dc2626", alpha=.8, label="LLTM (no resid)")
ax.axhline(0, color="#999", lw=.8)
ax.set_xticks(xs); ax.set_xticklabels([f"w{j+1}" for j in range(P)])
ax.set_title("covariate weights w", fontsize=11)
ax.legend(fontsize=8)

# (b) 학습 생성기 beta 복원
ax = axes[1]
lim = [min(beta_tr.min(), beta1.min())-.3, max(beta_tr.max(), beta1.max())+.3]
ax.plot(lim, lim, color="#bbb", lw=1)
ax.scatter(beta_tr, beta1, s=30, color="#2563eb", alpha=.85,
           label=f"with residual (r={res['beta_recovery_resid'][0]:.3f})")
ax.scatter(beta_tr, beta2, s=30, color="#dc2626", alpha=.65, marker="^",
           label=f"LLTM (r={res['beta_recovery_lltm'][0]:.3f})")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("true beta_G"); ax.set_ylabel("estimated beta_G")
ax.set_title("calibration generators (with responses)", fontsize=11)
ax.legend(fontsize=8)

# (c) 신규 생성기 OOS 예측
ax = axes[2]
lim = [min(beta_te.min(), pred_te_resid.min())-.4,
       max(beta_te.max(), pred_te_resid.max())+.4]
ax.plot(lim, lim, color="#bbb", lw=1)
ax.fill_between(lim, [lim[0]-2*SIG_E, lim[1]-2*SIG_E],
                [lim[0]+2*SIG_E, lim[1]+2*SIG_E],
                color="#94a3b8", alpha=.25,
                label="±2 sigma_e (irreducible)")
ax.scatter(beta_te, pred_te_resid, s=36, color="#2563eb",
           label=f"features only (r={res['oos_resid'][0]:.3f})")
ax.axhline(beta1.mean(), color="#dc2626", lw=1.2, ls="--",
           label=f"no-feature baseline (RMSE {res['oos_baseline_rmse']:.2f})")
ax.set_xlim(lim); ax.set_ylim(lim)
ax.set_xlabel("true beta (new generators)")
ax.set_ylabel("predicted from features only")
ax.set_title(f"new generators, no responses\n"
             f"RMSE {res['oos_resid'][1]:.3f} vs ceiling sigma_e={SIG_E}",
             fontsize=11)
ax.legend(fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig("research/assets/a1/a3_covariates.png", bbox_inches="tight")

with open("analysis/a1-identifiability/a3_results.json", "w",
          encoding="utf-8") as f:
    json.dump(res, f, indent=2, ensure_ascii=False)
print("저장: research/assets/a1/a3_covariates.png")
