# QuantumCloud — Product & Engineering Specification Documents

This directory is the complete requirements specification package for
QuantumCloud, written against the already-built prototype in
`../backend` and `../frontend` so that every claim of "implemented" is
backed by a real test or a live browser verification, not an assumption.

Read in this order:

1. [PRD.md](PRD.md) — product requirements, personas, modules, MVP
   definition, functional and non-functional requirements.
2. [ARCHITECTURE.md](ARCHITECTURE.md) — component responsibilities and
   Mermaid diagrams (architecture, sequence, deployment).
3. [API_SPECIFICATION.md](API_SPECIFICATION.md) — REST contract.
4. [DATABASE_DESIGN.md](DATABASE_DESIGN.md) — schema, ER diagram, JSON
   vs. relational rationale.
5. [USER_FLOWS.md](USER_FLOWS.md) — the 4 user journeys and 9 screen
   specifications.
6. [TESTING_STRATEGY.md](TESTING_STRATEGY.md) — test plan, what's
   actually covered (33/33 passing), and what isn't yet.
7. [ROADMAP.md](ROADMAP.md) — phased releases and prioritized backlog.
8. [RISK_REGISTER.md](RISK_REGISTER.md) — risks, mitigations, open
   assumptions and decisions.
9. [REQUIREMENTS_TRACEABILITY.md](REQUIREMENTS_TRACEABILITY.md) —
   full requirement→module→API→test matrix and consistency review.

No application code was written or changed as part of producing this
package, per the brief's instruction.
