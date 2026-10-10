--------------------- MODULE AugmentationProfileWitness ---------------------
\* Copyright 2026 Ravi Kiran Kadaboina. Licensed under the Apache License, 2.0.
\*
\* Reachability witnesses for AugmentationProfile.tla. Each predicate below
\* is EXPECTED to be violated: TLC finding a violation proves the scenario
\* is reachable, so the safety invariants are not passing vacuously.
\* Run by scripts/check-models.sh.

EXTENDS AugmentationProfile

\* Agents can act at all.
NoAgentAction == ~\E act \in actions: IsAgentAction(act)

\* The history that used to violate AUG-4: help given while the axis was
\* compensate, then the axis re-declared preserve.
NoRedeclaredPreserveHistory == ~\E act \in actions:
    /\ act.mediation = "agent_compensated"
    /\ profileAxis[<<act.principal, act.axis>>] = "preserve"

\* A step-up can pass its time limit before the nudge.
NoExpiredUnnudged == ~\E k \in StepUpKeys: stepUp[k] = "expired" /\ ~nudged[k]

\* Help resumes in a still-open task once the principal ends the step-up.
NoHelpAfterStepUpEnded == ~\E act \in actions, k \in StepUpKeys:
    /\ IsAgentAction(act)
    /\ act.task = k[3]
    /\ act.axis = k[2]
    /\ stepUp[k] = "ended"
    /\ taskState[k[3]] = "open"

=============================================================================
