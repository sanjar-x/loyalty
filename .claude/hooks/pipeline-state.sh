#!/bin/bash
# .claude/hooks/pipeline-state.sh
# State manager for 10-agent PRD → Implementation pipeline
# Works with Git Bash on Windows (ships with Claude Code)
#
# v2 CHANGELOG:
#   FIX: Python detection — python3 first, then python (was python twice)
#   FIX: ARTIFACTS map — correct per-MT paths for agents 7–10
#   FIX: INPUTS map — correct dependencies for agents 7–10
#   FIX: Loop agents (7–10) no longer expect a single static artifact
#   FIX: resume scans arch/, review/, qa-tests/ for MT progress
#   FIX: Pipeline completion message shows correct paths
#   FIX: Python errors logged to .claude/hooks/error.log instead of /dev/null
#   NEW: Micro-task tracking — init-mt, start-mt, complete-mt, block-mt, mt-status, resume-mt
#   NEW: status shows MT progress when in implementation phase
#   NEW: next shows MT-level next action for loop agents

PIPELINE_DIR=".claude/pipeline-runs"
STATE_FILE="$PIPELINE_DIR/current/state.json"
ARTIFACTS_DIR="$PIPELINE_DIR/current/artifacts"
LOG_FILE=".claude/hooks/error.log"

# --- FIX: was `python || python`, now `python3 || python` ---
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$PYTHON" ]; then
  echo "ERROR: Python не найден. Установи Python 3 с python.org" >&2
  exit 1
fi

# Ensure log directory exists once at script start
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null

log_error() {
  local msg="$1"
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
  echo "[$ts] $msg" >> "$LOG_FILE" 2>/dev/null
  echo "ERROR: $msg" >&2
}

# Full pipeline: 10 agents in order
STEPS=(
  "context-analyst"
  "competitive-intel"
  "gap-analysis"
  "prd-writer"
  "review-qa"
  "senior-pm"
  "senior-architect"
  "senior-backend"
  "senior-reviewer"
  "senior-qa"
)

# Agents that run per-MT inside the implementation loop (7–10)
LOOP_AGENTS="senior-architect senior-backend senior-reviewer senior-qa"

is_loop_agent() {
  [[ " $LOOP_AGENTS " == *" $1 "* ]]
}

# --- FIX: correct artifact names for agents 7–10 ---
declare -A ARTIFACTS
ARTIFACTS=(
  [context-analyst]="context-brief.json"
  [competitive-intel]="competitive-report.json"
  [gap-analysis]="enhancement-plan.json"
  [prd-writer]="prd.md"
  [review-qa]="qa-report.json"
  [senior-pm]="pm-spec.md"
  [senior-architect]="arch/MT-{N}-plan.md"
  [senior-backend]="(code files per MT)"
  [senior-reviewer]="review/MT-{N}-review.md"
  [senior-qa]="qa-tests/MT-{N}-qa.md"
)

# --- FIX: correct input deps for agents 7–10 ---
declare -A INPUTS
INPUTS=(
  [context-analyst]=""
  [competitive-intel]="context-brief.json"
  [gap-analysis]="context-brief.json,competitive-report.json"
  [prd-writer]="context-brief.json,competitive-report.json,enhancement-plan.json"
  [review-qa]="prd.md,context-brief.json,competitive-report.json,enhancement-plan.json"
  [senior-pm]="prd.md,qa-report.json"
  [senior-architect]="prd.md,pm-spec.md"
  [senior-backend]="prd.md,pm-spec.md"
  [senior-reviewer]="prd.md,pm-spec.md"
  [senior-qa]="prd.md,pm-spec.md"
)

ensure_dirs() {
  mkdir -p "$PIPELINE_DIR/current/artifacts/arch" 2>/dev/null
  mkdir -p "$PIPELINE_DIR/current/artifacts/review" 2>/dev/null
  mkdir -p "$PIPELINE_DIR/current/artifacts/qa-tests" 2>/dev/null
  mkdir -p "$PIPELINE_DIR/archive" 2>/dev/null
}

