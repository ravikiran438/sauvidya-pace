------------------------ MODULE AugmentationProfile -------------------------
\* Copyright 2026 Ravi Kiran Kadaboina. Licensed under the Apache License, 2.0.
\*
\* TLA+ specification of the active-augmentation profile extension to PACE.
\* This module adds six invariants on top of PACE Core's PCP-*, IM-*,
\* CCC-*, and AIC-* invariants:
\*
\*   AUG-1 Reversibility           : every augmentation can be reverted
\*   AUG-2 Audit Decomposition     : every action records its mediation
\*   AUG-3 Identity Preservation   : voice/style alteration requires consent
\*   AUG-4 Skill Maintenance       : no agent action on an axis declared
\*                                   preserve at the time of the action
\*   AUG-5 Emergency Boundary      : triggers force human handoff
\*   AUG-6 Task-Scoped Step-Up     : the principal may take an axis back for
\*                                   one task; agents stay off it until the
\*                                   task ends or the principal ends the
\*                                   step-up. A time limit only makes a
\*                                   nudge due; it never resumes help.
\*
\* Action records snapshot the state each invariant needs at append time
\* (axis kind, reversion, handoff, step-up), so invariants judge every
\* action by the rules in force when it happened, not by later changes.
\* The audit log is modeled as a set: every invariant quantifies over all
\* recorded actions, so order adds states without adding coverage.

EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Principals,        \* Set of principal identifiers
    AxisNames,         \* Set of augmentation axis names
    Triggers,          \* Set of declared emergency trigger names
    Tasks,             \* Set of task identifiers (A2A task ids)
    MaxActions         \* Bound on action sequence length

ASSUME MaxActions \in Nat

NoTask == "no_task"
AxisKinds == {"compensate", "amplify", "preserve"}
AgentKinds == {"compensate", "amplify"}
Mediations == {"agent_compensated", "agent_amplified",
               "user_direct", "agent_handed_off"}
AgentMediations == {"agent_compensated", "agent_amplified"}
TaskStates == {"idle", "open", "ended"}
\* "expired": the time limit passed while the task is still open. The
\* step-up still blocks agents; the principal is due a nudge.
StepUpStates == {"none", "active", "expired", "ended"}
Blocking == {"active", "expired"}

VARIABLES
    profileAxis,       \* Function: (principal, axis) -> AxisKinds \cup {"none"}
    identityConsent,   \* Function: principal -> BOOLEAN
    triggers,          \* Function: principal -> SUBSET Triggers
    activeTriggers,    \* Function: principal -> SUBSET Triggers (currently firing)
    handedOff,         \* Function: principal -> BOOLEAN
    actions,           \* Set of action records (the audit log)
    revertedAxes,      \* Function: principal -> SUBSET AxisNames
    taskState,         \* Function: task -> TaskStates
    stepUp,            \* Function: (principal, axis, task) -> StepUpStates
    nudged             \* Function: (principal, axis, task) -> BOOLEAN

pVars == <<profileAxis, identityConsent, triggers, activeTriggers,
           handedOff, actions, revertedAxes, taskState, stepUp, nudged>>

StepUpKeys == Principals \X AxisNames \X Tasks

\* ─────────────────────────────────────────────────────────────────────
\* Records
\* ─────────────────────────────────────────────────────────────────────

ActionRecord ==
    [principal: Principals,
     axis: AxisNames,
     task: Tasks \cup {NoTask},
     mediation: Mediations,
     alters_identity: BOOLEAN,
     axis_kind_at_append: AxisKinds \cup {"none"},
     axis_reverted_at_append: BOOLEAN,
     handed_off_at_append: BOOLEAN,
     stepped_up_at_append: BOOLEAN]

\* Build an action record, snapshotting the state the invariants check.
Rec(p, a, t, m, alters) ==
    [principal |-> p,
     axis |-> a,
     task |-> t,
     mediation |-> m,
     alters_identity |-> alters,
     axis_kind_at_append |-> profileAxis[<<p, a>>],
     axis_reverted_at_append |-> a \in revertedAxes[p],
     handed_off_at_append |-> handedOff[p],
     stepped_up_at_append |-> t \in Tasks /\ stepUp[<<p, a, t>>] \in Blocking]

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
    /\ taskState \in [Tasks -> TaskStates]
    /\ stepUp \in [StepUpKeys -> StepUpStates]
    /\ nudged \in [StepUpKeys -> BOOLEAN]
    /\ actions \subseteq ActionRecord
    /\ Cardinality(actions) <= MaxActions

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
    /\ actions = {}
    /\ taskState = [t \in Tasks |-> "idle"]
    /\ stepUp = [k \in StepUpKeys |-> "none"]
    /\ nudged = [k \in StepUpKeys |-> FALSE]

\* ─────────────────────────────────────────────────────────────────────
\* Profile actions
\* ─────────────────────────────────────────────────────────────────────

