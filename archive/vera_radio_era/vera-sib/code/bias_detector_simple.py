import numpy as np

np.random.seed(42)
signal_original = np.random.randn(100, 16)
signal_perturbed = signal_original * 1.2 + 0.3

residuals = np.mean(signal_perturbed - signal_original, axis=0)
mean_residual = np.mean(residuals)
std_residual = np.std(residuals)

print(f"Bias Detector (numpy-only)")
print(f"Mean residual: {mean_residual:.4f}")
print(f"Std residual: {std_residual:.4f}")
print(f"Offset detected: {abs(mean_residual) > 2*std_residual}")
