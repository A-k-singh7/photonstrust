# Troubleshooting

Common errors, their causes, and how to fix them.

---

## "Key rate is zero"

The secure key rate dropped to zero at your target distance.

**Possible causes and fixes:**

- **Distance exceeds protocol capability.** BB84 maxes out around 200 km on
  standard fiber. For longer distances, use `tf_qkd`, `pm_qkd`, or `sns_tf_qkd`
  which can surpass the PLOB bound and reach 400-500 km.

  ```python
  # Switch from BB84 to TF-QKD for long-haul
  result = simulate_qkd_link(protocol="tf_qkd", distance_km=300)
  ```

- **High-loss band selected.** The NIR bands (`nir_795` at 2.5 dB/km, `nir_850`
  at 2.2 dB/km) have much higher fiber attenuation than C-band (`c_1550` at
  0.20 dB/km). Switch to `c_1550` or `o_1310` for longer links.

- **QBER too high.** If detector dark counts, misalignment, or multi-photon
  emission push the QBER above the protocol threshold (~11% for BB84), the key
  rate is set to zero. Try lowering `g2_0`, reducing `dark_counts_cps`, or using
  SNSPD detectors.

- **Finite-key effects.** At low total detection counts (short runs or very
  lossy links), finite-key corrections can drive the rate to zero even if the
  asymptotic rate is positive.

---

## "Unknown protocol '<name>'"

The protocol name was not recognized.

**Fix:** Use one of the registered protocol names or aliases:

```bash
photonstrust list protocols
```

Common mappings:
| What you typed | Correct name   |
|----------------|----------------|
| `bb84`         | `bb84_decoy`   |
| `e91`          | `bbm92`        |
| `tf`           | `tf_qkd`       |
| `twin_field`   | `tf_qkd`       |
| `mdi`          | `mdi_qkd`      |
| `gg02`         | `cv_qkd`       |
| `sns`          | `sns_tf_qkd`   |

> The `simulate_qkd_link` function automatically normalizes common aliases, so
> `protocol="bb84"` resolves to `bb84_decoy`. If you get this error, check for
> typos.

---

## "Protocol applicability failed"

The selected protocol is not compatible with the chosen channel model.

**Rules:**
- **Fiber only:** `mdi_qkd`, `amdi_qkd`, `pm_qkd`, `tf_qkd`, `sns_tf_qkd`
  require `channel_model="fiber"`.
- **All channels:** `bb84`, `bbm92`, `cv_qkd`, `di_qkd` work with `fiber`,
  `free_space`, and `satellite`.

**Fix:** Change the protocol or the channel model:

```python
# MDI-QKD only works with fiber
result = simulate_qkd_link(protocol="mdi_qkd", channel_model="fiber")

# For satellite links, use BB84 instead
result = simulate_qkd_link(protocol="bb84", channel_model="satellite")
```

---

## "ConfigSchemaVersionError"

Your YAML configuration file is missing a schema version or has an unsupported
version.

**Fix:** Add `schema_version: "0.1"` to the top level of your YAML config:

```yaml
schema_version: "0.1"
band: c_1550
protocol:
  name: bb84
# ... rest of config
```

Legacy configs (version `"0.0"` or missing version) are auto-migrated
internally, but some edge cases may fail. Explicitly setting `"0.1"` is
recommended.

---

## ImportError for optional features

Some features require optional dependencies.

| Error message              | Fix                                      |
|----------------------------|------------------------------------------|
| `No module named 'rich'`   | `pip install photonstrust[cli]`           |
| `No module named 'qutip'`  | `pip install photonstrust[qutip]`         |
| `No module named 'matplotlib'` | `pip install matplotlib`              |
| Various missing modules    | `pip install photonstrust[dev]` (all deps)|

---

## "JAX not found" / JAX errors

JAX is not required for the base PhotonTrust QKD quickstart. If you see
JAX-related errors, you are likely on an optional path that expects it.

Install it only when the workflow you are using requires it:

```bash
pip install jax
```

On Windows, JAX CPU-only is usually sufficient:

```bash
pip install jax[cpu]
```

If you encounter `jax.config` errors on import, ensure you have a compatible
JAX version (0.4+ recommended) and confirm the active workflow actually depends
on JAX.

---

## "Unknown band '<name>'" / "Unknown detector class '<name>'"

The band or detector name was not recognized.

**Available bands:** `nir_795`, `nir_850`, `o_1310`, `c_1550`

**Available detectors:** `si_apd`, `ingaas`, `snspd`

```bash
photonstrust list bands
photonstrust list detectors
```

---

## Slow simulations

**Performance tips:**

- **Disable uncertainty analysis.** Set `include_uncertainty=False` for quick
  exploratory runs. Uncertainty adds Monte Carlo sampling overhead.

  ```python
  result = simulate_qkd_link(protocol="bb84", distance_km=50, include_uncertainty=False)
  ```

- **Single-point evaluation.** Pass a single distance instead of a sweep to
  get one key-rate value quickly:

  ```python
  result = simulate_qkd_link(protocol="bb84", distance_km=[50.0])
  ```

- **Reduce sweep resolution.** Use a coarser step size:

  ```python
  result = simulate_qkd_link(
      protocol="bb84",
      distance_km={"start": 0, "stop": 200, "step": 20},  # 11 points, not 41
  )
  ```

- **Compare fewer protocols.** When using `compare_protocols`, specify only the
  2-3 protocols you care about rather than all 9:

  ```python
  comp = compare_protocols(protocols=["bb84", "tf_qkd"])  # not all 9
  ```

- **Use analytic backend.** The default `physics_backend="analytic"` is much
  faster than `"qutip"`. Only use QuTiP when you need full master-equation
  dynamics.

---

## Matplotlib / plotting issues

- **"matplotlib not installed"**: Install it with `pip install matplotlib`.
- **Blank or non-displaying plots**: The `result.plot()` method returns a
  matplotlib `Figure` object. In scripts, call `plt.show()` or pass
  `save_path="plot.png"` to save to a file.
- **In Jupyter notebooks**: Plots display automatically. Add `%matplotlib inline`
  at the top of your notebook if they do not.

---

## Getting help

If none of the above resolves your issue:

1. Run `photonstrust info <resource>` for detailed information about any
   protocol, detector, or band.
2. Check the [config-reference.md](config-reference.md) for valid parameter
   ranges.
3. Look at the error's `.suggestion` attribute -- PhotonTrust errors include
   actionable fix suggestions:

   ```python
   try:
       result = simulate_qkd_link(protocol="unknown")
   except Exception as e:
       print(e)  # includes suggestion text
   ```