get_step_index() {
  local agent="$1"
  for i in "${!STEPS[@]}"; do
    if [ "${STEPS[$i]}" = "$agent" ]; then
      echo "$i"
      return
    fi
  done
  echo "-1"
}

# ═══════════════════════════════════════════════════════════
#  init — Initialize a new pipeline run
# ═══════════════════════════════════════════════════════════

init_pipeline() {
  local topic="$1"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
  local run_id
  run_id=$(date +"%Y%m%d-%H%M%S")

  ensure_dirs

  # Archive previous run if exists
  if [ -f "$STATE_FILE" ]; then
    local prev_id
    prev_id=$(cat "$STATE_FILE" | grep -o '"run_id"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*"run_id"[[:space:]]*:[[:space:]]*"\([^"]*\)"/\1/')
    if [ -n "$prev_id" ] && [ "$prev_id" != "null" ]; then
      cp -r "$PIPELINE_DIR/current" "$PIPELINE_DIR/archive/$prev_id" 2>/dev/null
    fi
    rm -rf "$PIPELINE_DIR/current"
    ensure_dirs
  fi

  # Build steps JSON
  local steps_json="{"
  for i in "${!STEPS[@]}"; do
    local agent="${STEPS[$i]}"
    local artifact="${ARTIFACTS[$agent]}"
    [ "$i" -gt 0 ] && steps_json="$steps_json,"
    steps_json="$steps_json \"$agent\": {\"status\":\"pending\",\"artifact\":\"$artifact\",\"started_at\":null,\"completed_at\":null}"
  done
  steps_json="$steps_json }"

  cat > "$STATE_FILE" << STATEEOF
{
  "run_id": "$run_id",
  "topic": $(printf '%s' "$topic" | "$PYTHON" -c "import sys,json; print(json.dumps(sys.stdin.read()))" 2>/dev/null || echo "\"$topic\""),
  "created_at": "$timestamp",
  "updated_at": "$timestamp",
  "current_step": 0,
  "status": "initialized",
  "pipeline_type": "prd-to-implementation",
  "total_steps": ${#STEPS[@]},
  "steps": $steps_json,
  "micro_tasks": {
    "total": 0,
    "current_mt": 0,
    "tasks": {}
  }
}
STATEEOF

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  PIPELINE INITIALIZED"
  echo "═══════════════════════════════════════════════════════════"
  echo "  Run ID:  $run_id"
  echo "  Topic:   $topic"
  echo "  Steps:   ${#STEPS[@]}"
  echo "  Artifacts: $ARTIFACTS_DIR/"
  echo ""
  echo "  NEXT: Use the context-analyst subagent on this topic:"
  echo "  $topic"
  echo "═══════════════════════════════════════════════════════════"
}

# ═══════════════════════════════════════════════════════════
#  start — Mark a PRD-phase agent as started
# ═══════════════════════════════════════════════════════════

mark_started() {
  local agent="$1"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

  if [ ! -f "$STATE_FILE" ]; then
    log_error "No active pipeline. Run: bash .claude/hooks/pipeline-state.sh init \"topic\""
    return 1
  fi

  # Check input dependencies
  local inputs="${INPUTS[$agent]}"
  if [ -n "$inputs" ]; then
    IFS=',' read -ra INPUT_FILES <<< "$inputs"
    for f in "${INPUT_FILES[@]}"; do
      if [ ! -f "$ARTIFACTS_DIR/$f" ]; then
        echo ""
        echo "═══ PIPELINE ERROR ═══"
        echo "❌ $agent CANNOT START"
        echo "Missing input: $ARTIFACTS_DIR/$f"
        echo ""
        for a in "${!ARTIFACTS[@]}"; do
          if [ "${ARTIFACTS[$a]}" = "$f" ]; then
            echo "FIX: Run the $a subagent first."
            break
          fi
        done
        echo "═══════════════════════"
        log_error "$agent cannot start: missing $ARTIFACTS_DIR/$f"
        return 1
      fi
    done
  fi

  "$PYTHON" -c "
import json, sys
try:
    with open('$STATE_FILE','r') as f: state=json.load(f)
    state['steps']['$agent']['status']='running'
    state['steps']['$agent']['started_at']='$timestamp'
    state['updated_at']='$timestamp'
    state['status']='running'
    with open('$STATE_FILE','w') as f: json.dump(state,f,indent=2)
except Exception as e:
    print(f'ERROR updating state: {e}', file=sys.stderr)
    sys.exit(1)
" 2>>"$LOG_FILE"

  echo "[PIPELINE] $agent started"
}

# ═══════════════════════════════════════════════════════════
#  complete — Mark a PRD-phase agent as completed
# ═══════════════════════════════════════════════════════════

mark_complete() {
  local agent="$1"
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

  if [ ! -f "$STATE_FILE" ]; then
    log_error "No active pipeline."
    return 1
  fi

  local step_idx
  step_idx=$(get_step_index "$agent")
  local next_step=$((step_idx + 1))

  # Only check artifact for PRD-phase agents (not loop agents)
  if ! is_loop_agent "$agent"; then
    local artifact_name="${ARTIFACTS[$agent]}"
    local artifact_path="$ARTIFACTS_DIR/$artifact_name"
    if [ ! -f "$artifact_path" ]; then
      echo "⚠️  WARNING: Expected artifact not found: $artifact_path"
      log_error "Artifact missing for $agent: $artifact_path"
    fi
  fi

  "$PYTHON" -c "
import json, sys
try:
    with open('$STATE_FILE','r') as f: state=json.load(f)
    state['steps']['$agent']['status']='completed'
    state['steps']['$agent']['completed_at']='$timestamp'
    state['current_step']=$next_step
    state['updated_at']='$timestamp'
    state['status']='completed' if $next_step >= ${#STEPS[@]} else 'waiting_for_next'
    with open('$STATE_FILE','w') as f: json.dump(state,f,indent=2)
except Exception as e:
    print(f'ERROR updating state: {e}', file=sys.stderr)
    sys.exit(1)
" 2>>"$LOG_FILE"

  if [ "$next_step" -ge "${#STEPS[@]}" ]; then
    echo ""
    echo "═══════════════════════════════════════════════════════════"
    echo "  ✅ PIPELINE COMPLETED — all ${#STEPS[@]} agents finished"
    echo "═══════════════════════════════════════════════════════════"
    echo "  PRD:      $ARTIFACTS_DIR/prd.md"
    echo "  QA:       $ARTIFACTS_DIR/qa-report.json"
    echo "  PM Spec:  $ARTIFACTS_DIR/pm-spec.md"
    echo "  Plans:    $ARTIFACTS_DIR/arch/"
    echo "  Reviews:  $ARTIFACTS_DIR/review/"
    echo "  Tests:    $ARTIFACTS_DIR/qa-tests/"
    echo "═══════════════════════════════════════════════════════════"
  else
    print_next
  fi
}

# ═══════════════════════════════════════════════════════════
#  init-mt — Register micro-tasks after senior-pm completes
#  Usage: bash pipeline-state.sh init-mt <total_count>
# ═══════════════════════════════════════════════════════════

init_micro_tasks() {
  local total="$1"

  if [ ! -f "$STATE_FILE" ]; then
    log_error "No active pipeline."
    return 1
  fi

  if [ -z "$total" ] || [ "$total" -lt 1 ]; then
    echo "Usage: $0 init-mt <total_mt_count>"
    return 1
  fi

  "$PYTHON" -c "
import json, sys
try:
    with open('$STATE_FILE','r') as f: state=json.load(f)
    total = $total
    state['micro_tasks'] = {
        'total': total,
        'current_mt': 1,
        'tasks': {}
    }
    for i in range(1, total + 1):
        state['micro_tasks']['tasks'][f'MT-{i}'] = {
            'status': 'pending',
            'senior-architect': 'pending',
            'senior-backend': 'pending',
            'senior-reviewer': 'pending',
            'senior-qa': 'pending'
        }
    ts = '$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")'
    state['updated_at'] = ts
    with open('$STATE_FILE','w') as f: json.dump(state,f,indent=2)
    print(f'  Registered {total} micro-tasks (MT-1 .. MT-{total})')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" 2>>"$LOG_FILE"
}

# ═══════════════════════════════════════════════════════════
#  start-mt — Mark agent started for a specific MT
#  Usage: bash pipeline-state.sh start-mt <N> <agent>
# ═══════════════════════════════════════════════════════════

start_micro_task() {
  local mt_num="$1"
  local agent="$2"

  if [ ! -f "$STATE_FILE" ]; then log_error "No active pipeline."; return 1; fi
  if [ -z "$mt_num" ] || [ -z "$agent" ]; then
    echo "Usage: $0 start-mt <N> <agent>"
    echo "  Agents: senior-architect | senior-backend | senior-reviewer | senior-qa"
    return 1
  fi

  # MT-level dependency checks
  case "$agent" in
    senior-backend)
      if [ ! -f "$ARTIFACTS_DIR/arch/MT-${mt_num}-plan.md" ]; then
        echo "❌ $agent cannot start MT-${mt_num}: missing arch/MT-${mt_num}-plan.md"
        echo "FIX: Run senior-architect for MT-${mt_num} first."
        return 1
      fi ;;
    senior-reviewer)
      local bs
      bs=$("$PYTHON" -c "
import json
with open('$STATE_FILE') as f: s=json.load(f)
print(s.get('micro_tasks',{}).get('tasks',{}).get('MT-$mt_num',{}).get('senior-backend','pending'))
" 2>/dev/null)
      if [ "$bs" != "completed" ]; then
        echo "❌ $agent cannot start MT-${mt_num}: senior-backend not completed (status: $bs)"
        return 1
      fi ;;
    senior-qa)
      if [ ! -f "$ARTIFACTS_DIR/review/MT-${mt_num}-review.md" ]; then
        echo "❌ $agent cannot start MT-${mt_num}: missing review/MT-${mt_num}-review.md"
        echo "FIX: Run senior-reviewer for MT-${mt_num} first."
        return 1
      fi ;;
  esac

  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

  "$PYTHON" -c "
import json, sys
try:
    with open('$STATE_FILE','r') as f: state=json.load(f)
    mk = 'MT-$mt_num'
    mt = state.get('micro_tasks',{}).get('tasks',{})
    if mk not in mt:
        print(f'ERROR: {mk} not registered. Run init-mt first.', file=sys.stderr); sys.exit(1)
    mt[mk]['$agent'] = 'running'
    mt[mk]['status'] = 'in_progress'
    state['micro_tasks']['current_mt'] = $mt_num
    state['updated_at'] = '$timestamp'
    with open('$STATE_FILE','w') as f: json.dump(state,f,indent=2)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)
