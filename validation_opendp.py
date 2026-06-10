import math
import opendp.prelude as dp
dp.enable_features("contrib")

R = 20
DS = 0.45
DELTA_INT = math.floor(R * DS) + 1
EPS_CIBLE = 0.5
SCALE = DELTA_INT / EPS_CIBLE

space = dp.atom_domain(T=int), dp.absolute_distance(T=int)
meas = space >> dp.m.then_laplace(scale=SCALE)
eps = meas.map(d_in=DELTA_INT)

print("Delta_int =", DELTA_INT, " scale =", SCALE)
print("epsilon garanti =", eps)
print("exemple f=0.7331 ->", meas(round(0.7331 * R)))
print("VERDICT:", "OK - garantie exacte" if eps <= EPS_CIBLE + 1e-12 else "ECHEC")