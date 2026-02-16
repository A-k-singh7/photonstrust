# Security, Privacy, and Compliance

This document defines trust and security controls for PhotonTrust artifacts.

## Threat model
- Artifact tampering (results or card modification)
- Misconfiguration leading to invalid safety conclusions
- Leakage of sensitive lab metadata

## Security controls
- Hash all configs and key artifacts
- Optional signatures for published bundles
- Immutable run registry snapshots for release candidates

## Privacy controls
- Support metadata redaction profiles for public release
- Separate private lab metadata from public benchmark outputs

## Compliance alignment
- Scientific reproducibility best practices
- Software supply chain hygiene (dependency pinning for releases)

## Operational controls
- Release checklist includes schema and regression validation
- Artifact integrity verification in CI

## Definition of done
- Security section included in release documentation.
- Public bundles pass redaction and integrity checks.


## Inline citations (web, verified 2026-02-12)
Applied to: threat model coverage, security controls, privacy/compliance alignment, and release integrity checks.
- NIST CSF 2.0 (February 26, 2024): https://doi.org/10.6028/NIST.CSWP.29
- NIST SP 800-218 Rev.1 IPD (SSDF update): https://csrc.nist.gov/pubs/sp/800/218/r1/ipd
- SLSA v1.0 notes: https://slsa.dev/spec/v1.0/whats-new
- Sigstore cosign signature verification: https://docs.sigstore.dev/cosign/verifying/verify/
- NIST PQC FIPS announcement (FIPS 203/204/205, August 2024): https://www.nist.gov/news-events/news/2024/08/announcing-approval-three-federal-information-processing-standards-fips
- NIST SP 800-227 (KEM recommendations, September 18, 2025): https://www.nist.gov/publications/nist-special-publication-800-227-recommendations-key-encapsulation-mechanisms
- OpenSSF Best Practices Badge program: https://openssf.org/best-practices-badge/

