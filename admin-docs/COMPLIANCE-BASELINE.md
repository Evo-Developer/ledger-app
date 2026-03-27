# Compliance Baseline: PCI DSS, SOX, HIPAA

## Important
This document defines a readiness baseline and implementation controls. It is not a certification report. Formal compliance requires scoped audits, evidence collection, policies, and assessor review.

## Scope Assumptions
- Backend API and database run in Docker-based environment.
- User authentication is JWT-based.
- Financial records are stored in MySQL.
- Audit events are captured in application logs and audit tables.

## Implemented Technical Controls in This Baseline
- Security headers middleware enabled globally.
- Request size limiting middleware enabled globally.
- CORS restricted to configured origins, not wildcard.
- Password policy enforced at registration.
- Registration rate limiting enforced per source IP.
- Production guardrails for insecure defaults in auth configuration.

## PCI DSS v4.0 Readiness Matrix
| Requirement | Status | Current Control | Remaining Action |
|---|---|---|---|
| 1. Network security controls | Partial | Nginx reverse proxy and container network isolation | Add firewall policy docs and segmentation evidence |
| 2. Secure configurations | Partial | Hardened headers and secure env guidance | Add CIS benchmark evidence and config drift checks |
| 3. Protect stored account data | Gap | No explicit PAN tokenization scope defined | Do not store PAN/CVV; implement tokenization with PCI vault |
| 4. Encrypt transmission | Partial | HTTPS front door present | Enforce TLS 1.2+ everywhere and certificate rotation evidence |
| 5. Protect systems from malware | Gap | Not defined in repo | Add endpoint/runtime malware controls |
| 6. Secure systems and software | Partial | Input validation and patchable dependency pins | Add SAST/DAST/SCA pipeline gates |
| 7. Restrict access need-to-know | Partial | Role and permission model exists | Map least privilege matrix to job functions |
| 8. Identify and authenticate users | Partial | JWT auth and password policy | Add MFA for admin and privileged users |
| 9. Physical access | Out of app scope | Cloud/datacenter responsibility | Maintain provider attestation in evidence set |
| 10. Log and monitor all access | Partial | Audit trails and request tracking | Centralize immutable logs (SIEM/WORM) |
| 11. Test security regularly | Gap | No formal cadence in code | Add quarterly ASV/pentest and evidence archive |
| 12. Support with policies | Gap | Technical notes exist | Add PCI policy set and annual attestation workflow |

## SOX Readiness Matrix
| Control Area | Status | Current Control | Remaining Action |
|---|---|---|---|
| Change management | Partial | Version controlled codebase | Add ticket-linked approvals and release sign-off |
| Access management | Partial | RBAC and role checks | Add periodic access recertification |
| Segregation of duties | Gap | Not formally enforced | Split admin, deployer, reviewer roles |
| Audit trail | Partial | Audit events and request IDs | Add immutable retention and legal hold |
| Financial data integrity | Partial | Validation and business rules | Add reconciliations and exception workflows |
| Backup and recovery | Partial | Backup references exist | Test and document restore evidence quarterly |
| Control monitoring | Gap | No formal KPI/KRI control testing | Add monthly SOX control test reports |

## HIPAA Readiness Matrix
| Safeguard | Status | Current Control | Remaining Action |
|---|---|---|---|
| Administrative safeguards | Gap | Basic security docs | Add risk analysis, sanctions policy, workforce training |
| Physical safeguards | Out of app scope | Hosting provider dependent | Keep BAA and facility controls evidence |
| Technical safeguards: Access control | Partial | Auth + RBAC | Add MFA and emergency access procedure |
| Technical safeguards: Audit controls | Partial | Audit logs and request tracking | Ensure immutable, retained, searchable logs |
| Technical safeguards: Integrity | Partial | Input validation | Add tamper detection and data integrity checks |
| Technical safeguards: Transmission security | Partial | HTTPS path available | Enforce TLS-only and disable insecure endpoints |
| BAA and vendor management | Gap | Not captured in app | Execute BAAs with all PHI processors |

## Evidence Pack You Should Maintain
- Architecture and data-flow diagrams.
- Asset inventory and data classification.
- Access review reports and role assignment approvals.
- Key and secret rotation logs.
- Vulnerability scan and patch reports.
- Penetration test reports and remediation evidence.
- Backup/restore test reports.
- Incident response drills and postmortems.
- Policy acknowledgments and training completion records.

## Recommended Next Implementation Steps
1. Add MFA for admin and privileged users.
2. Move JWT to HttpOnly secure cookies for browser sessions.
3. Integrate SIEM with immutable log retention.
4. Add secrets manager integration and automatic key rotation.
5. Add CI gates: SAST, dependency audit, container image scanning.
6. Add database encryption-at-rest and key management evidence.
7. Implement formal data retention and deletion workflows.

## Runtime Baseline Settings for Production
- ENVIRONMENT=production
- ENABLE_HSTS=true
- REQUIRE_PASSWORD_COMPLEXITY=true
- MIN_PASSWORD_LENGTH=12
- MAX_REGISTRATIONS_PER_HOUR tuned to your threat model
- ALLOWED_ORIGINS set to exact production domains only

## Compliance Statement Template
Use this language in internal docs:
"The system implements a compliance readiness baseline aligned to PCI DSS, SOX, and HIPAA control families. Formal compliance status is determined through scoped assessments, policy enforcement, and independent audit evidence."
