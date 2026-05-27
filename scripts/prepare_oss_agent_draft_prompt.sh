#!/usr/bin/env bash
# Generates a draft-only prompt for local OSS coding helpers.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: ./scripts/prepare_oss_agent_draft_prompt.sh --task "<task>" [options]

Generates a prompt for a local OSS coding helper such as Codex --oss, Ollama,
or llama.cpp. The prompt is intentionally limited to draft-only output and must
not be used to authorize commits, pushes, runtime mutation, or external
requests.

Options:
  --task "<task>"         Required. Narrow task description for the OSS helper.
  --files "<paths>"       Optional. Comma-separated files the helper may edit.
  --checks "<commands>"   Optional. Comma-separated checks Codex/human will run after review.
  --context "<notes>"     Optional. Extra context for the helper.
  -h, --help              Show this help text.

Example:
  ./scripts/prepare_oss_agent_draft_prompt.sh \
    --task "Draft fixture matrix additions for a bash check script" \
    --files "scripts/check_example.sh" \
    --checks "bash -n scripts/check_example.sh,bash scripts/check_example.sh"
EOF
}

TASK=""
FILES=""
CHECKS=""
CONTEXT=""

while (($# > 0)); do
  case "$1" in
    --task)
      if (($# < 2)) || [[ "${2:-}" == --* ]]; then
        usage >&2
        exit 2
      fi
      TASK="$2"
      shift 2
      ;;
    --files)
      if (($# < 2)) || [[ "${2:-}" == --* ]]; then
        usage >&2
        exit 2
      fi
      FILES="$2"
      shift 2
      ;;
    --checks)
      if (($# < 2)) || [[ "${2:-}" == --* ]]; then
        usage >&2
        exit 2
      fi
      CHECKS="$2"
      shift 2
      ;;
    --context)
      if (($# < 2)) || [[ "${2:-}" == --* ]]; then
        usage >&2
        exit 2
      fi
      CONTEXT="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "${TASK}" ]]; then
  usage >&2
  exit 2
fi

cat <<EOF
Task:
${TASK}

Operating mode:
- You are a draft-only local OSS coding helper.
- Output a proposed patch or structured edit plan only.
- Do not run commands.
- Do not claim validation was run.
- Do not create commits, branches, PRs, or pushes.

Hard prohibitions:
- Do not touch env, secrets, credentials, or tokens.
- Do not perform runtime mutation.
- Do not trigger external requests.
- Do not enable live trading.
- Do not modify deploy, docker, nginx, firewall, or cloud-host settings.

Repository workflow:
- Your output will be reviewed by Codex or a human before any repo change is accepted.
- Required checks will be run after review by the repository operator.
- Missing information should be called out explicitly instead of guessed.

Preferred output:
- Unified diff if possible.
- If a diff is not practical, provide a file-by-file edit plan with exact snippets.

Allowed files:
${FILES:-"(not specified; keep edits narrow and conservative)"}

Planned validation after review:
${CHECKS:-"(not specified yet; repository operator will decide)"}

Additional context:
${CONTEXT:-"(none)"}
EOF