\* Declaring or re-declaring an axis creates a new profile version.
\* Earlier actions keep the kind they were taken under (snapshot).
DeclareAxis(p, a, k) ==
    /\ p \in Principals /\ a \in AxisNames /\ k \in AxisKinds
    /\ profileAxis' = [profileAxis EXCEPT ![<<p, a>>] = k]
    /\ UNCHANGED <<identityConsent, triggers, activeTriggers,
                   handedOff, actions, revertedAxes, taskState, stepUp, nudged>>

GrantIdentityConsent(p) ==
    /\ p \in Principals
    /\ identityConsent' = [identityConsent EXCEPT ![p] = TRUE]
    /\ UNCHANGED <<profileAxis, triggers, activeTriggers,
                   handedOff, actions, revertedAxes, taskState, stepUp, nudged>>

DeclareTrigger(p, t) ==
    /\ p \in Principals /\ t \in Triggers
    /\ triggers' = [triggers EXCEPT ![p] = @ \cup {t}]
    /\ UNCHANGED <<profileAxis, identityConsent, activeTriggers,
                   handedOff, actions, revertedAxes, taskState, stepUp, nudged>>

FireTrigger(p, t) ==
    /\ p \in Principals /\ t \in triggers[p]
    /\ Cardinality(actions) < MaxActions
    /\ activeTriggers' = [activeTriggers EXCEPT ![p] = @ \cup {t}]
    /\ handedOff' = [handedOff EXCEPT ![p] = TRUE]
    /\ actions' = actions \cup
                    {Rec(p, CHOOSE a \in AxisNames: TRUE, NoTask,
                         "agent_handed_off", FALSE)}
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, revertedAxes,
                   taskState, stepUp, nudged>>

\* Principal reverts an axis. After reversion no further compensate or
\* amplify on that axis is allowed (AUG-1).
RevertAxis(p, a) ==
    /\ p \in Principals /\ a \in AxisNames
    /\ profileAxis[<<p, a>>] # "none"
    /\ revertedAxes' = [revertedAxes EXCEPT ![p] = @ \cup {a}]
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, actions, taskState, stepUp, nudged>>

\* ─────────────────────────────────────────────────────────────────────
\* Tasks and step-up (AUG-6)
\* ─────────────────────────────────────────────────────────────────────

OpenTask(t) ==
    /\ taskState[t] = "idle"
    /\ taskState' = [taskState EXCEPT ![t] = "open"]
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, actions, revertedAxes, stepUp, nudged>>

\* The task ending closes every step-up scoped to it.
EndTask(t) ==
    /\ taskState[t] = "open"
    /\ taskState' = [taskState EXCEPT ![t] = "ended"]
    /\ stepUp' = [k \in StepUpKeys |->
                    IF k[3] = t /\ stepUp[k] \in Blocking
                    THEN "ended" ELSE stepUp[k]]
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, actions, revertedAxes, nudged>>

\* Only the principal steps up, for one axis within one open task, on an
\* axis an agent would otherwise act on.
StepUp(p, a, t) ==
    /\ taskState[t] = "open"
    /\ profileAxis[<<p, a>>] \in AgentKinds
    /\ stepUp[<<p, a, t>>] = "none"
    /\ stepUp' = [stepUp EXCEPT ![<<p, a, t>>] = "active"]
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, actions, revertedAxes, taskState, nudged>>

\* The time limit passes mid-task. The step-up keeps blocking agents.
Expire(p, a, t) ==
    /\ stepUp[<<p, a, t>>] = "active"
    /\ stepUp' = [stepUp EXCEPT ![<<p, a, t>>] = "expired"]
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, actions, revertedAxes, taskState, nudged>>

\* The agent nudges the principal about an expired step-up.
Nudge(p, a, t) ==
    /\ stepUp[<<p, a, t>>] = "expired"
    /\ ~nudged[<<p, a, t>>]
    /\ nudged' = [nudged EXCEPT ![<<p, a, t>>] = TRUE]
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, actions, revertedAxes, taskState, stepUp>>

\* The principal ends the step-up (for example, answering a nudge with
\* "go ahead and help").
PrincipalEndsStepUp(p, a, t) ==
    /\ stepUp[<<p, a, t>>] \in Blocking
    /\ stepUp' = [stepUp EXCEPT ![<<p, a, t>>] = "ended"]
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, actions, revertedAxes, taskState, nudged>>

\* ─────────────────────────────────────────────────────────────────────
\* Actions on the principal's behalf
\* ─────────────────────────────────────────────────────────────────────

\* User-direct actions are always permitted and carry no agent
\* obligations, so the model does not record them; their audit shape
\* (AUG-2) is enforced by the Python AugmentationAction type.

