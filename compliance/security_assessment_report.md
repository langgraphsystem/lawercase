# Security Assessment Report (Template)

Project: MegaAgent Pro
Date: YYYY-MM-DD
Assessor: <name>
Scope Version: <git commit or tag>

## 1. Executive Summary

- Overall risk rating: <Low | Medium | High | Critical>
- Key risks: <short list>
- Recommended actions: <short list>

## 2. Scope

In scope:
- API surface (FastAPI routes, auth, RBAC)
- Storage (PostgreSQL, Redis, object storage)
- LLM integrations and tool execution
- Observability (logs, metrics, traces)

Out of scope:
- <list items>

## 3. Methodology

- Code review (static analysis)
- Dependency scan (pip-audit, etc.)
- Configuration review (.env, secrets, RBAC policies)
- Threat modeling (STRIDE or similar)
- Sample dynamic tests (if applicable)

## 4. Findings Summary

| ID | Severity | Title | Status |
|----|----------|-------|--------|
| F-001 | <High> | <Title> | <Open/Fixed> |

## 5. Detailed Findings

### F-001: <Title>

- Severity: <Low | Medium | High | Critical>
- Impact: <short impact>
- Affected components: <files/modules>
- Evidence: <logs/paths>
- Recommendation: <action>
- Owner: <team/person>
- Target date: <YYYY-MM-DD>

## 6. Configuration Review

- RBAC policy path: <value>
- Prompt injection detection: <enabled/disabled>
- Audit trail: <enabled/disabled>
- Rate limiting: <enabled/disabled>
- CORS: <allowed origins>

## 7. Dependency Review

- python dependencies: <summary>
- known vulnerabilities: <list>
- mitigation plan: <plan>

## 8. Data Protection

- PII handling: <redaction/controls>
- Encryption at rest: <details>
- Encryption in transit: <TLS>
- Secrets management: <details>

## 9. Penetration Testing (Optional)

- Tools used: <list>
- Summary: <summary>
- Notes: <notes>

## 10. Sign-Off

- Security lead: <name>
- Engineering lead: <name>
- Date: <YYYY-MM-DD>

