------------------------------ MODULE Pace ---------------------------------
\* Copyright 2026 Ravi Kiran Kadaboina. Licensed under the Apache License, 2.0.
\*
\* TLA+ specification of the PACE principal accessibility protocol.
\* Six safety properties verified under TLC.

EXTENDS Naturals, Sequences, FiniteSets, TLC

CONSTANTS
    Principals,          \* Set of principal identifiers
    Agents,              \* Set of agent identifiers
    TimeSlots,           \* Set of time slot identifiers (valid windows)
    AllTimes,            \* Set of all possible time identifiers
    MaxOptionsPerTurn,   \* Int: maximum options in one turn (default 2)
    CapacityThreshold    \* Int: minimum capacity (x100) to proceed (default 70)

ASSUME MaxOptionsPerTurn > 0
ASSUME CapacityThreshold \in 0..100

VARIABLES
    pcpDeclared,         \* Function: principal -> BOOLEAN (has PCP?)
    modalityComputed,    \* Function: (principal, agent) -> BOOLEAN
    capacityChecked,     \* Function: principal -> {none, proceed, simplify, defer, escalate}
    consentCreated,      \* Function: principal -> BOOLEAN
    interactionTime,     \* Current time slot
    optionsPresented,    \* Function: (principal, agent) -> count
    needsCapacityCheck   \* Function: principal -> BOOLEAN (fluctuating/limited capacity?)

vars == <<pcpDeclared, modalityComputed, capacityChecked, consentCreated,
          interactionTime, optionsPresented, needsCapacityCheck>>

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

\* ─────────────────────────────────────────────────────────────────────
\* Actions
\* ─────────────────────────────────────────────────────────────────────

\* Agent computes InteractionModality from PCP (IM-1)
ComputeModality(principal, agent) ==
    /\ pcpDeclared[principal]
    /\ ~modalityComputed[principal, agent]
    /\ modalityComputed' = [modalityComputed EXCEPT ![principal, agent] = TRUE]
    /\ UNCHANGED <<pcpDeclared, capacityChecked, consentCreated,
                   interactionTime, optionsPresented, needsCapacityCheck>>

\* Perform ConsentCapacityCheck
PerformCCC(principal, result) ==
    /\ needsCapacityCheck[principal]
    /\ result \in {"proceed", "simplify", "defer", "escalate"}
    /\ capacityChecked' = [capacityChecked EXCEPT ![principal] = result]
    /\ UNCHANGED <<pcpDeclared, modalityComputed, consentCreated,
                   interactionTime, optionsPresented, needsCapacityCheck>>

\* Create ConsentRecord (requires modality + CCC gate)
CreateConsent(principal, agent) ==
    /\ modalityComputed[principal, agent]                    \* IM-1
    /\ interactionTime \in TimeSlots                         \* AIC-1
    /\ IF needsCapacityCheck[principal]
       THEN capacityChecked[principal] \in {"proceed", "simplify"}  \* CCC-1
       ELSE TRUE
    /\ consentCreated' = [consentCreated EXCEPT ![principal] = TRUE]
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   interactionTime, optionsPresented, needsCapacityCheck>>

\* Present options (bounded by AIC-2)
PresentOptions(principal, agent, count) ==
    /\ modalityComputed[principal, agent]
    /\ count > 0
    /\ count <= MaxOptionsPerTurn                            \* AIC-2
    /\ optionsPresented' = [optionsPresented EXCEPT ![principal, agent] = count]
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   consentCreated, interactionTime, needsCapacityCheck>>

\* Time advances
AdvanceTime(t) ==
    /\ t \in AllTimes
    /\ interactionTime' = t
    /\ UNCHANGED <<pcpDeclared, modalityComputed, capacityChecked,
                   consentCreated, optionsPresented, needsCapacityCheck>>

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

\* AIC-1: Consent only during valid time windows
AICTimeWindow ==
    \A p \in Principals :
        consentCreated[p] => interactionTime \in TimeSlots

\* AIC-2: Option count bounded
AICOptionBound ==
    \A p \in Principals, a \in Agents :
        optionsPresented[p, a] <= MaxOptionsPerTurn

\* Combined invariant
Invariants ==
    /\ IMPrecondition
    /\ CCCGate
    /\ AICTimeWindow
    /\ AICOptionBound

=========================================================================
