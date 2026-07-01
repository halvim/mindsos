"""
Capacity 2 (grounding) — pixel -> structural pixel. DETERMINISTIC contrast filter.
A structural pixel = a location where local contrast magnitude crosses a threshold.
No learning, no attributes. Whatever the generator draws, this lists the structural pixels.
"""
import numpy as np

def grad_mag(img):
    kx = np.array([[-1,0,1],[-2,0,2],[-1,0,1]], float)
    p = np.pad(img, 1, mode="edge")
    gx = gy = None
    def c(k):
        out = np.zeros_like(img)
        for i in range(3):
            for j in range(3):
                out += k[i,j] * p[i:i+img.shape[0], j:j+img.shape[1]]
        return out
    return np.hypot(c(kx), c(kx.T))

def structural_pixels(img, tau=0.3):
    """The whole capacity: deterministic contrast filter -> boolean mask of structural pixels."""
    return grad_mag(img) > tau
