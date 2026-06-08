# -*- coding: utf-8 -*-
"""
D-study · 격자 규모 결정 (decision study)

method.html 식 (6)의 측정 모델로 합성 응답을 생성한 뒤 MAP 적합으로 복원해,
격자 후보(AV × G × severity × 셀당 반복) 각각에서 다음 네 지표를 1000 trial로
분포 추정한다. 합격 판정·split·ablation은 모두 research/decisions.html D-03 ~ D-05.

지표:
  (1) split-half b̂ Pearson r              (주, D-03)
  (2) 평균 |Δb̂|                            (D-03 보조)
  (3) Mantel-Haenszel DIF χ²                (D-03 보조, 이분 응답 DIF 정통)
  (4) θ̂ 95% Laplace CI 폭                  (D-03 보조)

합격 판정 (D-04): r 분포의 25 percentile이 0.80 이상.
ablation (D-05): 합격 격자에서 정보적 사전 끄기·셀당 반복 절반.
실행:
  python3 d_study.py sanity   # 작은 격자 1점, 빠른 검증 (~5s)
  python3 d_study.py msanity  # 작은 격자 1점, 32 코어 multiprocessing 검증 (~10s)
  python3 d_study.py sweep    # 본 sweep (27 격자 × 2 sev × 1000 trial, ~수 시간)
"""
import os
# BLAS 스레드 1로 고정 : 안 그러면 multiprocessing worker마다 BLAS가 32 스레드 다 잡아
# 32 × 32 = 1024 스레드 경합. 단일 BLAS 스레드 × 32 워커가 가장 빠르다.
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"

import json
import sys
import time
import multiprocessing as mp
from itertools import product
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import pearsonr


# ===================== 설계 (decisions.html D-05) =====================
GRID_CANDIDATES = {
    "N_AV":  [4, 6, 8],
    "N_G":   [3, 4, 5],
    "N_SEV": [3, 5, 7],
    "K_REP": [10, 20, 30],
}
N_TRIALS_FULL  = 1000
N_SPLITS       = 50
R_THRESH       = 0.80
PASS_PERCENTILE = 25
SEV_PLACEMENTS = ["uniform", "adaptive"]

# 참 모수 분포 (A1과 일치)
TRUE_PRIORS = dict(
    theta_mean=0.0,    theta_sd=1.0,
    beta_mean=-1.2,    beta_sd=1.0,
    gamma_log_mean=np.log(0.5), gamma_log_sd=0.30,
    a_log_mean=np.log(1.0),     a_log_sd=0.40,
    u_alpha=2.0,       u_beta=18.0,
)


# ===================== 참 모수 추출 =====================
def draw_true_params(n_av: int, n_g: int, rng: np.random.Generator) -> dict:
    return dict(
        theta=rng.normal(TRUE_PRIORS["theta_mean"], TRUE_PRIORS["theta_sd"], n_av),
        beta=rng.normal(TRUE_PRIORS["beta_mean"], TRUE_PRIORS["beta_sd"], n_g),
        gamma=rng.lognormal(TRUE_PRIORS["gamma_log_mean"], TRUE_PRIORS["gamma_log_sd"], n_g),
        a=rng.lognormal(TRUE_PRIORS["a_log_mean"], TRUE_PRIORS["a_log_sd"], n_g),
        u=rng.beta(TRUE_PRIORS["u_alpha"], TRUE_PRIORS["u_beta"], n_g),
    )


# ===================== severity 배치 (D-05) =====================
def severity_levels(n_sev: int, placement: str,
                    true_params: Optional[dict] = None) -> np.ndarray:
    """등간격(uniform) 또는 (AV, G) c50 분포 percentile 적응(adaptive)."""
    if placement == "uniform":
        return np.linspace(0.0, 4.0, n_sev)
    if placement == "adaptive":
        if true_params is None:
            return np.linspace(0.0, 4.0, n_sev)
        # 참 c50 = (theta_pi - beta_G) / gamma_G 의 모든 (AV, G) 쌍 분포
        theta = true_params["theta"]; beta = true_params["beta"]; gamma = true_params["gamma"]
        c50 = (theta[:, None] - beta[None, :]) / gamma[None, :]
        c50 = np.clip(c50.ravel(), 0.0, 4.0)
        ps = np.linspace(10, 90, n_sev)
        return np.percentile(c50, ps)
    raise ValueError(f"unknown placement: {placement}")


