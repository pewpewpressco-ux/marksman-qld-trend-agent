#!/usr/bin/env python3
"""
Marksman deterministic log writer + integrity validator.

WHY THIS EXISTS
---------------
qld_agent_log.txt entries used to be hand-composed prose written by append. A
cut-off write or a missing trailing newline left a fragment, and the integrity
check then re-flagged that fragment on every subsequent run. This module makes the
failure mode impossible: one structured record -> one validated, newline-terminated
line, written in a single atomic flush+fsync. The agent no longer assembles the
line by hand. NOTE / NOTIFY-FAILED lines also go through `note` so nothing is
hand-written.

USAGE
-----
  python3 log_writer.py append --ts "2026-06-16 08:10 ET" --qqq 743.84 --sma 626.23 \
      --zone "ABOVE upper band $638.76 (+18.78% vs SMA200)" --state "IN 21.72 sh" \
      --action "HOLD" --value 2151 --note "new ATH; halt floor $1,075 not triggered"
  python3 log_writer.py append ... --dry-run          # preview, no write
  python3 log_writer.py note --ts "..." --text "NOTIFY FAILED - reason"
  python3 log_writer.py validate                       # exit 1 if any malformed line
  python3 log_writer.py repair                          # one-time fix of known frags

Validator policy: blank lines and the leading '#' header are ignored. Lines tagged
NOTE / EXECUTION / RECOVERED / (transition) / DATA ERROR / DRAWDOWN HALT are
acknowledged variants and are not flagged. Every other line is a standard run
record and must carry QQQ:, SMA200:, State:, Action:, and a terminal Value: field.
"""
import argparse
import os
import re
import sys

LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qld_agent_log.txt")

ACK_MARKERS = ("NOTE", "EXECUTION", "RECOVERED", "(transition)", "DATA ERROR",
               "DRAWDOWN HALT")
REQUIRED = ("QQQ:", "SMA200:", "State:", "Action:", "Value:")


def _fmt_money(v):
    s = str(v).strip()
    if s.lower() in ("n/a", "na", "none", ""):
        return "n/a"
    s = s.replace("$", "").replace(",", "")
    return "$" + format(int(round(float(s))), ",d")


def _fmt_price(v):
    s = str(v).strip().replace("$", "").replace(",", "")
    return "$" + format(float(s), ".2f")


def compose(ts, qqq, sma, zone, state, action, value, note=None,
            notify_failed=False):
    ts = ts.strip()
    if not (ts.startswith("[") and ts.endswith("]")):
        ts = "[" + ts.strip("[]") + "]"
    val = _fmt_money(value)
    if note:
        val = "%s (%s)" % (val, note.strip())
    line = ("%s | QQQ: %s | SMA200: %s | Zone: %s | State: %s | Action: %s | "
            "Value: %s") % (ts, _fmt_price(qqq), _fmt_price(sma), zone.strip(),
                            state.strip(), action.strip(), val)
    if notify_failed:
        line += " | NOTIFY FAILED"
    if "\n" in line or "\r" in line:
        raise ValueError("composed log line contains a newline -- refusing to write")
    return line


def compose_note(ts, text):
    ts = ts.strip()
    if not (ts.startswith("[") and ts.endswith("]")):
        ts = "[" + ts.strip("[]") + "]"
    line = "%s | NOTE: %s" % (ts, text.strip())
    if "\n" in line or "\r" in line:
        raise ValueError("composed note contains a newline -- refusing to write")
    return line


def _ensure_trailing_newline(path):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return
    with open(path, "rb") as f:
        f.seek(-1, os.SEEK_END)
        last = f.read(1)
    if last != b"\n":
        with open(path, "ab") as f:
            f.write(b"\n")
            f.flush()
            os.fsync(f.fileno())