" 2>>"$LOG_FILE"

  echo "[MT-${mt_num}] $agent started"
}

# ═══════════════════════════════════════════════════════════
#  complete-mt — Mark agent completed for a specific MT
#  Usage: bash pipeline-state.sh complete-mt <N> <agent>
# ═══════════════════════════════════════════════════════════

complete_micro_task() {
  local mt_num="$1"
  local agent="$2"

  if [ ! -f "$STATE_FILE" ]; then log_error "No active pipeline."; return 1; fi
  if [ -z "$mt_num" ] || [ -z "$agent" ]; then
    echo "Usage: $0 complete-mt <N> <agent>"; return 1
  fi

  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

  "$PYTHON" -c "
import json, sys
try:
    with open('$STATE_FILE','r') as f: state=json.load(f)
    mk = 'MT-$mt_num'
    tasks = state.get('micro_tasks',{}).get('tasks',{})
    if mk not in tasks:
        print(f'ERROR: {mk} not registered.', file=sys.stderr); sys.exit(1)

    mt = tasks[mk]
    mt['$agent'] = 'completed'

    # Check if all 4 loop agents completed for this MT
    loop = ['senior-architect','senior-backend','senior-reviewer','senior-qa']
    all_done = all(mt.get(a) == 'completed' for a in loop)
    if all_done:
        mt['status'] = 'completed'
        # Advance to next pending MT
        total = state['micro_tasks']['total']
        nxt = $mt_num + 1
        while nxt <= total:
            if tasks.get(f'MT-{nxt}',{}).get('status') != 'completed':
                break
            nxt += 1
        state['micro_tasks']['current_mt'] = nxt

        # If all MTs done, mark pipeline complete
        if nxt > total:
            for a in loop:
                state['steps'][a]['status'] = 'completed'
                state['steps'][a]['completed_at'] = '$timestamp'
            state['current_step'] = 10
            state['status'] = 'completed'

    state['updated_at'] = '$timestamp'
    with open('$STATE_FILE','w') as f: json.dump(state,f,indent=2)

    if all_done:
        completed = sum(1 for t in tasks.values() if t.get('status')=='completed')
        total = state['micro_tasks']['total']
        print(f'  MT-$mt_num COMPLETE  ({completed}/{total} done)')
        if nxt > total:
            print()
            print('═══════════════════════════════════════════════════════════')
            print('  ALL MICRO-TASKS COMPLETE — Pipeline finished!')
            print('═══════════════════════════════════════════════════════════')
        else:
            print(f'  NEXT -> MT-{nxt}')
    else:
        done = [a.replace('senior-','') for a in loop if mt.get(a)=='completed']
        pend = [a.replace('senior-','') for a in loop if mt.get(a)!='completed']
        print(f'[MT-$mt_num] $agent done  (ok: {\", \".join(done)} | next: {\", \".join(pend)})')

except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)
" 2>>"$LOG_FILE"
}

