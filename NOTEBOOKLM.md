# NotebookLM CLI: Install & Read

This notebook is for doing tasks with a set of sources (e.g. a list of
YouTube videos) — not for producing batch summaries. Use the commands below
to get the tool running and to read/query the sources.

## Install

```bash
python3 -m venv ~/venvs/notebooklm
source ~/venvs/notebooklm/bin/activate

pip install notebooklm-py
playwright install chromium
```

## Login (one-time per profile)

```bash
notebooklm login
```

Opens a browser to authenticate with your Google account. Session is saved to
`~/.notebooklm/profiles/default/storage_state.json` — no need to log in again
until it expires.

Check status any time:
```bash
notebooklm doctor    # profile setup + auth status
notebooklm status    # current active notebook/conversation
```

## Create a notebook and add sources

```bash
notebooklm create "My Notebook" --use     # create + set as active
notebooklm use <notebook_id>              # or switch to an existing one

notebooklm source add "<youtube-url>"     # type auto-detected
notebooklm source add "<url>" --type youtube
notebooklm source list                    # confirm sources are in
notebooklm source wait <source_id>        # wait until processed
```

Repeat `source add` for each link. Partial notebook/source IDs work
(e.g. `notebooklm use abc` matches `abc123...`).

### Troubleshooting: `source add` fails on a YouTube URL

If `source add "<youtube-url>"` fails with `RPC ADD_SOURCE failed ... rpc_code=9`, the cause
is usually the **URL shape**, not auth or quota — seen concretely with a `/live/<id>` URL:

```bash
notebooklm source add "https://www.youtube.com/live/O_TaSnZomi0" --type youtube
# ERROR ... RPC ADD_SOURCE failed ... rpc_code=9
```

**Fix**: rewrite it to the standard `watch?v=<id>` form before adding — same video ID, just a
different URL path:

```bash
notebooklm source add "https://www.youtube.com/watch?v=O_TaSnZomi0"
# Added source: 4920f1b9-7186-41e8-a640-87a63b847289
```

Also drop the explicit `--type youtube` once you're on a `watch?v=` URL — auto-detect handles
it fine and there's one less thing to get wrong. If a plain `watch?v=` URL still fails, *then*
suspect auth/quota (`notebooklm doctor`) rather than the URL.

## Reading / asking questions (the actual task)

```bash
notebooklm ask "what does this video say about X?"
notebooklm ask -s <source_id> "question about one specific source"
notebooklm ask --new "start a fresh conversation"
notebooklm source guide <source_id>       # AI overview + keywords for one source
notebooklm summary                        # notebook-level AI insights
```

- Answers include inline citations like `[1]`, `[2]` referencing sources.
- Add `--json` to any command for structured output (source IDs included).
- Add `--save-as-note` to `ask` to persist an answer as a note in the notebook.
- Use `-s <source_id>` (repeatable) to scope a question to specific sources
  instead of the whole notebook.

## Notes for whoever (or whatever) reads this next

- This handover is generic on purpose — no notebook name/ID is hardcoded —
  so it can be copied as-is into a new notebook for a new batch of links.
- Goal here is answering questions / completing a task using the sources,
  not generating a structured summary of each one.
