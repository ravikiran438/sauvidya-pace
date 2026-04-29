------------------------ MODULE AugmentationProfile -------------------------
\* Copyright 2026 Ravi Kiran Kadaboina. Licensed under the Apache License, 2.0.
\*
\* TLA+ specification of the active-augmentation profile extension to PACE.
\* This module adds five safety invariants on top of PACE Core's PCP-*,
\* IM-*, CCC-*, and AIC-* invariants:
\*
\*   AUG-1 Reversibility           : every augmentation can be reverted
\*   AUG-2 Audit Decomposition     : every action records its mediation
\*   AUG-3 Identity Preservation   : voice/style alteration requires consent
\*   AUG-4 Skill Maintenance       : preserve axes are never replaced
\*   AUG-5 Emergency Boundary      : triggers force human handoff

EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Principals,        \* Set of principal identifiers
    AxisNames,         \* Set of augmentation axis names
    Triggers,          \* Set of declared emergency trigger names
    MaxActions         \* Bound on action sequence length

ASSUME MaxActions \in Nat

AxisKinds == {"compensate", "amplify", "preserve"}
Mediations == {"agent_compensated", "agent_amplified",
               "user_direct", "agent_handed_off"}

VARIABLES
    profileAxis,       \* Function: (principal, axis) -> AxisKinds \cup {"none"}
    identityConsent,   \* Function: principal -> BOOLEAN
    triggers,          \* Function: principal -> SUBSET Triggers
    activeTriggers,    \* Function: principal -> SUBSET Triggers (currently firing)
    handedOff,         \* Function: principal -> BOOLEAN
    actions,           \* Sequence of action records
    revertedAxes       \* Function: principal -> SUBSET AxisNames

pVars == <<profileAxis, identityConsent, triggers, activeTriggers,
           handedOff, actions, revertedAxes>>

\* ─────────────────────────────────────────────────────────────────────
\* Records
\* ─────────────────────────────────────────────────────────────────────

ActionRecord ==
    [principal: Principals,
     axis: AxisNames,
     mediation: Mediations,
     alters_identity: BOOLEAN,
     axis_reverted_at_append: BOOLEAN,
     handed_off_at_append: BOOLEAN,
     at: Nat]

\* ─────────────────────────────────────────────────────────────────────
\* Type invariant
\* ─────────────────────────────────────────────────────────────────────

TypeOK ==
    /\ profileAxis \in [Principals \X AxisNames -> AxisKinds \cup {"none"}]
    /\ identityConsent \in [Principals -> BOOLEAN]
    /\ triggers \in [Principals -> SUBSET Triggers]
    /\ activeTriggers \in [Principals -> SUBSET Triggers]
    /\ handedOff \in [Principals -> BOOLEAN]
    /\ revertedAxes \in [Principals -> SUBSET AxisNames]
    /\ Len(actions) <= MaxActions

\* ─────────────────────────────────────────────────────────────────────
\* Initial state
\* ─────────────────────────────────────────────────────────────────────

Init ==
    /\ profileAxis = [<<p, a>> \in Principals \X AxisNames |-> "none"]
    /\ identityConsent = [p \in Principals |-> FALSE]
    /\ triggers = [p \in Principals |-> {}]
    /\ activeTriggers = [p \in Principals |-> {}]
    /\ handedOff = [p \in Principals |-> FALSE]
    /\ revertedAxes = [p \in Principals |-> {}]
    /\ actions = <<>>

\* ─────────────────────────────────────────────────────────────────────
\* Actions
\* ─────────────────────────────────────────────────────────────────────

DeclareAxis(p, a, k) ==
    /\ p \in Principals /\ a \in AxisNames /\ k \in AxisKinds
    /\ profileAxis' = [profileAxis EXCEPT ![<<p, a>>] = k]
    /\ UNCHANGED <<identityConsent, triggers, activeTriggers,
                   handedOff, actions, revertedAxes>>

GrantIdentityConsent(p) ==
    /\ p \in Principals
    /\ identityConsent' = [identityConsent EXCEPT ![p] = TRUE]
    /\ UNCHANGED <<profileAxis, triggers, activeTriggers,
                   handedOff, actions, revertedAxes>>

DeclareTrigger(p, t) ==
    /\ p \in Principals /\ t \in Triggers
    /\ triggers' = [triggers EXCEPT ![p] = @ \cup {t}]
    /\ UNCHANGED <<profileAxis, identityConsent, activeTriggers,
                   handedOff, actions, revertedAxes>>

FireTrigger(p, t) ==
    /\ p \in Principals /\ t \in triggers[p]
    /\ activeTriggers' = [activeTriggers EXCEPT ![p] = @ \cup {t}]
    /\ handedOff' = [handedOff EXCEPT ![p] = TRUE]
    /\ actions' = Append(actions, [principal |-> p,
                                     axis |-> CHOOSE a \in AxisNames: TRUE,
                                     mediation |-> "agent_handed_off",
                                     alters_identity |-> FALSE,
                                     axis_reverted_at_append |-> FALSE,
                                     handed_off_at_append |-> FALSE,
                                     at |-> Len(actions)])
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, revertedAxes>>

\* User performs an unmediated action; always permitted.
UserDirect(p, a) ==
    /\ p \in Principals /\ a \in AxisNames
    /\ Len(actions) < MaxActions
    /\ actions' = Append(actions, [principal |-> p, axis |-> a,
                                     mediation |-> "user_direct",
                                     alters_identity |-> FALSE,
                                     axis_reverted_at_append |-> a \in revertedAxes[p],
                                     handed_off_at_append |-> handedOff[p],
                                     at |-> Len(actions)])
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, revertedAxes>>

