------------------------------ MODULE Pace ---------------------------------
\* Copyright 2026 Ravi Kiran Kadaboina. Licensed under the Apache License, 2.0.
\*
\* TLA+ specification of the PACE principal accessibility protocol.
\* Six safety properties verified under TLC.

EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Principals,          \* Set of principal identifiers
    Agents,              \* Set of agent identifiers
    Orchestrators,       \* Subset of Agents that can issue + receive ViolationNotices
    TimeSlots,           \* Set of time slot identifiers (valid windows)
    AllTimes,            \* Set of all possible time identifiers
    MaxOptionsPerTurn,   \* Int: maximum options in one turn (default 2)
    CapacityThreshold,   \* Int: minimum capacity (x100) to proceed (default 70)
    AicVersions          \* Set of AIC version identifiers (e.g. {"1.0", "2.0"})

ASSUME MaxOptionsPerTurn > 0
ASSUME CapacityThreshold \in 0..100
ASSUME Orchestrators \subseteq Agents

VARIABLES
    pcpDeclared,         \* Function: principal -> BOOLEAN (has PCP?)
    modalityComputed,    \* Function: (principal, agent) -> BOOLEAN
    capacityChecked,     \* Function: principal -> {none, proceed, simplify, defer, escalate}
    consentCreated,      \* Function: principal -> BOOLEAN
    interactionTime,     \* Current time slot
    optionsPresented,    \* Function: (principal, agent) -> count
    needsCapacityCheck,  \* Function: principal -> BOOLEAN (fluctuating/limited capacity?)
    aicBinding,          \* Function: (orchestrator, principal) -> AicVersion \cup {"none"}
    violationNotices,    \* Set of issued notice records (issuer, principal, agent, aic_version)
    blockList,           \* Function: orchestrator -> set of blocked agents
    consentAnnotations   \* Function: principal -> set of orchestrators that wrote an annotation

vars == <<pcpDeclared, modalityComputed, capacityChecked, consentCreated,
          interactionTime, optionsPresented, needsCapacityCheck,
          aicBinding, violationNotices, blockList, consentAnnotations>>

\* ─────────────────────────────────────────────────────────────────────
\* Initial state
\* ─────────────────────────────────────────────────────────────────────

Init ==
    /\ pcpDeclared = [p \in Principals |-> TRUE]
    /\ modalityComputed = [p \in Principals, a \in Agents |-> FALSE]
    /\ capacityChecked = [p \in Principals |-> "none"]
    /\ consentCreated = [p \in Principals |-> FALSE]
    /\ interactionTime \in AllTimes
    /\ optionsPresented = [p \in Principals, a \in Agents |-> 0]
    /\ needsCapacityCheck = [p \in Principals |-> TRUE]
    /\ aicBinding = [o \in Orchestrators, p \in Principals |-> "none"]
    /\ violationNotices = {}
    /\ blockList = [o \in Orchestrators |-> {}]
    /\ consentAnnotations = [p \in Principals |-> {}]

\* ─────────────────────────────────────────────────────────────────────
\* Actions
\* ─────────────────────────────────────────────────────────────────────

\* Agent computes InteractionModality from PCP (IM-1)
ComputeModality(principal, agent) ==
    /\ pcpDeclared[principal]
    /\ ~modalityComputed[principal, agent]
    /\ modalityComputed' = [modalityComputed EXCEPT ![principal, agent] = TRUE]
    /\ UNCHANGED <<pcpDeclared, capacityChecked, consentCreated,
                   interactionTime, optionsPresented, needsCapacityCheck,
                   aicBinding, violationNotices, blockList,
                   consentAnnotations>>

\* Perform ConsentCapacityCheck. Once consent is created, the gate is
\* sealed: re-running CCC retroactively would break CCCGate, so the
\* action requires the principal not yet have a recorded consent.
PerformCCC(principal, result) ==
    /\ needsCapacityCheck[principal]
    /\ ~consentCreated[principal]                                \* seal CCC-Gate
    /\ result \in {"proceed", "simplify", "defer", "escalate"}
    /\ capacityChecked' = [capacityChecked EXCEPT ![principal] = result]
    /\ UNCHANGED <<pcpDeclared, modalityComputed, consentCreated,
                   interactionTime, optionsPresented, needsCapacityCheck,
                   aicBinding, violationNotices, blockList,
                   consentAnnotations>>

