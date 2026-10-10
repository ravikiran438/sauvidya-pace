#!/usr/bin/env bash
# Run every TLA+ model check for PACE.
#
#   scripts/check-models.sh [all|core|cross|augmentation|witnesses|mutants]...
#
# core, cross, augmentation: configs that MUST check clean.
# witnesses: reachability predicates that MUST be violated (non-vacuity).
# mutants:   broken copies of the model whose violation TLC MUST report.
#
# Uses $TLA2TOOLS if set; otherwise downloads the pinned tla2tools.jar into
# .tla/ and verifies its checksum. Needs Java 11+.
set -euo pipefail

TLA_VERSION="v1.8.0"
TLA_SHA256="7beec0f04818732a62fa193731711a99aa4f11279499b2360a7d156c519ea78d"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CORE_DIR="$ROOT/specification"
AUG_DIR="$ROOT/extensions/augmentation_profile"
FAILED=0
SCRATCH=()
trap 'rm -rf "${SCRATCH[@]}"' EXIT

jar() {
  if [[ -n "${TLA2TOOLS:-}" ]]; then echo "$TLA2TOOLS"; return; fi
  local path="$ROOT/.tla/tla2tools-$TLA_VERSION.jar"
  if [[ ! -f "$path" ]]; then
    mkdir -p "$ROOT/.tla"
    curl -fsSL -o "$path.tmp" \
      "https://github.com/tlaplus/tlaplus/releases/download/$TLA_VERSION/tla2tools.jar"
    echo "$TLA_SHA256  $path.tmp" | sha256sum -c --quiet -
    mv "$path.tmp" "$path"
  fi
  echo "$path"
}

# tlc <workdir> <module> <cfg> [extra TLC args...] -> prints TLC output
tlc() {
  local dir="$1" module="$2" cfg="$3"; shift 3
  (cd "$dir" && java -XX:+UseParallelGC -cp "$JAR" tlc2.TLC \
     -workers auto -cleanup "$@" -config "$cfg" "$module" 2>&1) || true
}

# Copy model files into a fresh temp dir (TLC writes state files next to
# the module). Sets SCRATCH_DIR; the dir is removed on exit.
new_scratch() {
  SCRATCH_DIR="$(mktemp -d)"
  SCRATCH+=("$SCRATCH_DIR")
  cp "$@" "$SCRATCH_DIR"/
}

expect_clean() {
  local label="$1" out="$2"
  if grep -q "No error has been found" <<<"$out"; then
    echo "ok    $label: $(grep -E 'distinct states found, 0 states left' <<<"$out" | grep -oE '[0-9,]+ distinct states found' | tail -1)"
  else
    echo "FAIL  $label: expected no errors"; grep -E "Error|violated" <<<"$out" | head -5
    FAILED=1
  fi
}

expect_violation() {
  local label="$1" pattern="$2" out="$3"
  if grep -qE "$pattern" <<<"$out"; then
    echo "ok    $label: violated as expected"
  else
    echo "FAIL  $label: expected TLC to report /$pattern/"; FAILED=1
  fi
}

check_core() {
  new_scratch "$CORE_DIR/Pace.tla" "$CORE_DIR/Pace.cfg"; local d="$SCRATCH_DIR"
  expect_clean "Pace.cfg" "$(tlc "$d" Pace Pace.cfg -deadlock)"
}

check_cross() {
  new_scratch "$CORE_DIR/Pace.tla" "$CORE_DIR/Pace-CrossOrchestrator.cfg"; local d="$SCRATCH_DIR"
  expect_clean "Pace-CrossOrchestrator.cfg" \
    "$(tlc "$d" Pace Pace-CrossOrchestrator.cfg -deadlock)"
}

check_augmentation() {
  new_scratch "$AUG_DIR"/AugmentationProfile.tla "$AUG_DIR"/AugmentationProfile*.cfg; local d="$SCRATCH_DIR"
  expect_clean "AugmentationProfile.cfg" \
    "$(tlc "$d" AugmentationProfile AugmentationProfile.cfg)"
  expect_clean "AugmentationProfile-Liveness.cfg" \
    "$(tlc "$d" AugmentationProfile AugmentationProfile-Liveness.cfg)"
}

check_witnesses() {
  local w
  new_scratch "$AUG_DIR/AugmentationProfile.tla" "$AUG_DIR/AugmentationProfileWitness.tla"
  local d="$SCRATCH_DIR"
  for w in NoAgentAction NoRedeclaredPreserveHistory NoExpiredUnnudged NoHelpAfterStepUpEnded; do
    sed -n '/^SPECIFICATION/,/^    MaxActions/p' "$AUG_DIR/AugmentationProfile.cfg" > "$d/W.cfg"
    printf 'INVARIANTS\n    %s\n' "$w" >> "$d/W.cfg"
    expect_violation "witness $w" "Invariant $w is violated" \
      "$(tlc "$d" AugmentationProfileWitness W.cfg)"
  done
}

# mutate <label> <cfg> <expected pattern> <sed expression>
mutate() {
  local label="$1" cfg="$2" pattern="$3" expr="$4"
  new_scratch "$AUG_DIR/AugmentationProfile.tla" "$AUG_DIR/$cfg"
  local d="$SCRATCH_DIR"
  sed -i "$expr" "$d/AugmentationProfile.tla"
  if cmp -s "$d/AugmentationProfile.tla" "$AUG_DIR/AugmentationProfile.tla"; then
    echo "FAIL  mutant $label: sed changed nothing; update the mutation"; FAILED=1; return
  fi
  expect_violation "mutant $label" "$pattern" "$(tlc "$d" AugmentationProfile "$cfg")"
}

check_mutants() {
  mutate "no step-up guard" AugmentationProfile.cfg \
    "Invariant StepUpRespected is violated" \
    '/^    \/\\ stepUp\[<<p, a, t>>\] \\notin Blocking$/d'
  mutate "no nudge fairness" AugmentationProfile-Liveness.cfg \
    "Temporal property NudgeDue was violated" \
    's/WF_pVars(Nudge(p, a, t))/TRUE/'
}

JAR="$(jar)"
targets=("$@"); [[ ${#targets[@]} -eq 0 ]] && targets=(all)
for t in "${targets[@]}"; do
  case "$t" in
    all) check_core; check_augmentation; check_witnesses; check_mutants; check_cross ;;
    core|cross|augmentation|witnesses|mutants) "check_$t" ;;
    *) echo "unknown target: $t" >&2; exit 2 ;;
  esac
done
exit "$FAILED"