# ===================== 응답 생성 (식 6) =====================
def simulate_responses(true: dict, n_sev: int, K: int, sev_placement: str,
                       rng: np.random.Generator) -> dict:
    n_av, n_g = true["theta"].shape[0], true["beta"].shape[0]
    C = severity_levels(n_sev, sev_placement, true)
    I_, G_, L_ = np.meshgrid(np.arange(n_av), np.arange(n_g), np.arange(n_sev),
                             indexing="ij")
    I_, G_, L_ = I_.ravel(), G_.ravel(), L_.ravel()
    cc = C[L_]
    item_id = G_ * n_sev + L_      # (G, c) 한 조합을 하나의 item으로 식별
    eta = true["a"][G_] * (true["beta"][G_] + true["gamma"][G_] * cc - true["theta"][I_])
    p = true["u"][G_] + (1.0 - true["u"][G_]) * expit(eta)
    y = rng.binomial(K, p)
    return dict(y=y, I=I_, G=G_, L=L_, cc=cc, item_id=item_id, K=K, C=C,
                n_av=n_av, n_g=n_g, n_sev=n_sev)


# ===================== MAP 적합 (A1을 격자 후보용으로 일반화) =====================
def _unpack(x, n_av, n_g, fix_u):
    k = 0
    theta = x[k:k+n_av]; k += n_av
    beta  = x[k:k+n_g];  k += n_g
    gamma = np.exp(x[k:k+n_g]); k += n_g
    a     = np.exp(x[k:k+n_g]); k += n_g
    if fix_u is None:
        u = expit(x[k:k+n_g]); k += n_g
    else:
        u = fix_u
    return theta, beta, gamma, a, u


def _neg_logpost(x, y, I_, G_, cc_, K_, n_av, n_g, fix_u, use_prior):
    k = 0
    theta = x[k:k+n_av]; k += n_av
    beta  = x[k:k+n_g];  k += n_g
    lg    = x[k:k+n_g];  k += n_g
    la    = x[k:k+n_g];  k += n_g
    gamma, a = np.exp(lg), np.exp(la)
    if fix_u is None:
        zu = x[k:k+n_g]; u = expit(zu); k += n_g
    else:
        u = fix_u
    eta = a[G_] * (beta[G_] + gamma[G_] * cc_ - theta[I_])
    p = u[G_] + (1.0 - u[G_]) * expit(eta)
    p = np.clip(p, 1e-9, 1 - 1e-9)
    ll = np.sum(y * np.log(p) + (K_ - y) * np.log1p(-p))
    if not use_prior:
        return -ll
    lp  = -0.5 * np.sum(theta**2)
    lp += -0.5 * np.sum((beta / 3.0)**2)
    lp += -0.5 * np.sum(((lg - np.log(0.6)) / 1.0)**2)
    lp += -0.5 * np.sum((la / 1.0)**2)
    if fix_u is None:
        lp += -0.5 * np.sum(((zu + 2.0) / 2.0)**2)
    return -(ll + lp)


def fit_map(resp, fix_u=None, use_prior=True, seed=0):
    n_av, n_g = resp["n_av"], resp["n_g"]
    rs = np.random.default_rng(seed)
    n = n_av + n_g * (3 if fix_u is not None else 4)
    x0 = np.concatenate([
        np.zeros(n_av), np.zeros(n_g),
        np.full(n_g, np.log(0.6)), np.zeros(n_g),
        ([] if fix_u is not None else np.full(n_g, -2.0)),
    ]) + 0.01 * rs.normal(size=n)
    res = minimize(_neg_logpost, x0,
                   args=(resp["y"], resp["I"], resp["G"], resp["cc"], resp["K"],
                         n_av, n_g, fix_u, use_prior),
                   method="L-BFGS-B",
                   options=dict(maxiter=4000, maxfun=200000))
    theta, beta, gamma, a, u = _unpack(res.x, n_av, n_g, fix_u)
    m, s = theta.mean(), max(theta.std(), 1e-6)
    theta = (theta - m) / s
    beta  = (beta - m) / s
    gamma = gamma / s
    a     = a * s
    # Laplace 표준오차: 수치 헤시안 + 표준화 야코비안 보정
    # (정정 2026-06-06 REVIEW_FIXLIST A-1 + 라운드 18 야코비안 잔여 정정)
    # 이전 (라운드 18 1차): se_theta = se_raw / s : m이 적합된 양인데 단일 척도만
    # 나눠 표준화 좌표의 sum-to-zero 제약과 sample 상관을 무시한 흠.
    # 정정 (라운드 18 2차): J = (I − 11ᵀ/n_av) / s 야코비안으로 J Σ J^T 공분산을
    # 정확히 산출한 뒤 대각의 제곱근을 표준화 좌표 SE로 사용.
    try:
        H_num = _numerical_hessian(
            _neg_logpost, res.x,
            args=(resp["y"], resp["I"], resp["G"], resp["cc"], resp["K"],
                  n_av, n_g, fix_u, use_prior),
        )
        cov_num = np.linalg.inv(H_num)
        # theta 부분 공분산 (raw 좌표)
        cov_theta_raw = cov_num[:n_av, :n_av]
        # 표준화 야코비안: θ' = (θ − mean(θ)) / s 의 ∂θ'/∂θ
        J = (np.eye(n_av) - np.ones((n_av, n_av)) / n_av) / s
        cov_theta_std = J @ cov_theta_raw @ J.T
        se_theta = np.sqrt(np.clip(np.diag(cov_theta_std), 0.0, None))
    except Exception:
        se_theta = np.full(n_av, np.nan)
    return dict(theta=theta, beta=beta, gamma=gamma, a=a, u=u,
                converged=bool(res.success), se_theta=se_theta, scale_s=float(s))


