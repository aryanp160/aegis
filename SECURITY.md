# Security Policy

We take the security of **Aegis** seriously. This document outlines our supported versions, vulnerability reporting guidelines, and responsible disclosure policy.

## Supported Versions

Only the latest active release version of Aegis is supported with security updates.

| Version | Supported |
| ------- | --------- |
| >=0.1.x | ✅ Yes     |
| <0.1.0  | ❌ No      |

## Reporting a Vulnerability

If you discover a potential security vulnerability in Aegis, please **do not** open a public issue or discuss it publicly. Instead, report it privately to the maintainers using one of the following methods:

- **GitHub Private Vulnerability Reporting**: Use the "Report a vulnerability" button under the Security tab of the repository.
- **Email**: Send details directly to `security@aegis-project.org`.

### What to Include in your Report
To help us investigate and patch the issue quickly, please include:
1. A detailed description of the vulnerability.
2. Step-by-step instructions to reproduce it (a proof of concept).
3. The impact of the vulnerability.
4. Any potential remediations or configurations that mitigate the risk.

## Responsible Disclosure Policy

Upon receiving a vulnerability report, the maintainers will:
1. Acknowledge receipt of the report within **48 hours**.
2. Investigate the issue and determine if it represents a valid vulnerability.
3. Coordinate a patch and prepare a security advisory.
4. Issue a new release containing the fix.
5. Provide public attribution for the reporter (if desired) when the advisory is published.

We ask that you give us **90 days** from the initial report to patch the vulnerability before making details public, to protect users running Aegis in production.
