"""Interpret the append-only ledger for an approved Migration Map."""
import re
from typing import NamedTuple, Optional

from gitrun import Fail

SAFE_VERSION = re.compile(r"[A-Za-z0-9._-]+")
APPROVAL_EVENT = re.compile(r"PLAN APPROVED v(\S+)\Z")
FINAL_OUTCOMES = {
    "VIBE-TO-ENGINEERING — ALL GREEN": "All green",
    "VIBE-TO-ENGINEERING — COMPLETE WITH APPROVED BASELINE FAILURES": "Complete with approved failures",
    "VIBE-TO-ENGINEERING — COMPLETE WITH ACCEPTED VERIFICATION GAPS": "Complete with accepted gaps",
}
PLAN_FINGERPRINT = re.compile(r" {0,3}(?:Plan fingerprint:\s*)?`?([0-9a-f]{40}|[0-9a-f]{64})`?", re.I)
PHASE_EVENT = re.compile(r"PHASE ([1-9]\d*) (STARTED|COMPLETE|FAILED)\Z")
PHASE_RESTORE = re.compile(r"(?:r[1-9]\d*-)?\d{2,}-phase-([1-9]\d*)\Z")
BASELINE_RESTORE = re.compile(r"(?:r[1-9]\d*-)?00-baseline(?:-checked)?\Z")
EVENT_STATE = {"STARTED": "Now", "COMPLETE": "Done", "FAILED": "Failed"}


def approved_map_name(version, run=1):
    if not isinstance(version, str) or not SAFE_VERSION.fullmatch(version):
        raise Fail("unsafe or missing approved plan version")
    prefix = "" if run == 1 else "r%d-" % run
    return "approved-map-%sv%s.json" % (prefix, version)


def unfenced_lines(lines):
    fence = None
    for index, line in enumerate(lines):
        start = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)", line)
        if start:
            mark, rest = start.groups()
            if fence is None:
                fence = mark
            elif mark.startswith(fence) and not rest.strip():
                fence = None
            continue
        if not fence:
            yield index, line


def ledger_headings(lines):
    for index, line in unfenced_lines(lines):
        heading = re.match(r"^ {0,3}##[ \t]+(.+?)\s*$", line)
        if heading:
            fields = heading[1].split(" — ", 3)
            # Final outcomes have an em dash inside the event name.
            outcome_start = 0 if fields[0] == "VIBE-TO-ENGINEERING" else 1
            outcome = " — ".join(fields[outcome_start:outcome_start + 2])
            if outcome in FINAL_OUTCOMES:
                yield index, outcome, " — ".join(fields[outcome_start + 2:])
            elif len(fields) >= 3:
                yield index, fields[1], " — ".join(fields[2:])
            elif len(fields) == 1:
                yield index, fields[0], ""


class LedgerProgress(NamedTuple):
    states: dict
    completions: dict
    stopped: bool
    plan_only: bool
    restored: bool
    started: bool
    outcome: Optional[str]
    run: int
    fingerprints: dict


def update_warnings(lines, warnings, *, finalized=False):
    """Decisions use the same behavior label until its covering check closes it."""
    accepted_detail = baseline_failure = False
    for raw in lines:
        line = raw.strip()
        if line.startswith("- "):
            line = line[2:]
        if finalized and line.startswith(("Verification Warning:", "Not verified (accepted by the owner):",
                                          "Still failing (approved at the baseline):")):
            raise Fail("ledger warning or exception follows the final outcome")
        if line.startswith("Verification Warning:"):
            match = re.fullmatch(r"Verification Warning: (OPEN|ACCEPTED BY OWNER|CLOSED) — (.+)", line)
            if not match:
                raise Fail("unrecognized verification warning decision")
            warnings[match[2]] = match[1]
        elif line.startswith("Not verified (accepted by the owner):"):
            accepted_detail = True
        elif line.startswith("Still failing (approved at the baseline):"):
            baseline_failure = True
    return accepted_detail, baseline_failure


def final_status(event, warnings, accepted_detail, baseline_failure):
    if "OPEN" in warnings.values():
        raise Fail("final outcome has an open verification warning")
    status = FINAL_OUTCOMES[event]
    accepted = accepted_detail or "ACCEPTED BY OWNER" in warnings.values() or status == "Complete with accepted gaps"
    failures = baseline_failure or status == "Complete with approved failures"
    if failures and accepted:
        return "Complete with approved failures and accepted gaps"
    if failures:
        return "Complete with approved failures"
    if accepted:
        return "Complete with accepted gaps"
    return status


def advance_phase(states, number, action):
    next_phase = next((n for n, state in states.items() if state != "Done"), None)
    if number != next_phase:
        raise Fail("phase order: Phase %d cannot advance before its turn" % number)
    if action == "STARTED" and states[number] != "Waiting":
        raise Fail("Phase %d already started; record a correction or restore first" % number)
    states[number] = EVENT_STATE[action]