# ═══════════════════════════════════════════════════════════
#  block-mt — Mark MT as blocked (reviewer/QA sends back)
#  Usage: bash pipeline-state.sh block-mt <N> <blocking_agent>
# ═══════════════════════════════════════════════════════════

block_micro_task() {
  local mt_num="$1"
  local blocker="$2"

  if [ ! -f "$STATE_FILE" ]; then log_error "No active pipeline."; return 1; fi

  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")

  "$PYTHON" -c "
import json, sys
try:
    with open('$STATE_FILE','r') as f: state=json.load(f)
    mk = 'MT-$mt_num'
    mt = state['micro_tasks']['tasks'][mk]
    mt['status'] = 'blocked'
    mt['senior-backend'] = 'needs_fix'
    if '$blocker' == 'senior-reviewer':
        mt['senior-reviewer'] = 'blocked'
        mt['senior-qa'] = 'pending'
    elif '$blocker' == 'senior-qa':
        mt['senior-qa'] = 'blocked'
    state['updated_at'] = '$timestamp'
    with open('$STATE_FILE','w') as f: json.dump(state,f,indent=2)
    print(f'  MT-$mt_num BLOCKED by $blocker -> senior-backend must fix')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr); sys.exit(1)
" 2>>"$LOG_FILE"
}

