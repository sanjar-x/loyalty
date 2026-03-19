#!/bin/bash
# .claude/hooks/on-agent-stop.sh
# SubagentStop hook: auto-detects pipeline agent, updates state, prints next step
# Claude Code passes JSON via stdin with agent_type field (NOT agent_name)
#
# v2 CHANGELOG:
#   FIX: Python detection — python3 first, then python (was python twice)
#   FIX: Loop agents (7–10) use complete-mt instead of complete
#   NEW: Fuzzy matching — handles both exact slugs and description-based names
#   NEW: MT number extraction from agent prompt/name for loop agents
#   NEW: Error logging to .claude/hooks/error.log

LOG_FILE=".claude/hooks/error.log"
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null

log() {
  local ts
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ" 2>/dev/null || date +"%Y-%m-%dT%H:%M:%SZ")
  echo "[$ts] [on-agent-stop] $1" >> "$LOG_FILE" 2>/dev/null
}

# --- FIX: was `python || python`, now `python3 || python` ---
PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null)
if [ -z "$PYTHON" ]; then
  log "ERROR: Python not found"
  echo "ERROR: Python не найден" >&2
  exit 1
fi

# Read JSON from stdin (Claude Code passes hook context here)
INPUT=$(cat)
log "Raw input (truncated): $(echo "$INPUT" | head -c 500)"

# Extract agent_type and last_assistant_message via Python (stdin-safe)
PARSED=$("$PYTHON" -c "
import sys, json
try:
    d = json.loads(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else {}
except Exception:
    d = {}
name = d.get('agent_type', '') or d.get('agent_name', '') or ''
# Truncate prompt to avoid shell variable limits — only need MT-N pattern
prompt = d.get('last_assistant_message', '') or ''
prompt = prompt[-2000:] if len(prompt) > 2000 else prompt
# Output as tab-separated (safe: name has no tabs, prompt may but we only grep it)
sys.stdout.write(name + '\t' + prompt)
" "$INPUT" 2>/dev/null)

AGENT_NAME=$(echo "$PARSED" | cut -f1)
AGENT_PROMPT=$(echo "$PARSED" | cut -f2-)

# Fallback: if Python parsing failed, try simple grep
if [ -z "$AGENT_NAME" ]; then
  AGENT_NAME=$(echo "$INPUT" | grep -o '"agent_type"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:.*"\([^"]*\)"/\1/')
fi
if [ -z "$AGENT_NAME" ]; then
  AGENT_NAME=$(echo "$INPUT" | grep -o '"agent_name"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/.*:.*"\([^"]*\)"/\1/')
fi

log "Extracted agent_name='$AGENT_NAME'"

# ─── Agent matching ───
# Exact slug match first, then fuzzy match on description/prompt

PRD_AGENTS="context-analyst competitive-intel gap-analysis prd-writer review-qa senior-pm"
LOOP_AGENTS="senior-architect senior-backend senior-reviewer senior-qa"
ALL_AGENTS="$PRD_AGENTS $LOOP_AGENTS"

MATCHED_AGENT=""

# 1) Exact match
for agent in $ALL_AGENTS; do
  if [ "$AGENT_NAME" = "$agent" ]; then
    MATCHED_AGENT="$agent"
    break
  fi
done

# 2) Fuzzy match — agent_name may contain the slug as a substring
#    e.g. "Market research for Products" contains no slug,
#    but "competitive-intel" prompt or description might
if [ -z "$MATCHED_AGENT" ]; then
  SEARCH_TEXT="$AGENT_NAME $AGENT_PROMPT"
  # Match by unique keywords in agent names/descriptions
  if echo "$SEARCH_TEXT" | grep -qi "context.analyst\|context.*brief\|topic.*decomp"; then
    MATCHED_AGENT="context-analyst"
  elif echo "$SEARCH_TEXT" | grep -qi "competitive.intel\|market.*research\|competitive.*report"; then
    MATCHED_AGENT="competitive-intel"
  elif echo "$SEARCH_TEXT" | grep -qi "gap.analysis\|enhancement.*plan\|decision.*matrix"; then
    MATCHED_AGENT="gap-analysis"
  elif echo "$SEARCH_TEXT" | grep -qi "prd.writer\|write.*prd\|prd.*document"; then
    MATCHED_AGENT="prd-writer"
  elif echo "$SEARCH_TEXT" | grep -qi "review.qa\|qa.*report\|validate.*prd"; then
    MATCHED_AGENT="review-qa"
  elif echo "$SEARCH_TEXT" | grep -qi "senior.pm\|micro.task.*decomp\|pm.spec"; then
    MATCHED_AGENT="senior-pm"
  elif echo "$SEARCH_TEXT" | grep -qi "senior.architect\|arch.*plan\|architecture.*plan"; then
    MATCHED_AGENT="senior-architect"
  elif echo "$SEARCH_TEXT" | grep -qi "senior.backend\|implement.*mt\|senior.*backend"; then
    MATCHED_AGENT="senior-backend"
  elif echo "$SEARCH_TEXT" | grep -qi "senior.reviewer\|review.*mt\|code.*review"; then
    MATCHED_AGENT="senior-reviewer"
  elif echo "$SEARCH_TEXT" | grep -qi "senior.qa\|test.*mt\|qa.*test"; then
    MATCHED_AGENT="senior-qa"
  fi

  if [ -n "$MATCHED_AGENT" ]; then
    log "Fuzzy matched '$AGENT_NAME' -> '$MATCHED_AGENT'"
  fi
fi

# No match — exit silently (not a pipeline agent)
if [ -z "$MATCHED_AGENT" ]; then
  log "No match for agent_name='$AGENT_NAME' — skipping"
  exit 0
fi

# ─── Determine if this is a loop agent (7–10) ───

is_loop_agent() {
  case "$1" in
    senior-architect|senior-backend|senior-reviewer|senior-qa) return 0 ;;
    *) return 1 ;;
  esac
}

