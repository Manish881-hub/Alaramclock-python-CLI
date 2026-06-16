# ⏰ alarm-clock

A terminal alarm clock built in Python. No dependencies beyond the standard library.

```
$ python alarm_clock.py

⏰  Alarm Clock  (type help for commands)

  #   TIME  LABEL                   REPEAT   STATUS
  ─   ────  ─────────────────────   ──────   ────────────
  1  07:30  Wake up                 daily    active
  2  09:00  Stand-up                daily    snoozed 3m
  3  18:00  Gym                     once     off

› add
  Time (HH:MM): 07:30
  Label (optional): Morning run
  Repeat daily? (y/N): y

  ✓  'Morning run' set — next ring Tue 17 Jun 07:30
```

---

## Quick start

```bash
python alarm_clock.py        # Python 3.10+
```

No `pip install` required. Run the tests with:

```bash
pip install pytest
python -m pytest test_alarm_clock.py -v
```

---

## Commands

| Command | What it does |
|---|---|
| `add` | Interactive prompt to set time, label, repeat |
| `list` | Show all alarms with status |
| `delete <n>` | Remove alarm by list number |
| `enable <n>` | Re-enable a disabled alarm |
| `s` | Snooze a ringing alarm (5 min) |
| `d` | Dismiss a ringing alarm |
| `quit` | Exit (alarms auto-saved) |

---

## Engineering Process

### Step 1 — Scoping the problem

The brief is deliberately open-ended: *"decide what to build with the time you have."*
That's the real test. With 30 minutes the risk isn't under-building — it's **over-building**
and delivering something half-finished or untested.

I used AI (Claude) to pressure-test an initial feature list:

> **Me:** "Here's a rough feature list for a CLI alarm clock. What's essential, what's
> nice-to-have, and what's a trap?"
>
> **AI output (paraphrased):**
> - **Essential:** set alarms, list them, trigger reliably, snooze/dismiss, survive restarts
> - **Nice-to-have:** recurring alarms, coloured output, auto-dismiss
> - **Traps:** timezone handling, multiple simultaneous alarms UI, config files (YAGNI)

I cut timezone support (defaulting to local time with a clear note), cut a config file
(hardcoded constants are fine for a 30-minute scope), and kept recurring alarms because
they're only ~10 extra lines and dramatically increase usefulness.

**Included:**
- Add / list / delete alarms
- Repeat-daily or one-shot
- Snooze (5 min, hardcoded but named constant)
- Auto-dismiss after 30 s (prevents zombie rings)
- Persistence to `~/.alarms.json` (survives restarts)
- Cross-platform audio with terminal-bell fallback
- Re-enable disabled alarms

**Excluded:**
- Timezone support (local time; noted in limitations)
- Multiple simultaneous snoozes
- Config file / CLI flags (YAGNI — constants are readable)
- Curses / rich TUI (scope creep; plain REPL is more robust)

---

### Step 2 — Architecture decisions

#### Threading model

The core tension: we need `input()` blocking in the main thread (user REPL) while a
background thread fires alarms at the right moment.

**Option A — `asyncio`:** Clean, but `input()` is not async-friendly; you'd need
`asyncio.get_event_loop().run_in_executor()` or `aioconsole`. Adds complexity with no
real benefit here.

**Option B — polling loop with `time.sleep`:** Simple but burns a thread and wakes every
second regardless.

**Option C — `threading.Thread` + `threading.Event.wait(timeout=)`:** The background
thread blocks on `Event.wait(timeout=1)` instead of `sleep(1)`. This is semantically
identical to B in steady state but gives us a clean shutdown path (`_stop.set()` →
`Event.wait` returns immediately) and a response channel for the ringing alarm. Chosen.

```
Main thread (REPL)          AlarmMonitor thread         Ring sub-thread
──────────────────          ───────────────────         ───────────────
input("› ")                 _stop.wait(timeout=1)       print banner
  │                           │ wakes                   beep()
  │ user types "s"            │ checks alarms           _response_event.wait(timeout=5)
  │                           │ alarm due →               │ wakes
  ▼                           │ spawn ring thread         ▼ read _response_value
monitor.receive_response("s")                           snooze / dismiss
  sets _response_event                                  save_alarms()
```