def _numerical_hessian(f, x, args=(), h=1e-5):
    """중심 차분(central difference) 기반 수치 헤시안 산출.

    L-BFGS-B의 res.hess_inv는 제한메모리 근사라 SE 산출에 신뢰할 수 없으므로
    최적점 x에서 함수 f의 정확한 수치 헤시안을 산출한다. n=O(20) 자료에서
    O(n²) 함수 호출이라 약 400회 호출, 본 격자(N_av=3) 자료에서 약 1~5초.
    """
    n = len(x)
    H = np.zeros((n, n))
    # 대각 성분: H_ii = (f(x+h) - 2f(x) + f(x-h)) / h^2
    f_x = float(f(x, *args))
    for i in range(n):
        x_p = x.copy(); x_p[i] += h
        x_m = x.copy(); x_m[i] -= h
        H[i, i] = (float(f(x_p, *args)) - 2 * f_x + float(f(x_m, *args))) / (h * h)
    # 비대각 성분: H_ij = (f(x+h_i+h_j) - f(x+h_i-h_j) - f(x-h_i+h_j) + f(x-h_i-h_j)) / (4 h^2)
    for i in range(n):
        for j in range(i + 1, n):
            x_pp = x.copy(); x_pp[i] += h; x_pp[j] += h
            x_pm = x.copy(); x_pm[i] += h; x_pm[j] -= h
            x_mp = x.copy(); x_mp[i] -= h; x_mp[j] += h
            x_mm = x.copy(); x_mm[i] -= h; x_mm[j] -= h
            H[i, j] = (float(f(x_pp, *args)) - float(f(x_pm, *args))
                       - float(f(x_mp, *args)) + float(f(x_mm, *args))) / (4 * h * h)
            H[j, i] = H[i, j]
    return H


def b_item_grid(beta, gamma, C):
    return beta[:, None] + gamma[:, None] * C[None, :]


# ===================== MH DIF χ² =====================
def mh_chi2(resp: dict, group_a: np.ndarray, group_b: np.ndarray) -> float:
    """Mantel-Haenszel χ²: AV를 두 그룹으로 가른 뒤 각 item (G, c)에서
    같은 어려움인지 검정. 단일 자유도 χ²이라 > 3.84면 유의 (α=0.05)."""
    K = resp["K"]
    A_obs = A_exp = A_var = 0.0
    for iid in np.unique(resp["item_id"]):
        mask = resp["item_id"] == iid
        I_item = resp["I"][mask]; y_item = resp["y"][mask]
        a_mask = np.isin(I_item, group_a); b_mask = np.isin(I_item, group_b)
        n_a = int(a_mask.sum()) * K
        n_b = int(b_mask.sum()) * K
        k_a = int(y_item[a_mask].sum())
        k_b = int(y_item[b_mask].sum())
        n_tot = n_a + n_b
        if n_tot < 2:
            continue
        k_tot = k_a + k_b
        if k_tot == 0 or k_tot == n_tot:
            continue   # 항상 모두 정답·오답이면 정보 없음
        E_ka = n_a * k_tot / n_tot
        var_ka = n_a * n_b * k_tot * (n_tot - k_tot) / (n_tot ** 2 * (n_tot - 1))
        A_obs += k_a; A_exp += E_ka; A_var += var_ka
    if A_var <= 0:
        return float("nan")
    return float((A_obs - A_exp) ** 2 / A_var)


