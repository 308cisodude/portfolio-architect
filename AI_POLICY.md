# AI-assisted development policy

Portfolio Architect is developed with substantial use of generative AI. AI may
produce implementation code, tests, documentation, review suggestions, and
release-preparation material under maintainer direction.

AI assistance does not transfer responsibility away from the maintainer. The
maintainer owns the project's architecture, security decisions, release scope,
publication decisions, and the content ultimately merged and released.

## Human-controlled workflow

Portfolio Architect does not permit autonomous publication. Creating release
branches, opening and merging pull requests, creating release tags, and deploying
releases remain explicit maintainer actions.

For architecture- or security-sensitive changes, the release process includes a
human review checkpoint covering the intended invariants, trust boundaries,
source delta, validation evidence, and live acceptance criteria. Automated tests
and AI review are evidence, not a substitute for maintainer responsibility.

This policy does not claim that every AI-assisted line is manually reviewed line
by line. Contributors must describe material AI assistance honestly and remain
responsible for the changes they submit.

## Independent AI second-opinion review

Material release candidates may additionally be reviewed by a separate AI system
that was not the primary implementation assistant. This second-opinion review is
deliberately security-focused: it prioritizes trust boundaries, authentication,
network exposure, parsing and storage safety, downgrade resistance, secret handling,
release-artifact integrity, and regressions of previously identified findings.

The secondary reviewer is expected to inspect the prepared source/release artifacts
and to state the scope and limitations of its review, including anything it could
not execute or verify directly. This is defense-in-depth review evidence, not an
independent security certification or a substitute for tests, protected workflows,
live acceptance, or maintainer judgment. The secondary AI has no merge, tagging,
publication, or deployment authority.

## Validation expectations

AI-assisted changes are subject to the same project controls as other changes,
including deterministic regression tests, Home Assistant/HACS validation where
applicable, publication-readiness checks, reproducible release builds, checksum
verification, protected-branch pull requests, and live acceptance for material
runtime changes.

Security-sensitive code must preserve Portfolio Architect's fail-closed trust
boundaries. In particular, client-side validation is never treated as an
authorization control, bank credentials remain outside the Portfolio Architect
integration, and stale or untrusted data must not silently become authorization
for a new investment action.

## Relationship to the Open Home Foundation AI policy

Portfolio Architect is an independent project and is not an Open Home Foundation
project. It therefore does **not claim compliance** with the Open Home Foundation
AI Policy. The OHF policy informs this project's approach to accountability,
human-in-the-loop development, and transparent use of AI-assisted work.

References:

- https://developers.home-assistant.io/blog/2026/07/20/ai-policy/
- https://developers.home-assistant.io/docs/ai_policy/