\* Agent compensates on an axis. Permitted iff:
\*   - axis is declared "compensate" (AUG-4)
\*   - axis has not been reverted (AUG-1)
\*   - principal not currently handed-off (AUG-5)
\*   - if alters_identity, identity_consent must hold (AUG-3)
\* The action record snapshots reverted/handed-off state at append time so
\* the safety invariants check the state-at-action-time, not the current
\* (monotonically growing) state.
AgentCompensate(p, a, alters) ==
    /\ p \in Principals /\ a \in AxisNames /\ alters \in BOOLEAN
    /\ profileAxis[<<p, a>>] = "compensate"
    /\ a \notin revertedAxes[p]
    /\ ~handedOff[p]
    /\ (alters => identityConsent[p])
    /\ Len(actions) < MaxActions
    /\ actions' = Append(actions, [principal |-> p, axis |-> a,
                                     mediation |-> "agent_compensated",
                                     alters_identity |-> alters,
                                     axis_reverted_at_append |-> a \in revertedAxes[p],
                                     handed_off_at_append |-> handedOff[p],
                                     at |-> Len(actions)])
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, revertedAxes>>

\* Agent amplifies on an axis. Same rules as compensate but axis must
\* be declared "amplify".
AgentAmplify(p, a, alters) ==
    /\ p \in Principals /\ a \in AxisNames /\ alters \in BOOLEAN
    /\ profileAxis[<<p, a>>] = "amplify"
    /\ a \notin revertedAxes[p]
    /\ ~handedOff[p]
    /\ (alters => identityConsent[p])
    /\ Len(actions) < MaxActions
    /\ actions' = Append(actions, [principal |-> p, axis |-> a,
                                     mediation |-> "agent_amplified",
                                     alters_identity |-> alters,
                                     axis_reverted_at_append |-> a \in revertedAxes[p],
                                     handed_off_at_append |-> handedOff[p],
                                     at |-> Len(actions)])
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, revertedAxes>>

\* Principal reverts an axis. After reversion no further compensate or
\* amplify on that axis is allowed (AUG-1).
RevertAxis(p, a) ==
    /\ p \in Principals /\ a \in AxisNames
    /\ profileAxis[<<p, a>>] # "none"
    /\ revertedAxes' = [revertedAxes EXCEPT ![p] = @ \cup {a}]
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, actions>>

Next ==
    \/ \E p \in Principals, a \in AxisNames, k \in AxisKinds:
            DeclareAxis(p, a, k)
    \/ \E p \in Principals: GrantIdentityConsent(p)
    \/ \E p \in Principals, t \in Triggers: DeclareTrigger(p, t)
    \/ \E p \in Principals, t \in Triggers: FireTrigger(p, t)
    \/ \E p \in Principals, a \in AxisNames: UserDirect(p, a)
    \/ \E p \in Principals, a \in AxisNames, alt \in BOOLEAN:
            AgentCompensate(p, a, alt)
    \/ \E p \in Principals, a \in AxisNames, alt \in BOOLEAN:
            AgentAmplify(p, a, alt)
    \/ \E p \in Principals, a \in AxisNames: RevertAxis(p, a)

Spec == Init /\ [][Next]_pVars

\* ─────────────────────────────────────────────────────────────────────
\* Safety properties
\* ─────────────────────────────────────────────────────────────────────

\* AUG-1 Reversibility: no compensate or amplify action was taken on an
\* axis that had been reverted at the time of the action. Snapshot field
\* axis_reverted_at_append captures state-at-action-time; the invariant
\* checks that snapshot rather than the current (monotonic) revertedAxes.
Reversibility ==
    \A i \in 1..Len(actions):
        LET act == actions[i]
        IN (act.mediation \in {"agent_compensated", "agent_amplified"})
              => (act.axis_reverted_at_append = FALSE)

\* AUG-2 Audit Decomposition: every action carries one of the four
\* mediation values. Encoded by TypeOK already, restated here.
AuditDecomposition ==
    \A i \in 1..Len(actions):
        actions[i].mediation \in Mediations

\* AUG-3 Identity Preservation: if an agent action alters identity,
\* identity_consent for that principal MUST hold.
IdentityPreservation ==
    \A i \in 1..Len(actions):
        LET act == actions[i]
        IN (act.alters_identity /\
             act.mediation \in {"agent_compensated", "agent_amplified"})
              => identityConsent[act.principal]

\* AUG-4 Skill Maintenance: no agent action operates on an axis whose
\* declared kind is "preserve".
SkillMaintenance ==
    \A i \in 1..Len(actions):
        LET act == actions[i]
        IN (act.mediation \in {"agent_compensated", "agent_amplified"})
              => profileAxis[<<act.principal, act.axis>>] # "preserve"

\* AUG-5 Emergency Boundary: at the time a compensate or amplify action
\* was taken, the principal had not been handed off. The snapshot field
\* handed_off_at_append captures state-at-action-time.
EmergencyBoundary ==
    \A i \in 1..Len(actions):
        LET act == actions[i]
        IN (act.mediation \in {"agent_compensated", "agent_amplified"})
              => (act.handed_off_at_append = FALSE)

=============================================================================
