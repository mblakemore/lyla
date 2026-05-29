# Probabilistic Programming Fundamentals

## The Core Idea

Probabilistic programming languages (PPLs) let you specify probabilistic models as code, then automatically infer posterior distributions. Instead of writing inference algorithms by hand, you declare the model and let the PPL handle the computation.

**The pipeline:**
1. Specify a probabilistic model (priors + likelihood)
2. Observe data
3. Run inference (automatic)
4. Get posterior samples → uncertainty quantification, predictions, decisions

This is Bayesian inference as a first-class programming primitive.

---

## Inference Engines

### Hamiltonian Monte Carlo (HMC)

The workhorse of modern Bayesian computation. Unlike random-walk MCMC (Metropolis, Gibbs), HMC uses gradient information to explore parameter space efficiently.

**Key insight:** Treat parameter estimation as a physics simulation. Assign each parameter a "velocity" and let the log-posterior gradient act as a force. The resulting trajectory explores the posterior in long, directed steps rather than random hops.

**Why it matters:** Random-walk MCMC scales as O(D) in D dimensions. HMC scales as O(log D) — essentially dimension-independent. For models with 10+ parameters, HMC is orders of magnitude more efficient.

**The catch:** HMC requires gradients of the log-posterior. This means models must be differentiable — no discrete parameters, no hard thresholds.

### No-U-Turn Sampler (NUTS)

HMC requires two hyperparameters: step size and number of steps. NUTS (Hoffman & Gelman 2014) eliminates both by:
- Building trajectories adaptively until they double back (a "U-turn")
- Using a doubling tree structure that's computationally efficient
- Automatically terminating when the trajectory starts looping

NUTS is the default sampler in both Stan and PyMC. It's "just works" for most continuous models.

### Variational Inference (VI)

Approximate the posterior with a parametric family (usually mean-field Gaussian). Optimize the ELBO — the same objective from C522.

**Pros:** Fast, scalable to millions of data points, differentiable (great for deep learning)
**Cons:** Mean-field assumption ignores correlations, underestimates uncertainty, can miss multimodality

**When to use:** Large datasets, hierarchical models with many groups, or when you need inference inside a neural network.

### Laplace Approximation

Approximate the posterior as a Gaussian centered at the MAP estimate, with curvature from the Hessian. Fast for low-dimensional problems, but same limitations as mean-field VI.

---

## Stan: The HMC Engine

Stan (Carpenter et al. 2017) is a compiled PPL that specializes in HMC/NUTS. It's the inference engine behind CmdStanPy, rstan, and PyMC's backend.

**Model specification:**
```stan
data {
  int<lower=0> N;           // number of observations
  vector[N] x;              // predictor
  vector[N] y;              // response
}
parameters {
  real alpha;               // intercept
  real beta;                // slope
  real<lower=0> sigma;      // noise
}
model {
  // Priors
  alpha ~ normal(0, 5);
  beta ~ normal(0, 2);
  sigma ~ cauchy(0, 2.5);

  // Likelihood
  y ~ normal(alpha + beta * x, sigma);
}
```

**Key strengths:**
- **Differentiation:** Automatic differentiation via reverse mode (like backprop) gives exact gradients
- **No-tuning:** NUTS adapts step size and trajectory length automatically
- **Warmup:** Initial phase estimates the mass matrix (approximate posterior covariance) for better sampling geometry
- **Diagnostics built-in:** R-hat, effective sample size, tree depth monitoring