# ═══════════════════════════════════════════════════════════
#  mt-status — Show micro-task progress table
# ═══════════════════════════════════════════════════════════

print_mt_status() {
  if [ ! -f "$STATE_FILE" ]; then echo "No active pipeline."; return 1; fi

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  MICRO-TASK PROGRESS"
  echo "═══════════════════════════════════════════════════════════"

  "$PYTHON" -c "
import json
with open('$STATE_FILE') as f: s=json.load(f)
mt_data = s.get('micro_tasks', {})
total = mt_data.get('total', 0)
current = mt_data.get('current_mt', 0)
tasks = mt_data.get('tasks', {})

if total == 0:
    print('  No micro-tasks registered. Run: init-mt <count>')
    exit(0)

icons = {
    'completed': 'OK', 'running': '..', 'pending': '--',
    'blocked': 'BL', 'needs_fix': 'FX', 'in_progress': '..'
}

completed = sum(1 for t in tasks.values() if t.get('status')=='completed')
print(f'  {completed}/{total} completed   current: MT-{current}')
print()
print(f'  {\"MT\":<7s}  arch  back  rev   qa    status')
print(f'  -------  ----  ----  ----  ----  ----------')

for i in range(1, total+1):
    k = f'MT-{i}'
    t = tasks.get(k, {})
    st = t.get('status','pending')
    cols = []
    for a in ['senior-architect','senior-backend','senior-reviewer','senior-qa']:
        cols.append(icons.get(t.get(a,'pending'),'??'))
    marker = '  <-' if i == current and st != 'completed' else ''
    print(f'  {k:<7s}  {cols[0]:<4s}  {cols[1]:<4s}  {cols[2]:<4s}  {cols[3]:<4s}  {st}{marker}')
" 2>/dev/null

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  OK=completed  ..=running  --=pending  BL=blocked  FX=needs_fix"
  echo "═══════════════════════════════════════════════════════════"
}