def current_approval(ledger, version, fingerprint, *, require_open=False):
    """Match the latest approval to these plan bytes, independently of map output."""
    lines = ledger.splitlines()
    events = list(ledger_headings(lines))
    run, run_start, next_start, last, boundary = 0, 0, 0, None, 0
    fingerprints = {}
    new_run = True
    for index, (line, event, _) in enumerate(events):
        if event == "MIGRATION STOPPED" or event in FINAL_OUTCOMES:
            new_run, next_start, boundary = True, index + 1, line + 1
            continue
        approval = APPROVAL_EVENT.fullmatch(event)
        if not approval:
            continue
        if new_run:
            run += 1
            run_start = next_start
            fingerprints = {}
            new_run = False
        if approval[1] in fingerprints:
            raise Fail("ledger repeats a plan version in the same run")
        # Only the last presented plan fingerprint in this approval interval applies.
        recorded = [m[1] for _, row in unfenced_lines(lines[boundary:line])
                    if (m := PLAN_FINGERPRINT.fullmatch(row.rstrip()))]
        fingerprints[approval[1]] = recorded[-1] if recorded else None
        last, boundary = index, line + 1
    if last is None or events[last][1] != "PLAN APPROVED v" + version:
        raise Fail("map version does not match the current approval")
    if fingerprints[version] != fingerprint:
        raise Fail("ledger has no matching approved plan fingerprint before the current approval")
    if require_open and new_run:
        raise Fail("the approved migration has ended; a new run requires its own approval")
    return lines, events, run, run_start, last, fingerprints


def phase_states(ledger, version, fingerprint, numbers):
    lines, events, run, run_start, last, fingerprints = current_approval(ledger, version, fingerprint)
    states = dict.fromkeys(numbers, "Waiting")
    if list(states) != sorted(states):
        raise Fail("phase order: plan phase numbers must be ascending")
    completions, active_version, outcome = {}, None, None
    stopped = restored = started = False
    warnings = {}
    if run_start == 0:
        update_warnings(lines[:events[0][0]], warnings)
    elif events[run_start - 1][1] == "MIGRATION STOPPED":
        # The STOP report records the project and checkpoint. New decisions may
        # already be recorded before the new run's first approval heading.
        stop_line = events[run_start - 1][0]
        update_warnings(lines[stop_line + 1:events[run_start][0]], warnings)
    plan_only = events[last][2] == "PLAN ONLY"
    for index in range(run_start, len(events)):
        line, event, _ = events[index]
        end = events[index + 1][0] if index + 1 < len(events) else len(lines)
        accepted_detail, baseline_failure = update_warnings(lines[line + 1:end], warnings, finalized=outcome is not None)
        phase = PHASE_EVENT.fullmatch(event)
        approved = APPROVAL_EVENT.fullmatch(event)
        restore = event == "RESTORED" or event.startswith("RESTORED ")
        if outcome is not None and (phase or restore or event in FINAL_OUTCOMES or event == "MIGRATION STOPPED"):
            raise Fail("ledger event %s follows the final outcome" % event)
        if stopped and (phase or event in FINAL_OUTCOMES):
            raise Fail("ledger event %s follows MIGRATION STOPPED without a new approval" % event)
        if (phase or restore) and active_version is None:
            raise Fail("ledger event %s has no active plan approval" % event)
        if approved:
            active_version = approved[1]
        elif phase:
            number = int(phase[1])
            started |= phase[2] == "STARTED"
            if number not in states:
                if index < last:
                    continue
                raise Fail("ledger event names a phase absent from the plan: %s" % number)
            advance_phase(states, number, phase[2])
            if phase[2] == "COMPLETE":
                completions[number] = active_version
            restored = False
            if index > last:
                plan_only = False
        elif event == "MIGRATION STOPPED":
            stopped = True
        elif event in FINAL_OUTCOMES and index > last:
            unfinished = ["Phase %d is %s" % (number, state) for number, state in states.items() if state != "Done"]
            if unfinished:
                raise Fail("final outcome requires every phase to be Done (%s)" % ", ".join(unfinished))
            outcome = final_status(event, warnings, accepted_detail, baseline_failure)
        elif restore:
            label = event[len("RESTORED "):]
            saved_phase = PHASE_RESTORE.fullmatch(label)
            if BASELINE_RESTORE.fullmatch(label):
                cutoff = 0
            elif saved_phase:
                cutoff = int(saved_phase[1])
            else:
                raise Fail("unknown restore label: %s" % label)
            for number in states:
                if number > cutoff:
                    states[number] = "Waiting"
            restored = True
            if index > last:
                plan_only = False
    return LedgerProgress(states, completions, stopped, plan_only, restored, started, outcome, run, fingerprints)