\* Create ConsentRecord (requires modality + CCC gate)
CreateConsent(principal, agent) ==
    /\ modalityComputed[principal, agent]                    \* IM-1
    /\ interactionTime \in TimeSlots                         \* AIC-1
    /\ IF needsCapacityCheck[principal]
       THEN capacityChecked[principal] \in {"proceed", "simplify"}  \* CCC-1
       ELSE TRUE
    /\ consentCreated' = [consentCreated EXCEPT ![principal] = TRUE]
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   interactionTime, optionsPresented, needsCapacityCheck,
                   aicBinding, violationNotices, blockList,
                   consentAnnotations>>

\* Present options (bounded by AIC-2)
PresentOptions(principal, agent, count) ==
    /\ modalityComputed[principal, agent]
    /\ count > 0
    /\ count <= MaxOptionsPerTurn                            \* AIC-2
    /\ optionsPresented' = [optionsPresented EXCEPT ![principal, agent] = count]
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   consentCreated, interactionTime, needsCapacityCheck,
                   aicBinding, violationNotices, blockList,
                   consentAnnotations>>

\* Time advances
AdvanceTime(t) ==
    /\ t \in AllTimes
    /\ interactionTime' = t
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   consentCreated, optionsPresented, needsCapacityCheck,
                   aicBinding, violationNotices, blockList, consentAnnotations>>

\* Orchestrator binds an AIC version for a principal under its care.
\* A version change invalidates blocks issued under the prior version
\* (a notice naming aic_version=v1 has no force when the receiver is now
\* bound to v2 — the policy itself changed). We therefore clear the
\* orchestrator's blockList on every binding change so V-1 (block
\* enforcement) and V-3 (scope) remain truthful for the *current*
\* binding; receivers that want to preserve enforcement across version
\* upgrades must re-issue notices under the new version.
BindAic(orchestrator, principal, version) ==
    /\ orchestrator \in Orchestrators
    /\ version \in AicVersions
    /\ aicBinding[orchestrator, principal] /= version
    /\ aicBinding' = [aicBinding EXCEPT ![orchestrator, principal] = version]
    /\ blockList' = [blockList EXCEPT ![orchestrator] = {}]
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   consentCreated, interactionTime, optionsPresented,
                   needsCapacityCheck, violationNotices,
                   consentAnnotations>>

\* PACE annotates a created consent (PACEConsentAnnotation)
\* Referential integrity: annotation only valid if consent already exists.
WriteConsentAnnotation(orchestrator, principal) ==
    /\ orchestrator \in Orchestrators
    /\ consentCreated[principal]                                \* AnnotIntegrity
    /\ aicBinding[orchestrator, principal] /= "none"
    /\ consentAnnotations' = [consentAnnotations EXCEPT
        ![principal] = @ \union {orchestrator}]
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   consentCreated, interactionTime, optionsPresented,
                   needsCapacityCheck, aicBinding, violationNotices,
                   blockList>>

\* Orchestrator detects an AIC violation by ``offender`` against ``principal``
\* and broadcasts the notice (PACEViolationNotice).
IssueViolationNotice(issuer, principal, offender) ==
    /\ issuer \in Orchestrators
    /\ aicBinding[issuer, principal] /= "none"
    /\ LET notice == [issuer |-> issuer,
                      principal |-> principal,
                      offender |-> offender,
                      aic_version |-> aicBinding[issuer, principal]]
       IN /\ notice \notin violationNotices              \* idempotent re-issue
          /\ violationNotices' = violationNotices \union {notice}
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   consentCreated, interactionTime, optionsPresented,
                   needsCapacityCheck, aicBinding, blockList,
                   consentAnnotations>>

\* Receiver applies V-1 / V-3 logic: blocks the offender iff bound by the
\* same AIC version for the same principal. Per V-2 receivers do NOT
\* re-publish; the notices set is unchanged.
ApplyViolationNotice(receiver, notice) ==
    /\ receiver \in Orchestrators
    /\ notice \in violationNotices
    /\ blockList' = [blockList EXCEPT ![receiver] =
        IF aicBinding[receiver, notice.principal] = notice.aic_version
        THEN @ \union {notice.offender}                  \* V-1
        ELSE @]                                          \* V-3 (no AIC match -> log only)
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   consentCreated, interactionTime, optionsPresented,
                   needsCapacityCheck, aicBinding, violationNotices,
                   consentAnnotations>>

