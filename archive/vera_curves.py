import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

np.random.seed(42)
N = 92834
plays = np.random.zipf(1.8, N).astype(float)
plays = np.clip(plays, 1, 200)

epsilons = [0.1, 0.3, 0.5, 1.0, 1.5, 2.0]
rhos, aucs, noise_ratios = [], [], []

for eps in epsilons:
    real_mean = np.mean(plays)
    sensitivity = 1.0
    noise_scale = sensitivity / eps
    windows_real = [np.mean(plays[i:i+100]) for i in range(0, 50000, 100)]
    windows_dp   = [w + np.random.laplace(0, noise_scale) for w in windows_real]
    rho = np.corrcoef(windows_real, windows_dp)[0,1]
    rhos.append(rho)
    members     = plays[:N//2]
    non_members = np.random.zipf(1.8, N//2).astype(float)
    non_members = np.clip(non_members, 1, 200)
    dp_members     = members + np.random.laplace(0, noise_scale, N//2)
    dp_non_members = non_members + np.random.laplace(0, noise_scale, N//2)
    threshold = np.median(np.concatenate([dp_members, dp_non_members]))
    tp = np.sum(dp_members > threshold)
    fp = np.sum(dp_non_members > threshold)
    auc = (tp / (N//2) + (1 - fp/(N//2))) / 2
    aucs.append(auc)
    noise_ratios.append(noise_scale / np.std(plays))

fig, axes = plt.subplots(1, 3, figsize=(14, 5))
fig.suptitle('VERA Privacy/Utility Tradeoff — Last.fm hetrec2011 calibrated', fontsize=13)

axes[0].plot(epsilons, rhos, 'b-o', linewidth=2)
axes[0].axhline(y=0.95, color='r', linestyle='--', alpha=0.7, label='threshold p=0.95')
axes[0].set_xlabel('epsilon'); axes[0].set_ylabel('Correlation (utility)')
axes[0].set_title('Utility vs epsilon'); axes[0].legend(); axes[0].grid(True, alpha=0.3)

axes[1].plot(epsilons, aucs, 'r-o', linewidth=2)
axes[1].axhline(y=0.55, color='orange', linestyle='--', alpha=0.7, label='AUC=0.55')
axes[1].axhline(y=0.5,  color='g', linestyle='--', alpha=0.7, label='random=0.5')
axes[1].set_xlabel('epsilon'); axes[1].set_ylabel('Attacker AUC (MIA)')
axes[1].set_title('MIA Attack vs epsilon'); axes[1].legend(); axes[1].grid(True, alpha=0.3)

axes[2].plot(epsilons, noise_ratios, 'g-o', linewidth=2)
axes[2].set_xlabel('epsilon'); axes[2].set_ylabel('noise/signal ratio')
axes[2].set_title('Relative Noise vs epsilon'); axes[2].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('vera_utility_privacy.png', dpi=150, bbox_inches='tight')
print("OK")
print(f"\neps\t\trho\t\tAUC\t\tnoise_ratio")
for i, eps in enumerate(epsilons):
    print(f"{eps}\t\t{rhos[i]:.4f}\t\t{aucs[i]:.4f}\t\t{noise_ratios[i]:.4f}")