\* Agent compensates or amplifies on an axis within a task. Permitted iff:
\*   - axis is declared with the matching kind (AUG-4)
\*   - axis has not been reverted (AUG-1)
\*   - principal not currently handed-off (AUG-5)
\*   - if alters_identity, identity_consent must hold (AUG-3)
\*   - task is open and the principal has not stepped up on this axis
\*     in this task (AUG-6)
AgentAct(p, a, t, alters, kind, mediation) ==
    /\ p \in Principals /\ a \in AxisNames /\ alters \in BOOLEAN
    /\ taskState[t] = "open"
    /\ profileAxis[<<p, a>>] = kind
    /\ a \notin revertedAxes[p]
    /\ ~handedOff[p]
    /\ (alters => identityConsent[p])
    /\ stepUp[<<p, a, t>>] \notin Blocking
    /\ Cardinality(actions) < MaxActions
    /\ actions' = actions \cup {Rec(p, a, t, mediation, alters)}
    /\ UNCHANGED <<profileAxis, identityConsent, triggers, activeTriggers,
                   handedOff, revertedAxes, taskState, stepUp, nudged>>

AgentCompensate(p, a, t, alters) ==
    AgentAct(p, a, t, alters, "compensate", "agent_compensated")

AgentAmplify(p, a, t, alters) ==
    AgentAct(p, a, t, alters, "amplify", "agent_amplified")

Next ==
    \/ \E p \in Principals, a \in AxisNames, k \in AxisKinds:
            DeclareAxis(p, a, k)
    \/ \E p \in Principals: GrantIdentityConsent(p)
    \/ \E p \in Principals, t \in Triggers: DeclareTrigger(p, t)
    \/ \E p \in Principals, t \in Triggers: FireTrigger(p, t)
    \/ \E p \in Principals, a \in AxisNames: RevertAxis(p, a)
    \/ \E t \in Tasks: OpenTask(t) \/ EndTask(t)
    \/ \E p \in Principals, a \in AxisNames, t \in Tasks:
            \/ StepUp(p, a, t)
            \/ Expire(p, a, t)
            \/ Nudge(p, a, t)
            \/ PrincipalEndsStepUp(p, a, t)
    \/ \E p \in Principals, a \in AxisNames, t \in Tasks, alt \in BOOLEAN:
            AgentCompensate(p, a, t, alt) \/ AgentAmplify(p, a, t, alt)

\* Weak fairness on Nudge: an expired step-up cannot be ignored forever.
Spec == Init /\ [][Next]_pVars
             /\ \A p \in Principals, a \in AxisNames, t \in Tasks:
                    WF_pVars(Nudge(p, a, t))

\* ─────────────────────────────────────────────────────────────────────
\* Safety properties
\* ─────────────────────────────────────────────────────────────────────

IsAgentAction(act) == act.mediation \in AgentMediations

\* AUG-1 Reversibility: no compensate or amplify action was taken on an
\* axis that had been reverted at the time of the action.
Reversibility ==
    \A act \in actions: IsAgentAction(act) => ~act.axis_reverted_at_append

\* AUG-2 Audit Decomposition: every action carries one of the four
\* mediation values. Encoded by TypeOK already, restated here.
AuditDecomposition ==
    \A act \in actions: act.mediation \in Mediations

\* AUG-3 Identity Preservation: if an agent action alters identity,
\* identity_consent for that principal MUST hold. identityConsent is
\* never revoked in this model, so the current value is the value at
\* action time.
IdentityPreservation ==
    \A act \in actions:
        (act.alters_identity /\ IsAgentAction(act))
            => identityConsent[act.principal]

\* AUG-4 Skill Maintenance: no agent action operated on an axis whose
\* declared kind was "preserve" at the time of the action. Re-declaring
\* an axis later does not rewrite history.
SkillMaintenance ==
    \A act \in actions: IsAgentAction(act) => act.axis_kind_at_append # "preserve"

\* AUG-5 Emergency Boundary: at the time a compensate or amplify action
\* was taken, the principal had not been handed off.
EmergencyBoundary ==
    \A act \in actions: IsAgentAction(act) => ~act.handed_off_at_append

\* AUG-6a Step-Up Respected: no compensate or amplify action was taken
\* on an axis the principal had stepped up on in that task, including
\* after the time limit passed (no silent resumption).
StepUpRespected ==
    \A act \in actions: IsAgentAction(act) => ~act.stepped_up_at_append

\* AUG-6b Step-Up Closes With Task: once a task ends, no step-up scoped
\* to it is still blocking.
StepUpClosesWithTask ==
    \A k \in StepUpKeys:
        taskState[k[3]] = "ended" => stepUp[k] \notin Blocking

\* AUG-6c Step-Up Scope: a step-up is only ever open within an open task.
StepUpScope ==
    \A k \in StepUpKeys:
        stepUp[k] \in Blocking => taskState[k[3]] = "open"

\* ─────────────────────────────────────────────────────────────────────
\* Liveness
\* ─────────────────────────────────────────────────────────────────────

\* AUG-6d Nudge Due: an expired step-up leads to a nudge or to the
\* step-up ending.
NudgeDue ==
    \A k \in StepUpKeys:
        stepUp[k] = "expired" ~> (nudged[k] \/ stepUp[k] = "ended")

=============================================================================