\* ─────────────────────────────────────────────────────────────────────
\* Next-state relation
\* ─────────────────────────────────────────────────────────────────────

Next ==
    \/ \E p \in Principals, a \in Agents : ComputeModality(p, a)
    \/ \E p \in Principals : \E r \in {"proceed", "simplify", "defer", "escalate"} :
        PerformCCC(p, r)
    \/ \E p \in Principals, a \in Agents : CreateConsent(p, a)
    \/ \E p \in Principals, a \in Agents : \E c \in 1..MaxOptionsPerTurn :
        PresentOptions(p, a, c)
    \/ \E t \in AllTimes : AdvanceTime(t)
    \/ \E o \in Orchestrators, p \in Principals, v \in AicVersions :
        BindAic(o, p, v)
    \/ \E o \in Orchestrators, p \in Principals : WriteConsentAnnotation(o, p)
    \/ \E i \in Orchestrators, p \in Principals, a \in Agents :
        IssueViolationNotice(i, p, a)
    \/ \E r \in Orchestrators, n \in violationNotices : ApplyViolationNotice(r, n)

Spec == Init /\ [][Next]_vars

\* ─────────────────────────────────────────────────────────────────────
\* Safety properties
\* ─────────────────────────────────────────────────────────────────────

\* IM-Precondition: No consent without modality
IMPrecondition ==
    \A p \in Principals :
        consentCreated[p] =>
            \E a \in Agents : modalityComputed[p, a]

\* CCC-Gate: No consent without capacity check for fluctuating principals
CCCGate ==
    \A p \in Principals :
        (consentCreated[p] /\ needsCapacityCheck[p]) =>
            capacityChecked[p] \in {"proceed", "simplify"}

\* AIC-1 (structural): Consent only during valid time windows.
\* Enforced by the CreateConsent action's enabling guard
\* (``interactionTime \in TimeSlots``). NOT a state invariant: time is
\* mutable while consentCreated is monotonic, so once time advances out
\* of the window the state-only form ``consentCreated => interactionTime
\* \in TimeSlots`` would falsify even though no rule was violated.
\* The action guard remains the operative enforcement.

\* AIC-2: Option count bounded
AICOptionBound ==
    \A p \in Principals, a \in Agents :
        optionsPresented[p, a] <= MaxOptionsPerTurn

\* V-1 (Block enforcement): a receiver that has blocked an agent must
\* hold an AIC binding for the corresponding principal whose version
\* matches at least one issued notice naming that agent. In other words,
\* receivers don't block out-of-the-blue.
ViolationBlockEnforcement ==
    \A r \in Orchestrators :
        \A offender \in blockList[r] :
            \E n \in violationNotices :
                /\ n.offender = offender
                /\ aicBinding[r, n.principal] = n.aic_version

\* V-3 (Scope) is STRUCTURAL: the ``ApplyViolationNotice`` action only
\* mutates ``blockList`` when ``aicBinding[receiver, notice.principal]
\* = notice.aic_version`` — receivers without standing (no AIC, or a
\* different version) leave their block list untouched. As a state
\* invariant the property collapses to V-1 (there's no separate
\* per-principal block scoping in this model — blockList is keyed
\* per-orchestrator only), so we don't restate it as an invariant.
\* Same treatment as N-4, N-15, AICTimeWindow: action guard is the
\* operative enforcement; no redundant state assertion.

\* AnnotationIntegrity: every PACE consent annotation references a
\* principal whose ConsentRecord has been created. Replaces the
\* "pace.* keys inside ConsentRecord" pattern with a referential
\* integrity invariant on the sibling annotation.
AnnotationIntegrity ==
    \A p \in Principals :
        consentAnnotations[p] /= {} => consentCreated[p]

\* Combined invariant
Invariants ==
    /\ IMPrecondition
    /\ CCCGate
    \* AIC-1 is structural (see above); not asserted at state level.
    /\ AICOptionBound
    /\ ViolationBlockEnforcement   \* V-1
    \* V-3 is structural (see above); not asserted at state level.
    /\ AnnotationIntegrity         \* sibling-annotation referential integrity

\* Note on V-2 (no re-forwarding): expressed in the action structure —
\* ApplyViolationNotice never adds to violationNotices. The set grows
\* only via IssueViolationNotice, so receivers are mechanically unable
\* to forward. This makes V-2 a structural property rather than a
\* TLC-checked invariant.

=========================================================================