if is_loop_agent "$MATCHED_AGENT"; then
  # Extract MT number from agent name or prompt
  # Patterns: "MT-3", "MT 3", "micro-task 3", "Micro-Task 3"
  MT_NUM=""
  SEARCH_TEXT="$AGENT_NAME $AGENT_PROMPT $INPUT"

  MT_NUM=$(echo "$SEARCH_TEXT" | grep -oE "MT[-_ ]?([0-9]+)" | head -1 | grep -oE "[0-9]+")

  if [ -z "$MT_NUM" ]; then
    MT_NUM=$(echo "$SEARCH_TEXT" | grep -oiE "micro[-_ ]?task[-_ ]?([0-9]+)" | head -1 | grep -oE "[0-9]+")
  fi

  if [ -n "$MT_NUM" ]; then
    log "Loop agent: $MATCHED_AGENT completing MT-$MT_NUM"
    bash .claude/hooks/pipeline-state.sh complete-mt "$MT_NUM" "$MATCHED_AGENT"
  else
    # Fallback: read current_mt from state
    STATE_FILE=".claude/pipeline-runs/current/state.json"
    if [ -f "$STATE_FILE" ]; then
      MT_NUM=$("$PYTHON" -c "
import json
with open('$STATE_FILE') as f: s=json.load(f)
print(s.get('micro_tasks',{}).get('current_mt',0))
" 2>/dev/null)
      if [ -n "$MT_NUM" ] && [ "$MT_NUM" -gt 0 ]; then
        log "Loop agent: $MATCHED_AGENT completing MT-$MT_NUM (from current_mt fallback)"
        bash .claude/hooks/pipeline-state.sh complete-mt "$MT_NUM" "$MATCHED_AGENT"
      else
        log "WARNING: Could not determine MT number for $MATCHED_AGENT — skipping"
      fi
    else
      log "WARNING: No state file, cannot determine MT for $MATCHED_AGENT"
    fi
  fi
else
  # PRD-phase agent — simple complete
  log "PRD agent: completing $MATCHED_AGENT"
  bash .claude/hooks/pipeline-state.sh complete "$MATCHED_AGENT"
fi

exit 0