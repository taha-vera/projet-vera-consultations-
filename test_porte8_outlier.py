import random, math

DELTA_INT = 10
N_SIM = 200000

def laplace(scale):
    u = random.random() - 0.5
    return -scale * math.copysign(1.0, u) * math.log(1 - 2*abs(u))

def mesure(eps):
    scale = DELTA_INT / eps
    obs_non = [DELTA_INT + laplace(scale) for _ in range(N_SIM)]
    obs_oui = [0.0 + laplace(scale) for _ in range(N_SIM)]
    oui_sorted = sorted(obs_oui)
    def tpr_at_fpr(fpr):
        idx = int((1 - fpr) * len(oui_sorted))
        seuil = oui_sorted[min(idx, len(oui_sorted)-1)]
        tp = sum(1 for v in obs_non if v >= seuil)
        return tp / len(obs_non)
    return (eps, scale, tpr_at_fpr(0.10), tpr_at_fpr(0.01), tpr_at_fpr(0.001))

print("Porte 8 - fuite sur l'outlier")
print("eps    scale   TPR@10%  TPR@1%  TPR@0.1%")
for eps in [0.5, 0.1, 0.08]:
    eps, scale, t10, t1, t01 = mesure(eps)
    print(f"{eps:.2f}  {scale:6.1f}  {t10:7.2%}  {t1:6.2%}  {t01:7.2%}")