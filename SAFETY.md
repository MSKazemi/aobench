# Safety, limitations and pre-deployment checks — aobench

**Scope:** Benchmarking permission-aware AI agents for high-performance-computing operations using evaluation scenarios.  
**Issued:** 2026-10-17  
**Status:** Risk guidance, **not** a safety certification, compliance approval, or verified representation that technical controls have been implemented.

This document is meant to help users and maintainers identify foreseeable risks and the checks **they still need to perform**. It supplements [DISCLAIMER.md](DISCLAIMER.md) and the existing software license; it does not override either or remove non-waivable duties.

## Material risks to assess

- Success on a benchmark does not establish production safety, compliance or reliable behavior against live HPC clusters.
- Fixture and scoring defects may misclassify policy violations.
- Evaluation traces, prompts and scenarios may disclose test data or system details.

## Required assessment before consequential deployment

- [ ] Verify task labels, role-policy tests and independent scoring, including explicit failure cases.
- [ ] Keep benchmark workloads isolated from real scheduling or administrative systems.
- [ ] Publish test limitations, provenance and reproducibility conditions before comparing agents.
- [ ] Do not market benchmark scores as proof of operational authorization or security.

## Operational conditions

- Start with an isolated, disposable environment and the least privileges possible.
- Do not infer that a feature claim in project documentation proves that the safeguard is effectively enforced in every execution path. Perform threat modeling and independent testing.
- Independently validate material outcomes. Preserve audit evidence, tested version, configuration, dependencies, approver identity and incident response arrangements where appropriate.
- Before exposing a networked service, inspect authentication, authorization, logging, data handling, supply chain and applicable laws.
- Pause deployment when unresolved critical flaws, missing permissions, unexplained automation, or inaccurate claims are discovered. Route security reports privately rather than disclosing exploitable details in public issues.

**Important:** Project maintainers and users remain subject to applicable mandatory safety, privacy, security and product laws. A disclaimer does not substitute for these checks or guarantee immunity from claims.
