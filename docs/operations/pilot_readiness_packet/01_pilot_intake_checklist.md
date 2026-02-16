# Pilot Intake Checklist (Execution-Ready)

**Customer:** ____________________  
**Pilot ID:** ____________________  
**Date:** ____________________  
**PhotonTrust owner:** ____________________

## A) Business + decision context

- [ ] Primary decision this pilot must unlock is explicit (buy / expand / no-go).
- [ ] Pilot timeline agreed (start, midpoint review, final review).
- [ ] Decision makers and technical approvers named.
- [ ] Success metric owners assigned on both sides.

## B) Technical scope lock

- [ ] Use case selected (fiber QKD / relay-family study / PIC scattering analysis).
- [ ] Protocol family selected (BB84 / BBM92 / E91 / MDI / PM / TF as applicable).
- [ ] Channel mode selected and fixed for pilot scenarios.
- [ ] Background model mode locked (`fixed` vs `radiance_proxy`) with day/night assumptions.
- [ ] Orbit-pass finite-key budgeting stance locked (enforced semantics + epsilon policy).
- [ ] Canonical satellite benchmark set selected for pilot drift governance.
- [ ] Required outputs agreed: reliability card v1.1 + summary report + artifact bundle.

## C) Input readiness

- [ ] Scenario configs provided (or customer signed off using PhotonTrust canonical presets).
- [ ] Parameter units and bounds validated (distance, wavelength, detector params, source params).
- [ ] Radiance-proxy inputs captured when used (FOV, filter bandwidth, gate/window, day/night regime, site-light proxy).
- [ ] Orbit finite-key pass inputs captured (pass duration, duty cycle, detection-probability assumption, epsilon budget fields).
- [ ] Orbit claims are explicitly finite-pass constrained (no asymptotic-only framing).
- [ ] Any customer measurement data availability confirmed (if none, mark simulation-only evidence tier).
- [ ] Security/legal constraints captured (data handling, sharing restrictions, license acceptance).

## D) Environment + reproducibility gate

- [ ] Clean environment runbook shared and accepted.
- [ ] Customer can run baseline commands or has agreed managed-run model.
- [ ] Validation harness path agreed (`results/validation` output structure).
- [ ] Artifact retention location agreed (customer-owned folder or shared evidence store).

## E) Pilot support model

- [ ] Weekly cadence fixed (ops + technical).
- [ ] Incident/escalation contacts assigned.
- [ ] SLA for blocker triage agreed (e.g., P1 response within 1 business day).
- [ ] Troubleshooting owner named for environment/setup issues.

## F) Go/No-Go to start execution

- [ ] Intake complete with no unresolved critical blocker.
- [ ] Success criteria template signed by both sides.
- [ ] Claim boundaries reviewed and accepted.

**Pilot kickoff decision:** GO / HOLD  
**If HOLD, blockers + owners + dates:**
- __________________________________________
- __________________________________________
