import random, math

DELTA_INT = 10
EPS = 0.5
N_SIM = 100000

def laplace(scale):
    u = random.random() - 0.5
    return -scale * math.copysign(1.0, u) * math.log(1 - 2*abs(u))

def mesure_k(k):
    scale = DELTA_INT / EPS
    obs_non = []
    obs_oui = []
    for _ in range(N_SIM):
        moy_non = sum(DELTA_INT + laplace(scale) for _ in range(k)) / k
        moy_oui = sum(0.0 + laplace(scale) for _ in range(k)) / k
        obs_non.append(moy_non)
        obs_oui.append(moy_oui)
    oui_sorted = sorted(obs_oui)
    def tpr_at_fpr(fpr):
        idx = int((1 - fpr) * len(oui_sorted))
        seuil = oui_sorted[min(idx, len(oui_sorted)-1)]
        return sum(1 for v in obs_non if v >= seuil) / len(obs_non)
    return tpr_at_fpr(0.10), tpr_at_fpr(0.01), tpr_at_fpr(0.001)

print("Porte 8 en composition - outlier observe k fois (eps=0.5)")
print("k      TPR@10%  TPR@1%  TPR@0.1%")
for k in [1, 5, 10, 50]:
    t10, t1, t01 = mesure_k(k)
    print(f"{k:<4}   {t10:7.2%}  {t1:6.2%}  {t01:7.2%}")
print()
print("k=1  : garanti par la partition (porte 7)")
print("k>1  : seulement si la partition est VIOLEE")
print("Lecture : la fuite monte avec k. La porte 7 maintient k=1.")