# ===================== split-half (D-04) =====================
def split_half_metrics(resp: dict, true_u: np.ndarray,
                       rng: np.random.Generator, use_prior: bool):
    """한 split: b̂ Pearson r + MH χ². 반환: (r, mh_chi2)."""
    n_av = resp["n_av"]
    perm = rng.permutation(n_av)
    half_a, half_b = perm[:n_av // 2], perm[n_av // 2:]
    b_pair = []
    for half in (half_a, half_b):
        mask = np.isin(resp["I"], half)
        remap = {old: new for new, old in enumerate(half)}
        I_sub = np.array([remap[i] for i in resp["I"][mask]])
        sub = dict(y=resp["y"][mask], I=I_sub, G=resp["G"][mask],
                   cc=resp["cc"][mask], item_id=resp["item_id"][mask],
                   K=resp["K"], C=resp["C"],
                   n_av=len(half), n_g=resp["n_g"], n_sev=resp["n_sev"])
        f = fit_map(sub, fix_u=true_u, use_prior=use_prior,
                    seed=int(rng.integers(1e9)))
        b_pair.append(b_item_grid(f["beta"], f["gamma"], resp["C"]))
    r = float(pearsonr(b_pair[0].ravel(), b_pair[1].ravel())[0])
    mh = mh_chi2(resp, half_a, half_b)
    return r, mh, float(np.mean(np.abs(b_pair[0] - b_pair[1])))


# ===================== 한 trial =====================
def run_one_trial(n_av, n_g, n_sev, K, sev_placement, use_prior, n_splits, rng):
    true = draw_true_params(n_av, n_g, rng)
    resp = simulate_responses(true, n_sev, K, sev_placement, rng)
    main_fit = fit_map(resp, fix_u=true["u"], use_prior=use_prior,
                       seed=int(rng.integers(1e9)))
    rs, mhs, deltas = [], [], []
    for _ in range(n_splits):
        r, mh, d = split_half_metrics(resp, true["u"], rng, use_prior)
        rs.append(r); mhs.append(mh); deltas.append(d)
    b_true = b_item_grid(true["beta"], true["gamma"], resp["C"])
    b_est  = b_item_grid(main_fit["beta"], main_fit["gamma"], resp["C"])
    se = main_fit["se_theta"]
    ci_width = float(np.nanmean(2 * 1.96 * se)) if se.size else float("nan")
    return dict(
        split_r=np.array(rs),
        split_mh=np.array(mhs),
        split_delta=np.array(deltas),
        b_recovery_r=float(pearsonr(b_est.ravel(), b_true.ravel())[0]),
        theta_ci_width=ci_width,
        converged=bool(main_fit["converged"]),
    )


# ===================== multiprocessing worker =====================
def _trial_worker(args):
    n_av, n_g, n_sev, K, sev_placement, use_prior, n_splits, trial_seed = args
    rng = np.random.default_rng(trial_seed)
    try:
        return run_one_trial(n_av, n_g, n_sev, K, sev_placement, use_prior,
                             n_splits, rng)
    except Exception as e:
        return dict(error=str(e), converged=False)


def sweep_one_grid_parallel(grid, sev_placement, use_prior, n_trials, n_splits,
                            pool, base_seed=0, log_prefix=""):
    args_list = [
        (grid["n_av"], grid["n_g"], grid["n_sev"], grid["K"],
         sev_placement, use_prior, n_splits, base_seed + t)
        for t in range(n_trials)
    ]
    t0 = time.time()
    results = pool.map(_trial_worker, args_list)
    wall = time.time() - t0
    ok = [r for r in results if "error" not in r]
    if not ok:
        return dict(grid=grid, sev_placement=sev_placement, use_prior=use_prior,
                    n_trials=n_trials, error="all trials failed", wall_sec=wall)
    all_r  = np.concatenate([r["split_r"]     for r in ok])
    all_mh = np.concatenate([r["split_mh"]    for r in ok])
    all_d  = np.concatenate([r["split_delta"] for r in ok])
    all_ci = np.array([r["theta_ci_width"]    for r in ok])
    all_bv = np.array([r["b_recovery_r"]      for r in ok])
    p25 = float(np.nanpercentile(all_r, PASS_PERCENTILE))
    out = dict(
        grid=grid, sev_placement=sev_placement, use_prior=use_prior,
        n_trials=n_trials, n_splits=n_splits,
        n_converged=sum(int(r["converged"]) for r in ok),
        split_r_mean=float(np.nanmean(all_r)),
        split_r_p05=float(np.nanpercentile(all_r, 5)),
        split_r_p25=p25,
        split_r_p50=float(np.nanpercentile(all_r, 50)),
        split_r_p95=float(np.nanpercentile(all_r, 95)),
        split_mh_mean=float(np.nanmean(all_mh)),
        split_mh_p95=float(np.nanpercentile(all_mh, 95)),
        split_mh_dif_rate=float(np.mean(all_mh > 3.84)),   # α=0.05 거짓발견 비율
        split_delta_mean=float(np.nanmean(all_d)),
        theta_ci_width_mean=float(np.nanmean(all_ci)),
        recovery_r_mean=float(np.nanmean(all_bv)),
        wall_sec=wall,
        pass_at_threshold=p25 >= R_THRESH,
    )
    if log_prefix:
        print(f"{log_prefix} grid={grid} sev={sev_placement} "
              f"p25={p25:.3f} pass={'YES' if out['pass_at_threshold'] else 'no'} "
              f"({wall:.1f}s)", flush=True)
    return out


# ===================== 전체 sweep =====================
def sweep_all_grids(pool, n_trials, n_splits):
    """27 격자 × 2 sev 배치 = 54 sweep."""
    grids = []
    for n_av, n_g, n_sev, K in product(
            GRID_CANDIDATES["N_AV"], GRID_CANDIDATES["N_G"],
            GRID_CANDIDATES["N_SEV"], GRID_CANDIDATES["K_REP"]):
        grids.append(dict(n_av=n_av, n_g=n_g, n_sev=n_sev, K=K))
    print(f">>> 본 sweep 시작: {len(grids)} 격자 × {len(SEV_PLACEMENTS)} sev × "
          f"{n_trials} trial · 32 코어 multiprocessing", flush=True)
    out = []
    t_total = time.time()
    for i, grid in enumerate(grids):
        for sev_placement in SEV_PLACEMENTS:
            res = sweep_one_grid_parallel(
                grid, sev_placement, use_prior=True,
                n_trials=n_trials, n_splits=n_splits, pool=pool,
                base_seed=20260603 + i * 10000,
                log_prefix=f"  [{i+1:2d}/{len(grids)}]"
            )
            out.append(res)
    print(f">>> sweep 완료, 전체 {time.time() - t_total:.0f}s", flush=True)
    return out


# ===================== ablation (D-05) =====================
def run_ablation(best_grid, pool, n_trials, n_splits):
    """합격 격자에서 두 가지: 정보적 사전 끄기 · 셀당 반복 절반.
    severity 배치 비교(uniform vs adaptive)는 이미 본 sweep에 있으므로 별도 안 함."""
    print(f">>> ablation 시작 (격자: {best_grid})", flush=True)
    ab = []
    # (a) 정보적 사전 끄기 (sev=adaptive 기준)
    ab.append(sweep_one_grid_parallel(
        best_grid, "adaptive", use_prior=False,
        n_trials=n_trials, n_splits=n_splits, pool=pool,
        base_seed=987654321, log_prefix="  [ab/prior-off]"))
    # (b) K 절반 (사전 on, sev=adaptive)
    half_K_grid = dict(best_grid); half_K_grid["K"] = max(2, best_grid["K"] // 2)
    ab.append(sweep_one_grid_parallel(
        half_K_grid, "adaptive", use_prior=True,
        n_trials=n_trials, n_splits=n_splits, pool=pool,
        base_seed=123456789, log_prefix="  [ab/half-K]"))
    return ab


# ===================== 시간 예산 표 =====================
def time_budget_table(sweep_results, sec_per_cell=60.0, parallel=2):
    """4080 한 대로 합격 격자를 채우는 데 걸리는 시간 (시간 단위)."""
    rows = []
    for r in sweep_results:
        if r.get("error"):
            continue
        g = r["grid"]
        cells = g["n_av"] * g["n_g"] * g["n_sev"] * g["K"]
        hours = cells * sec_per_cell / parallel / 3600.0
        rows.append(dict(
            grid=g, sev=r["sev_placement"],
            cells=cells, est_hours_4080=hours,
            pass_at_threshold=r["pass_at_threshold"],
        ))
    return rows


# ===================== sanity checks =====================
def sanity_check_single():
    """단일 코어, 작은 격자 1점 (~5s)."""
    rng = np.random.default_rng(20260603)
    print(">>> 1단계 sanity (단일 코어, 작은 격자 10 trial · 10 split)", flush=True)
    out = run_one_trial(4, 3, 3, 10, "uniform", True, 10, rng)
    print(f"  split_r 평균 {out['split_r'].mean():.3f} p25 {np.percentile(out['split_r'], 25):.3f}",
          flush=True)
    print(f"  split_mh 평균 {out['split_mh'].mean():.2f} (>3.84 비율 {np.mean(out['split_mh'] > 3.84):.2f})",
          flush=True)
    print(f"  θ̂ CI 폭 {out['theta_ci_width']:.3f}", flush=True)
    print(f"  본 b̂ 복원 r {out['b_recovery_r']:.3f}", flush=True)


def sanity_check_multiproc():
    """32 코어 multiprocessing, 작은 격자 1점, 20 trial × 10 split (~10s)."""
    print(">>> 2단계 sanity (32 코어 multiprocessing, 20 trial · 10 split)", flush=True)
    grid = dict(n_av=4, n_g=3, n_sev=3, K=10)
    with mp.Pool(32) as pool:
        res = sweep_one_grid_parallel(grid, "uniform", True,
                                       n_trials=20, n_splits=10, pool=pool,
                                       log_prefix="  [msanity]")
    print(json.dumps({k: v for k, v in res.items() if not isinstance(v, dict) or k == "grid"},
                     ensure_ascii=False, indent=2), flush=True)


# ===================== 본 sweep main =====================
def full_sweep_and_save():
    """본 sweep + ablation + JSON 저장."""
    out_path = Path(__file__).resolve().parent / "d_study_results.json"
    print(f">>> 결과 저장 경로: {out_path}", flush=True)
    with mp.Pool(32) as pool:
        sweep = sweep_all_grids(pool, n_trials=N_TRIALS_FULL, n_splits=N_SPLITS)
        # 합격 격자 중 가장 작은 것 선택 (셀 수 기준)
        passing = [r for r in sweep if r.get("pass_at_threshold")]
        ablation_target = None
        ablation = []
        if passing:
            ablation_target = min(passing, key=lambda r: (
                r["grid"]["n_av"] * r["grid"]["n_g"] *
                r["grid"]["n_sev"] * r["grid"]["K"]))["grid"]
            ablation = run_ablation(ablation_target, pool,
                                    n_trials=N_TRIALS_FULL, n_splits=N_SPLITS)
        else:
            print(">>> 합격 격자 없음 : 가장 큰 격자에서 ablation 돌림", flush=True)
            biggest = max(sweep, key=lambda r: (
                r["grid"]["n_av"] * r["grid"]["n_g"] *
                r["grid"]["n_sev"] * r["grid"]["K"]))
            ablation_target = biggest["grid"]
            ablation = run_ablation(ablation_target, pool,
                                    n_trials=N_TRIALS_FULL, n_splits=N_SPLITS)
    budget = time_budget_table(sweep)
    results = dict(
        config=dict(
            grid_candidates=GRID_CANDIDATES,
            n_trials=N_TRIALS_FULL, n_splits=N_SPLITS,
            r_thresh=R_THRESH, pass_percentile=PASS_PERCENTILE,
            sev_placements=SEV_PLACEMENTS,
            true_priors={k: float(v) if not callable(v) else None
                         for k, v in TRUE_PRIORS.items()},
        ),
        sweep=sweep,
        ablation_target_grid=ablation_target,
        ablation=ablation,
        time_budget_4080=budget,
    )
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2,
                                   default=lambda o: float(o) if isinstance(o, np.floating)
                                                     else (int(o) if isinstance(o, np.integer)
                                                     else o.tolist() if isinstance(o, np.ndarray)
                                                     else str(o))))
    print(f">>> JSON 저장 완료: {out_path}", flush=True)


# ===================== entrypoint =====================
if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "sanity"
    if mode == "sanity":
        sanity_check_single()
    elif mode == "msanity":
        sanity_check_multiproc()
    elif mode == "sweep":
        full_sweep_and_save()
    else:
        print(f"unknown mode: {mode}. use sanity | msanity | sweep")