#### Response channel design

The ringing alarm needs to receive `s`/`d` from the main thread without polling. I used a
`threading.Event` + a plain string slot rather than a `queue.Queue`. Justification: there
is at most one ringing alarm at a time (a reasonable UX constraint), so a one-slot
channel is correct. A queue would imply buffering multiple responses, which has no
meaning here. If I extended to simultaneous alarms I'd switch to a `dict[alarm_id, Event]`.

#### Persistence

Alarms are stored as a JSON array in `~/.alarms.json`. Each `Alarm` is a `@dataclass`
so `dataclasses.asdict()` gives free serialisation; loading is `Alarm(**dict_from_json)`.

Alternatives considered:

| Option | Verdict |
|---|---|
| In-memory only | Fails the "what if the process crashes" test |
| SQLite | 40 lines of schema + cursor boilerplate — overkill |
| pickle | Binary, opaque, version-fragile |
| JSON | Human-readable, diff-friendly, zero deps |

The store is written on every mutation (add / delete / snooze / dismiss). With a small
alarm count (< 100) this is instant and avoids a dirty-state window.

#### Audio

Cross-platform audio without `pygame` or `playsound`:

| Platform | Primary | Fallback |
|---|---|---|
| macOS | `afplay` (bundled) | `\a` bell |
| Linux | `paplay` (PulseAudio) | `aplay` (ALSA) → `\a` |
| Windows | `winsound.Beep` (stdlib) | `\a` bell |

The audio call is wrapped in a broad `except Exception` — a failed beep should never
crash the alarm or leave the lock held.

#### Colour / ANSI

ANSI codes are emitted only when `sys.stdout.isatty()` is true. Piped or redirected
output stays clean. No external library (`rich`, `colorama`) needed.

---

### Step 3 — Implementation order

1. `Alarm` dataclass + `next_trigger()` logic (core invariant; easiest to test)
2. `load_alarms` / `save_alarms` (persistence; test with `tmp_path`)
3. `AlarmMonitor` thread skeleton (poll + fire)
4. REPL loop (add / list / delete)
5. Ring / snooze / dismiss flow
6. Audio + colour polish
7. Tests

Writing `next_trigger()` first let me validate the scheduling logic (past one-shot,
future, daily rollover, snooze override) before wiring up threads.

---

### Step 4 — How I used AI

| Task | AI role | My role |
|---|---|---|
| Feature triage | Generated list; flagged traps | Final cut decisions |
| Threading options | Explained asyncio vs threading tradeoffs | Chose threading.Event |
| `next_trigger` edge cases | Suggested: expired snooze, midnight rollover | Wrote + validated in tests |
| Audio platform matrix | Listed OS-specific commands | Verified on macOS, added timeout |
| README structure | Suggested sections | Wrote all prose |

I treated AI output as a **fast, opinionated colleague**: useful for surfacing options and
spotting edge cases I might miss in a time-constrained session, but every decision went
through my own reasoning before committing to code.

---

## Known limitations

- **Local time only.** Alarms fire at the system clock's local time. No timezone support.
- **One alarm at a time.** If two alarms fire within the same poll tick, only one is
  announced; the other fires on the next poll cycle (1 second later). Rare in practice.
- **`input()` blocks.** The alarm banner is printed above the prompt, which looks slightly
  odd. A curses UI would avoid this but was out of scope.

---

## What I'd add next

1. `--snooze-minutes N` CLI flag (respects user preference)
2. `alarm edit <n>` command (time / label update without delete + re-add)
3. Timezone support via `zoneinfo` (stdlib in 3.9+)
4. Rich TUI with `curses` to separate the alarm banner from the input line
5. Integration test: set alarm 5 seconds ahead, assert it fires and the monitor thread
   invokes the ring callback

---

## File layout

```
alarm-clock/
├── alarm_clock.py        # Single-file application (~280 lines)
├── test_alarm_clock.py   # Unit tests (parse_time, next_trigger, persistence, monitor)
├── requirements.txt      # Runtime: none. Dev: pytest
└── README.md
```
