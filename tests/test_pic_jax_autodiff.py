import jax
import jax.numpy as jnp
from photonstrust.components.pic.library import component_scattering_matrix

jax.config.update("jax_enable_x64", True)

def test_jax_autodiff_phase_shifter():
    # We want to differentiate the output power of a simple setup w.r.t the phase shift
    # Setup: Light enters a phase shifter.
    
    def output_power(phase_rad):
        # Build component scattering matrix (2x2)
        params = {"phase_rad": phase_rad, "insertion_loss_db": 0.0}
        S = component_scattering_matrix("pic.phase_shifter", params, wavelength_nm=1550.0)
        
        # Inject light into port 0
        a_ext = jnp.array([1.0 + 0.0j, 0.0 + 0.0j], dtype=jnp.complex128)
        
        # In a single component driven directly, b = S @ a_ext
        b = S @ a_ext
        
        # Power at output (port 1)
        amp = b[1]
        
        # Return real power (abs squared)
        return jnp.abs(amp) ** 2

    # The power should be 1.0 regardless of phase shift for a single phase shifter
    power = output_power(0.5)
    
    # Compute the gradient of power w.r.t phase_rad
    grad_fn = jax.grad(output_power)
    gradient = grad_fn(0.5)

    assert jnp.isclose(power, 1.0)
    assert jnp.isclose(gradient, 0.0)


def test_jax_autodiff_mzi_interference():
    # Setup: Mach-Zehnder Interferometer (MZI)
    # The output power of an MZI strongly depends on the phase difference between arms.

    def mzi_output_power(phase_rad):
        # We will build the S matrix for the whole MZI manually for this pure JAX test
        # to prove the component library math is differentiable.
        
        # Coupler 1 (50/50)
        cpl_params = {"coupling_ratio": 0.5}
        S_cpl = component_scattering_matrix("pic.coupler", cpl_params, wavelength_nm=1550.0)
        
        # Phase shifters
        S_ps1 = component_scattering_matrix("pic.phase_shifter", {"phase_rad": 0.0}, wavelength_nm=1550.0)
        S_ps2 = component_scattering_matrix("pic.phase_shifter", {"phase_rad": phase_rad}, wavelength_nm=1550.0)
        
        # forward matrix for coupler is S_cpl[2:4, 0:2]
        T_cpl = S_cpl[2:4, 0:2]
        
        T_ps = jnp.block([
            [S_ps1[1, 0], jnp.zeros_like(S_ps1[1, 0])],
            [jnp.zeros_like(S_ps2[1, 0]), S_ps2[1, 0]]
        ])
        
        # Total forward transmission
        T_total = T_cpl @ T_ps @ T_cpl
        
        # Input power at in1 only
        a_in = jnp.array([1.0 + 0.0j, 0.0 + 0.0j], dtype=jnp.complex128)
        
        b_out = T_total @ a_in
        
        # We look at output 1 power
        return jnp.abs(b_out[0]) ** 2

    power_0 = mzi_output_power(0.0)
    power_pi = mzi_output_power(jnp.pi)
    
    assert jnp.allclose(power_0, 0.0, atol=1e-5)
    assert jnp.allclose(power_pi, 1.0, atol=1e-5)
    
    grad_fn = jax.grad(mzi_output_power)
    
    grad_pi_2 = grad_fn(jnp.pi / 2.0)
    expected_grad_pi_2 = 0.5 * jnp.sin(jnp.pi / 2.0)
    assert jnp.allclose(grad_pi_2, expected_grad_pi_2, atol=1e-5)

if __name__ == "__main__":
    print("Testing phase shifter autodiff...")
    test_jax_autodiff_phase_shifter()
    print("Testing MZI autodiff...")
    test_jax_autodiff_mzi_interference()
    print("Success!")