**Weaknesses:**
- No discrete parameters (gradients don't exist)
- No built-in marginalization (you write the sum/integral)
- Compiled language — slower iteration cycle than pure Python

**The Stan pipeline:**
1. Write model in Stan language
2. Stan compiles to C++ → links to math library
3. Warmup phase: adapts step size, estimates mass matrix
4. Sampling phase: NUTS draws posterior samples
5. Diagnostics: R-hat < 1.01, ESS > 400 per parameter

---

## PyMC: Python-First Probabilistic Programming

PyMC (v5+) is a pure-Python PPL built on Aesara/PyTorch for automatic differentiation.

**Model specification:**
```python
import pymc as pm
import numpy as np

with pm.Model() as model:
    # Priors
    alpha = pm.Normal("alpha", mu=0, sigma=5)
    beta = pm.Normal("beta", mu=0, sigma=2)
    sigma = pm.HalfNormal("sigma", sigma=2.5)

    # Likelihood
    mu = alpha + beta * x
    y_obs = pm.Normal("y_obs", mu=mu, sigma=sigma, observed=y)

    # Sample
    trace = pm.sample(4000, tune=2000, target_accept=0.9)
```

**Key strengths:**
- Python-native — no separate model language
- Flexible model construction (loops, conditionals, hierarchical indexing)
- Multiple backends: NUTS (default), MCMC, VI, Laplace
- Built on PyTensor (formerly Aesara) for symbolic computation + autodiff
- Seamless integration with NumPy, pandas, scikit-learn

**Weaknesses:**
- Slower than Stan for large models (Python overhead)
- More flexible → more room for user error
- Debugging inference issues requires understanding the model graph

---

## Model Diagnostics

### R-hat (Gelman-Rubin Statistic)

Measures convergence across multiple chains. Run K chains from overdispersed initial values. If all chains explore the same posterior, within-chain and between-chain variances match → R-hat ≈ 1.

**Threshold:** R-hat < 1.01 (Gelman 2021). Older threshold was 1.1 — too lenient.

**How it works:**
- Split each chain into halves → estimate within-chain variance W
- Compare to between-chain variance B
- R-hat = sqrt((B/N) / W) with finite-sample correction

### Effective Sample Size (ESS)

MCMC samples are correlated. ESS tells you how many independent samples your correlated chain is worth.

**Two types:**
- **ESS_mean:** For estimating posterior means (accounts for autocorrelation)
- **ESS_std:** For estimating posterior variance/tails (more conservative)

**Rule of thumb:** ESS > 400 per parameter for reliable estimates. ESS < 100 → diagnose the model.

### Posterior Predictive Checks

Generate synthetic data from the posterior predictive distribution. If the model is good, synthetic data should look like observed data.

```python
# In PyMC
ppc = pm.sample_posterior_predictive(trace)
# Compare: mean(ppc["y_obs"]) vs y_observed
```

This catches model misspecification that R-hat and ESS miss — a model can converge perfectly to the wrong answer.

### Divergences

NUTS detects when the trajectory is heading into a region it hasn't explored. Divergences indicate the posterior has geometry the sampler is missing (funnels, ridges, discontinuities).

**Fix:** Re-parameterize (non-centered parameterization for hierarchical models), increase `target_accept`, or check for data issues.

---

## Hierarchical Models

The killer application for probabilistic programming. Hierarchical (multilevel) models share information across groups via a common prior.

```python
with pm.Model() as hierarchical:
    # Group-level hyperparameters
    mu_alpha = pm.Normal("mu_alpha", 0, 5)
    sigma_alpha = pm.HalfNormal("sigma_alpha", 5)

    # Group-level parameters
    alpha = pm.Normal("alpha", mu_alpha, sigma_alpha, shape=K)

    # Observations
    y_obs = pm.Normal("y_obs", alpha[group], sigma, observed=y)
```

**Centered vs non-centered parameterization:**
- **Centered:** Sample group effects directly. Good when groups have lots of data.
- **Non-centered:** Sample standard normals, then transform. Good when groups have little data (avoids the "funnel" geometry).

The non-centered parameterization is the canonical HMC re-parameterization trick. It turns aNeal's funnel (a pathological posterior geometry) into a cylinder — easy for HMC to sample.

---

## The Computational Reasoning Stack (C520-C525)

```
Information Theory (C520)  →  entropy, KL, mutual information
       ↓
Bayesian Inference (C521)  →  Bayes' theorem, conjugacy, hierarchical models
       ↓
Variational Inference (C522) →  ELBO, mean-field, speed at cost of accuracy
       ↓
Gaussian Processes (C523)   →  non-parametric priors, kernel methods
       ↓
Causal Inference (C524)     →  SCM, do-calculus, identification
       ↓
Probabilistic Programming (C525) → HMC/NUTS, Stan, PyMC, diagnostics
```

PPLs operationalize the entire stack: Bayes' theorem gives the framework, VI and HMC are inference engines, GPs are model components, causal models are structural priors, and information theory provides the loss functions (KL divergence = ELBO).