def append_line(line, path=LOG):
    if "\n" in line or "\r" in line:
        raise ValueError("refusing to write a multi-line log entry")
    _ensure_trailing_newline(path)
    with open(path, "ab") as f:
        f.write((line + "\n").encode("utf-8"))
        f.flush()
        os.fsync(f.fileno())
    with open(path, "r", encoding="utf-8") as f:
        written = f.read().splitlines()[-1]
    if written != line:
        raise RuntimeError("post-write verification failed: disk line != intended")
    return line


def validate(path=LOG):
    problems = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    for i, raw in enumerate(lines, start=1):
        line = raw.rstrip()
        if not line or line.startswith("#"):
            continue
        if any(m in line for m in ACK_MARKERS):
            continue
        missing = [k for k in REQUIRED if k not in line]
        if missing:
            problems.append((i, "missing " + ", ".join(missing)))
            continue
        tail = line.rsplit("Value:", 1)[1].strip()
        if not re.match(r"(\$[\d,]+|\bn/a\b)", tail):
            problems.append((i, "Value field not parseable: %r" % tail))
    return problems


def repair(path=LOG):
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().split("\n")
    changed = False
    for i, raw in enumerate(lines):
        if ("2026-06-14 21:00 ET" in raw and "malformed frag" in raw
                and "RECOVERED" not in raw):
            base = raw.rstrip()
            if base.endswith("malformed frag"):
                base = base[: -len("malformed frag")] + "malformed fragment"
            lines[i] = (base + ", now acknowledged) | Value: n/a "
                        "[RECOVERED 2026-06-15: original entry was truncated "
                        "mid-write; the account value for the 2026-06-14 weekend run "
                        "was not captured and is not recoverable. Prior 2026-06-12 run "
                        "logged $2,033; weekend value was unchanged but is not a traced "
                        "read for this run.]")
            changed = True
    text = "\n".join(lines)
    if not text.endswith("\n"):
        text += "\n"
    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
    return changed


def main():
    ap = argparse.ArgumentParser(description="Marksman log writer / validator")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="compose + append one validated run line")
    a.add_argument("--ts", required=True)
    a.add_argument("--qqq", required=True)
    a.add_argument("--sma", required=True)
    a.add_argument("--zone", required=True)
    a.add_argument("--state", required=True)
    a.add_argument("--action", required=True)
    a.add_argument("--value", required=True)
    a.add_argument("--note", default=None)
    a.add_argument("--notify-failed", action="store_true")
    a.add_argument("--dry-run", action="store_true")

    n = sub.add_parser("note", help="append a free-form acknowledged NOTE line")
    n.add_argument("--ts", required=True)
    n.add_argument("--text", required=True)
    n.add_argument("--dry-run", action="store_true")

    sub.add_parser("validate", help="report malformed lines (exit 1 if any)")
    sub.add_parser("repair", help="one-time fix of known truncated lines")

    args = ap.parse_args()

    if args.cmd == "append":
        line = compose(args.ts, args.qqq, args.sma, args.zone, args.state,
                       args.action, args.value, args.note, args.notify_failed)
        if args.dry_run:
            print(line)
            return
        append_line(line)
        print("APPENDED: " + line)
        probs = validate()
        if probs:
            print("WARNING: validator flagged: %s" % probs, file=sys.stderr)
            sys.exit(1)
        print("VALIDATE: clean")

    elif args.cmd == "note":
        line = compose_note(args.ts, args.text)
        if args.dry_run:
            print(line)
            return
        append_line(line)
        print("APPENDED NOTE: " + line)

    elif args.cmd == "validate":
        probs = validate()
        if probs:
            for ln, why in probs:
                print("LINE %d: %s" % (ln, why))
            sys.exit(1)
        print("VALIDATE: clean (no malformed lines)")

    elif args.cmd == "repair":
        changed = repair()
        print("REPAIR: " + ("lines updated" if changed else "nothing to repair (idempotent)"))
        probs = validate()
        print("VALIDATE: " + ("clean" if not probs else "still flagged: %s" % probs))
        if probs:
            sys.exit(1)


if __name__ == "__main__":
    main()
