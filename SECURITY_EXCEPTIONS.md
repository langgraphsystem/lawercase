# Security Vulnerability Exceptions

This document tracks known security vulnerabilities that are intentionally ignored in CI/CD pipeline.

## Ignored Vulnerabilities

### GHSA-wj6h-64fc-37mp - Minerva timing attack on P-256 in python-ecdsa

- **Package**: `ecdsa` 0.19.1
- **Severity**: HIGH (CVSS 7.4)
- **CVE**: CVE-2024-23342
- **Status**: Won't be fixed by maintainers
- **Reason for ignoring**:
  - Maintainers consider side-channel attacks out of scope for python-ecdsa
  - Requires precise timing measurements to exploit
  - Only affects ECDSA signature generation, not verification
  - Our application uses this as transitive dependency via `python-jose` for JWT validation only
  - We do not use ECDSA signing in production environments
- **Mitigation**: Not applicable to our use case
- **References**:
  - https://github.com/advisories/GHSA-wj6h-64fc-37mp
  - https://github.com/mpdavis/python-jose/issues/341

### GHSA-4xh5-x5gv-qwph - pip tar extraction symlink vulnerability

- **Package**: `pip` 25.2
- **Severity**: MEDIUM
- **CVE**: CVE-2025-8869
- **Status**: Fix planned in pip 25.3
- **Reason for ignoring**:
  - Only exploitable when installing malicious source distributions
  - CI/CD uses pinned, trusted dependencies from PyPI
  - All dependencies in requirements files are from verified sources
  - pip itself is upgraded regularly in CI
- **Mitigation**:
  - Only install packages from trusted PyPI
  - Use requirements files with pinned versions
  - Regular dependency updates
- **Plan**: Remove this exception when pip 25.3+ is released
- **References**:
  - https://github.com/advisories/GHSA-4xh5-x5gv-qwph
  - https://github.com/pypa/pip/issues/13607

## Review Schedule

These exceptions should be reviewed:
- **Monthly**: Check if pip 25.3+ is available and remove GHSA-4xh5-x5gv-qwph exception
- **Quarterly**: Re-evaluate ecdsa usage and consider migration to alternative cryptography library

## Last Updated

2025-10-18
