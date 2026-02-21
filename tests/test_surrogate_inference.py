from photonstrust.ai_surrogate import cached_surrogate, clear_surrogate_cache, HAS_SKLEARN
import math
import numpy as np
import pytest

@cached_surrogate(domain="dummy_physics", train_threshold=10)
def complex_physics_sim(length_um: float, width_nm: float, coupling: float) -> complex:
    phase = length_um * 2.0 * math.pi / 1.55
    loss = math.exp(-0.01 * length_um / width_nm)
    return loss * (1.0 - coupling) * complex(math.cos(phase), math.sin(phase))

def test_ai_surrogate_training_and_inference():
    clear_surrogate_cache()
    
    for i in range(10):
        res = complex_physics_sim(length_um=10.0 + i*0.1, width_nm=500.0, coupling=0.1)
        assert isinstance(res, complex)
        
    if HAS_SKLEARN:
        res_surrogate = complex_physics_sim(length_um=10.55, width_nm=500.0, coupling=0.1)
        assert isinstance(res_surrogate, complex)
        assert abs(res_surrogate) > 0.1 

def test_ai_surrogate_scalar_inference():
    clear_surrogate_cache()
    
    @cached_surrogate(domain="scalar_physics", train_threshold=5)
    def scalar_sim(temp_k: float) -> float:
        return temp_k ** 2.0
        
    for i in range(5):
        scalar_sim(temp_k=300.0 + i)
        
    if HAS_SKLEARN:
        res = scalar_sim(temp_k=302.5)
        assert isinstance(res, float)