# ═══════════════════════════════════════════════════════════
#  next — Print next action (PRD-phase or MT-level)
# ═══════════════════════════════════════════════════════════

print_next() {
  if [ ! -f "$STATE_FILE" ]; then echo "No active pipeline."; return 1; fi

  local current_step
  current_step=$("$PYTHON" -c "import json; print(json.load(open('$STATE_FILE'))['current_step'])" 2>/dev/null)

  if [ -z "$current_step" ] || [ "$current_step" -ge "${#STEPS[@]}" ]; then
    echo "Pipeline completed or invalid state."
    return 0
  fi

  local next_agent="${STEPS[$current_step]}"

  # For loop agents, delegate to MT-level next
  if is_loop_agent "$next_agent"; then
    print_mt_next
    return
  fi

  local next_artifact="${ARTIFACTS[$next_agent]}"
  local inputs="${INPUTS[$next_agent]}"

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  NEXT: $next_agent (step $((current_step + 1))/${#STEPS[@]})"
  echo "═══════════════════════════════════════════════════════════"
  echo ""
  echo "  Use the $next_agent subagent."

  if [ -n "$inputs" ]; then
    IFS=',' read -ra INPUT_FILES <<< "$inputs"
    for f in "${INPUT_FILES[@]}"; do
      echo "  Read: $ARTIFACTS_DIR/$f"
    done
  fi

  echo "  Save output to: $ARTIFACTS_DIR/$next_artifact"
  echo ""
  echo "═══════════════════════════════════════════════════════════"
}

print_mt_next() {
  "$PYTHON" -c "
import json
with open('$STATE_FILE') as f: s=json.load(f)
mt_data = s.get('micro_tasks', {})
total = mt_data.get('total', 0)
current = mt_data.get('current_mt', 0)
tasks = mt_data.get('tasks', {})

if total == 0 or current > total:
    print('  All micro-tasks completed (or none registered).')
    exit(0)

mk = f'MT-{current}'
mt = tasks.get(mk, {})

order = ['senior-architect','senior-backend','senior-reviewer','senior-qa']
nxt = None
for a in order:
    st = mt.get(a, 'pending')
    if st in ('pending', 'needs_fix', 'blocked'):
        nxt = a
        break

if not nxt:
    print(f'  MT-{current} fully completed. Run: resume to advance.')
    exit(0)

arts = '$ARTIFACTS_DIR'
print()
print('=' * 59)
print(f'  NEXT: {nxt} for MT-{current} ({current}/{total})')
print('=' * 59)
print()
print(f'  Use the {nxt} subagent.')
print(f'  Task: \"Process MT-{current}\"')
print(f'  Read: {arts}/pm-spec.md')

if nxt == 'senior-backend':
    print(f'  Read plan: {arts}/arch/MT-{current}-plan.md')
elif nxt in ('senior-reviewer', 'senior-qa'):
    print(f'  Read plan: {arts}/arch/MT-{current}-plan.md')
if nxt == 'senior-qa':
    print(f'  Read review: {arts}/review/MT-{current}-review.md')
if mt.get(nxt) == 'needs_fix':
    print(f'  !! FIX MODE — read review/qa feedback first')
print()
print('=' * 59)
" 2>/dev/null
}

# ═══════════════════════════════════════════════════════════
#  status — Full pipeline status (PRD + MT)
# ═══════════════════════════════════════════════════════════

print_status() {
  if [ ! -f "$STATE_FILE" ]; then
    echo "No active pipeline. Run: bash .claude/hooks/pipeline-state.sh init \"topic\""
    return 0
  fi

  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "  PRD -> IMPLEMENTATION PIPELINE"
  echo "═══════════════════════════════════════════════════════════"

  "$PYTHON" -c "
import json
with open('$STATE_FILE') as f: s=json.load(f)
print(f\"  Run:     {s['run_id']}\")
print(f\"  Topic:   {s['topic']}\")
print(f\"  Status:  {s['status']}\")
print()

icons={'completed':'[OK]','running':'[..]','pending':'[  ]','failed':'[!!]','waiting_for_next':'[OK]'}
steps=['context-analyst','competitive-intel','gap-analysis','prd-writer','review-qa',
       'senior-pm','senior-architect','senior-backend','senior-reviewer','senior-qa']
phases={0:'  -- PRD Phase --',5:'  -- Implementation Phase --'}

for i,agent in enumerate(steps):
    if i in phases: print(phases[i])
    if agent not in s['steps']: continue
    st = s['steps'][agent]
    icon = icons.get(st['status'],'[??]')
    artifact = st.get('artifact','')
    line = f\"  {icon} {i+1:2d}. {agent:<22s}\"
    if st['status']=='completed' and artifact:
        line += f' -> {artifact}'
    elif st['status'] != 'pending':
        line += f' ({st[\"status\"]})'
    print(line)

mt_data = s.get('micro_tasks', {})
total = mt_data.get('total', 0)
if total > 0:
    tasks = mt_data.get('tasks', {})
    done = sum(1 for t in tasks.values() if t.get('status')=='completed')
    cur = mt_data.get('current_mt', 0)
    print()
    print(f'  -- Micro-tasks: {done}/{total} completed --')
    if cur <= total:
        print(f'  Current: MT-{cur}')
    print(f'  Details: bash .claude/hooks/pipeline-state.sh mt-status')
" 2>/dev/null

  echo ""
  echo "═══════════════════════════════════════════════════════════"
}

# ═══════════════════════════════════════════════════════════
#  resume — Scan artifacts, fix state, find resume point
# ═══════════════════════════════════════════════════════════

find_resume() {
  if [ ! -f "$STATE_FILE" ]; then
    echo "No active pipeline to resume."
    return 1
  fi

  echo "Scanning artifacts for resume point..."
  echo ""

  # Phase 1: PRD agents (1–6)
  for i in 0 1 2 3 4 5; do
    local agent="${STEPS[$i]}"
    local artifact="${ARTIFACTS[$agent]}"
    local path="$ARTIFACTS_DIR/$artifact"

    if [ -f "$path" ]; then
      local status
      status=$("$PYTHON" -c "import json; print(json.load(open('$STATE_FILE'))['steps']['$agent']['status'])" 2>/dev/null)
      if [ "$status" != "completed" ]; then
        echo "  Found $artifact (was $status -> fixing to completed)"
        mark_complete "$agent" > /dev/null
      fi
    else
      echo "  Resume from: $agent (step $((i + 1)))"
      "$PYTHON" -c "
import json
with open('$STATE_FILE','r') as f: state=json.load(f)
state['current_step']=$i
state['status']='waiting_for_next'
with open('$STATE_FILE','w') as f: json.dump(state,f,indent=2)
" 2>/dev/null
      print_next
      return 0
    fi
  done

  echo "  PRD phase complete. Checking micro-task progress..."

  # Phase 2: Initialize MT tracking if needed
  local mt_total
  mt_total=$("$PYTHON" -c "import json; print(json.load(open('$STATE_FILE')).get('micro_tasks',{}).get('total',0))" 2>/dev/null)

  if [ "$mt_total" = "0" ] || [ -z "$mt_total" ]; then
    if [ -f "$ARTIFACTS_DIR/pm-spec.md" ]; then
      local counted
      counted=$(grep -c "^## Micro-Task" "$ARTIFACTS_DIR/pm-spec.md" 2>/dev/null)
      if [ -n "$counted" ] && [ "$counted" -gt 0 ]; then
        echo "  Found $counted micro-tasks in pm-spec.md, initializing..."
        init_micro_tasks "$counted"
        mt_total="$counted"
      fi
    fi
  fi

  if [ "$mt_total" = "0" ] || [ -z "$mt_total" ]; then
    echo "  No micro-tasks found. Run senior-pm first."
    return 0
  fi

  # Phase 3: Scan arch/, review/, qa-tests/ to reconcile state
  "$PYTHON" -c "
import json, os

arts = '$ARTIFACTS_DIR'
with open('$STATE_FILE','r') as f: state=json.load(f)
mt_data = state.get('micro_tasks',{})
total = mt_data.get('total',0)
tasks = mt_data.get('tasks',{})

resume_mt = None
for i in range(1, total+1):
    k = f'MT-{i}'
    if k not in tasks:
        tasks[k] = {'status':'pending','senior-architect':'pending','senior-backend':'pending',
                     'senior-reviewer':'pending','senior-qa':'pending'}

    # Reconcile from disk
    if os.path.exists(f'{arts}/arch/MT-{i}-plan.md'):
        if tasks[k].get('senior-architect') != 'completed':
            tasks[k]['senior-architect'] = 'completed'
    if os.path.exists(f'{arts}/review/MT-{i}-review.md'):
        tasks[k]['senior-backend'] = 'completed'
        if tasks[k].get('senior-reviewer') != 'completed':
            tasks[k]['senior-reviewer'] = 'completed'
    if os.path.exists(f'{arts}/qa-tests/MT-{i}-qa.md'):
        if tasks[k].get('senior-qa') != 'completed':
            tasks[k]['senior-qa'] = 'completed'

    agents = ['senior-architect','senior-backend','senior-reviewer','senior-qa']
    all_done = all(tasks[k].get(a)=='completed' for a in agents)
    if all_done:
        tasks[k]['status'] = 'completed'
    elif resume_mt is None:
        resume_mt = i
        tasks[k]['status'] = 'in_progress'

mt_data['tasks'] = tasks
if resume_mt:
    mt_data['current_mt'] = resume_mt
state['micro_tasks'] = mt_data
state['current_step'] = 6
state['status'] = 'running'
with open('$STATE_FILE','w') as f: json.dump(state,f,indent=2)

completed = sum(1 for t in tasks.values() if t.get('status')=='completed')
if resume_mt:
    print(f'  Micro-tasks: {completed}/{total} completed')
    print(f'  Resume from: MT-{resume_mt}')
else:
    print(f'  All {total} micro-tasks completed!')
" 2>/dev/null

  echo ""
  print_mt_next
}

# ═══════════════════════════════════════════════════════════
#  Dispatch
# ═══════════════════════════════════════════════════════════

case "${1:-status}" in
  init)        init_pipeline "$2" ;;
  start)       mark_started "$2" ;;
  complete)    mark_complete "$2" ;;
  status)      print_status ;;
  next)        print_next ;;
  resume)      find_resume ;;
  init-mt)     init_micro_tasks "$2" ;;
  start-mt)    start_micro_task "$2" "$3" ;;
  complete-mt) complete_micro_task "$2" "$3" ;;
  block-mt)    block_micro_task "$2" "$3" ;;
  mt-status)   print_mt_status ;;
  resume-mt)   print_mt_next ;;
  *)
    echo "Usage: $0 <command> [args]"
    echo ""
    echo "  Pipeline (PRD phase):"
    echo "    init <topic>              Initialize new pipeline"
    echo "    start <agent>             Mark agent as started"
    echo "    complete <agent>          Mark agent as completed"
    echo "    status                    Full pipeline status"
    echo "    next                      Show next action"
    echo "    resume                    Find resume point from disk"
    echo ""
    echo "  Micro-tasks (Implementation phase):"
    echo "    init-mt <count>           Register N micro-tasks"
    echo "    start-mt <N> <agent>      Agent started for MT-N"
    echo "    complete-mt <N> <agent>   Agent completed for MT-N"
    echo "    block-mt <N> <agent>      MT-N blocked by agent"
    echo "    mt-status                 Micro-task progress table"
    echo "    resume-mt                 Show next MT action"
    ;;
esac