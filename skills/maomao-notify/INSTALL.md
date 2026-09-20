# Installing the `maomao-notify` skill into another agent

A self-contained Claude Code skill that lets an agent notify you via your
MaoMaoNotify server. Two files: `SKILL.md` (instructions + auto-trigger
description) and `notify.py` (a zero-dependency Python 3 CLI wrapping the Agent
API). Copy the whole `maomao-notify/` folder as one unit.

## Requirements

- Python 3 (standard library only — no pip installs).
- Two environment variables available to the agent's shell:
  - `MAOMAO_URL`  — e.g. `http://100.106.153.5:8287`
  - `MAOMAO_TOKEN` — an agent token with the `notification:send` scope
    (add `presence:read` for `--presence`). Create it in the Web Admin
    (`/admin` → Agents) under the account whose devices you use.

## Install into a Claude Code agent

Copy the folder into one of the skill directories, then set the env vars:

```bash
# available in every project (recommended for "ping me" from anywhere):
cp -r maomao-notify ~/.claude/skills/

# or only inside one project:
cp -r maomao-notify <that-project>/.claude/skills/
```

Add to the shell profile the agent runs under (e.g. `~/.zshrc`):

```bash
export MAOMAO_URL="http://100.106.153.5:8287"
export MAOMAO_TOKEN="<the agent token>"
```

Claude Code auto-discovers the skill from `SKILL.md`'s `name`/`description` —
nothing else to register. Verify:

```bash
env MAOMAO_URL=$MAOMAO_URL MAOMAO_TOKEN=$MAOMAO_TOKEN \
  python3 ~/.claude/skills/maomao-notify/notify.py "hello from a new agent"
```

## Use from a non-Claude-Code agent

`notify.py` is a normal CLI — call it directly from any agent/CI that can run
Python and read the two env vars:

```bash
python3 /path/to/maomao-notify/notify.py --priority high "deploy failed"
```

Or skip the script entirely and POST from anything that can do HTTP:

```bash
curl -s -X POST "$MAOMAO_URL/api/v1/notifications" \
  -H "Authorization: Bearer $MAOMAO_TOKEN" -H 'Content-Type: application/json' \
  -d '{"title":"CI","message":"deploy done","type":"text","priority":"normal"}'
```

Voice alert: set `"type":"voice"`, drop `message`, and add
`"voice":{"source":"server_tts","language":"zh-TW"}` + `"content":{"text":"..."}`.
