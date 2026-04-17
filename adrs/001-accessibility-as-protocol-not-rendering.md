# ADR 001: Accessibility as Protocol Concern, Not Rendering Concern

**Status:** Accepted
**Date:** 2026-04-17
**Authors:** Ravi Kiran Kadaboina

---

## Context

Accessibility standards (WCAG 2.2, WAI-ARIA 1.2) govern how content is
presented to users with disabilities: color contrast, screen reader
compatibility, keyboard navigation, text alternatives. These are
rendering-layer concerns.

Agent accessibility is a different problem. An agent decides what to
communicate, when, how much, how many options to present, how long to
wait, and whether the principal can consent at this moment. WCAG says
nothing about any of these.

A perfectly WCAG-compliant interface can still overwhelm an elder with
five options when they can process two, interrupt them during
sundowning hours, present information in English when they think in
Telugu, and accept a consent tap that the principal did not cognitively
process.

## Decision

PACE addresses accessibility at the protocol layer (agent behavior)
rather than the rendering layer (UI presentation).

## Rationale

The rendering layer cannot solve these problems because it does not
control agent behavior. WCAG can ensure a button has sufficient
contrast; it cannot ensure the agent presents at most two options, or
that it checks cognitive capacity before requesting consent, or that
it speaks Telugu instead of defaulting to English.

The protocol layer is where these decisions are made, and it is where
the constraints must be enforced.

## Consequences

- PACE and WCAG are complementary, not competing. PACE governs
  agent behavior; WCAG governs UI rendering. Both are needed.
- Agents must implement PACE invariants at the communication layer,
  not just at the presentation layer.
- The PrincipalCapabilityProfile is a communication contract, not a
  disability label.
