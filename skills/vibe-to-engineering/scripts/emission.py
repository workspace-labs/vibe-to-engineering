#!/usr/bin/env python3
"""Governed output for R2-F2/F3/F6: complete messages, parser output and result facts.

An early context collects every maskable wrapper --env value before parsing. After secret-file
classification the context also contains the known file values, preserving their whole-word rule for
short/numeric values. No parent environment or unrelated file supplies redaction data.

Redaction finds overlapping spans in the original text, substitutes readable masks, then checks the
assembled result. Any newly created match is replaced ONCE by a word character absent from every
protected value. Such a replacement cannot create a value across its edges, inside itself, or by turning
an adjacent short file value into a whole word. There is no replace-until-clean loop.

Wrapper 0/1/2/3 means ran+evidence / operational failure / pre-launch refusal / post-launch integrity.
The child outcome is separate data. Standard library only; Python 3.8+.
"""

import argparse
import json
import re
import signal
import sys

RAN, OPERATIONAL, REFUSED, INTEGRITY = 0, 1, 2, 3   # the wrapper status namespace (owner decision 5.3)

MASK = "<masked>"        # the value-free fallback marker — used only where it holds no context value
MARKER_LENGTH = 64       # a generated fallback marker is one safe character repeated this many times
ONLY_SPACE_EQUALS = re.compile(r"[\s=]+")   # a value of only whitespace and '=' can never be masked
WORD = re.compile(r"[\w-]\Z")
OPTIONS = {"--project": 1, "--out": 1, "--with-path": 1, "--enroll-runner": 1,
           "--env": 1, "--help": 0, "-h": 0}


def unmaskable(value):
    """Whether a value could never be masked (only whitespace and '='): childenv refuses such values at
    admission; the redaction contexts skip them too — masking a blank or '=' would destroy the text."""
    return not ONLY_SPACE_EQUALS.sub("", value)


def collect(argv, options=None):
    """Every maskable --env value from the wrapper's own raw arguments, before parsing and validation —
    the early redaction context (R2-F3, two-phase admission, phase one). Both spellings ('--env X=Y' and
    '--env=X=Y') count, and a setting's value counts however the setting would later fail (a duplicate or
    prohibited name's value is just as secret). Scanning stops at the command boundary — '--' or the first
    positional — so the check's own arguments are never read as wrapper settings; the parent's environment
    and unrelated user data are never consulted."""
    options = OPTIONS if options is None else options

    def candidates(token):
        name = token.partition("=")[0]
        if name in options:
            return [name]     # an exact option wins over all longer prefix matches, as in argparse
        return [key for key in options if name.startswith("--") and key.startswith(name)]

    def operand(token):
        # argparse accepts a negative number as an operand, but another option (even unknown) is not
        # consumed when a value is missing. Keep scanning that option so later --env values are protected.
        return (not token.startswith("-") or token == "-" or re.fullmatch(r"-\d+|-\d*\.\d+", token)
                or " " in token and not candidates(token))

    values = []
    at = 0
    while at < len(argv):
        token = argv[at]
        if token == "--" or operand(token):
            break                                        # the command boundary: nothing past it is ours
        setting = None
        matches = candidates(token)
        name = matches[0] if len(matches) == 1 else None
        _, equals, attached = token.partition("=")
        if equals and "--env" in matches:
            setting = attached   # ambiguous prefixes still refuse; their diagnostic echoes this value
        elif name and options[name] and not equals and at + 1 < len(argv):
            following = argv[at + 1]
            setting = following if name == "--env" else None
            if operand(following):
                at += 1
        at += 1
        if setting is None:
            continue
        name, equals, value = setting.partition("=")
        candidate = value if equals else setting         # a setting with no '=': the whole word is data
        if candidate and not unmaskable(candidate):
            values.append(candidate)
    return values


def symbols(values, count=1):
    """Printable word symbols absent from all protected strings (also safe at replacement boundaries).

    Try ASCII first, then Unicode letters/numbers. Search is finite; no input is echoed on exhaustion.
    The same alphabet property protects the lossless result record when literal JSON would collide.
    """
    used = set().union(*(set(value) for value in values)) if values else set()
    found = []
    for codepoint in [95] + list(range(65, 91)) + list(range(97, 123)):
        char = chr(codepoint)
        if char not in used:
            found.append(char)
            if len(found) == count:
                return found
    for codepoint in range(0xA1, 0x110000):
        char = chr(codepoint)
        if char not in used and char.isprintable() and WORD.fullmatch(char):
            found.append(char)
            if len(found) == count:
                return found
    raise ValueError("no representable output alphabet")


def fallback(values):
    """A mask marker that holds none of the context's values: '<masked>' itself when no value occurs
    inside it, else a word symbol absent from the protected strings. This only guarantees the marker's
    own bytes; Context.scrub also checks its concatenation with the surrounding text."""
    values = [value for value in values if value]
    if not any(value in MASK for value in values):
        return MASK
    return symbols(values)[0] * MARKER_LENGTH


class Context:
    """The applicable value policies at an emission point; settings classified as readable are excluded."""

    def __init__(self, declared=(), file_values=()):
        anywhere = {v for v in declared if v and not unmaskable(v)}
        whole = set()
        for value, _ in file_values:
            if value and not unmaskable(value):
                (whole if len(value) < 4 or value.isdigit() else anywhere).add(value)
        self.anywhere = anywhere
        self.whole = whole - anywhere
        self.values = sorted(anywhere | whole, key=lambda v: (-len(v), v))

    def spans(self, text):
        matches = []
        for value in self.values:
            at = text.find(value)
            while at >= 0:
                end = at + len(value)
                if value in self.anywhere or ((at == 0 or not WORD.fullmatch(text[at - 1])) and
                                              (end == len(text) or not WORD.fullmatch(text[end]))):
                    matches.append((at, end))
                at = text.find(value, at + 1)   # all original overlaps, before any substitution
        merged = []
        for start, end in sorted(matches):
            if merged and start <= merged[-1][1]:
                merged[-1][1] = max(end, merged[-1][1])
            else:
                merged.append([start, end])
        return merged

    @staticmethod
    def replace(text, spans, marker):
        pieces, done = [], 0
        for start, end in spans:
            pieces.extend((text[done:start], marker))
            done = end
        return "".join(pieces) + text[done:]

    def scrub(self, text):
        spans = self.spans(text)
        if not spans:
            return text
        result = self.replace(text, spans, fallback(self.values))
        recreated = self.spans(result)
        if recreated:
            # A word symbol absent from EVERY value cannot complete one on either edge. Word status also
            # preserves the non-boundary beside an originally embedded short/numeric file value.
            result = self.replace(result, recreated, symbols(self.values)[0] * MARKER_LENGTH)
        return result


def scrub(text, values):
    """Compatibility entry for declared values, which are protected anywhere, including single digits."""
    return Context(values).scrub(text)


def child_outcome(returncode):
    """The child's own result as data (owner decision 5.3): its exit code, or — when a signal ended it —
    the signal's number and name, never collapsed into an ordinary exit code (a returncode of -N is
    signal N; 'exit 1' would lie about SIGTERM)."""
    if returncode >= 0:
        return "exited %d" % returncode
    number = -returncode
    try:
        name = signal.Signals(number).name
    except ValueError:
        return "terminated by signal %d" % number
    return "terminated by signal %d (%s)" % (number, name)


def child_result(returncode):
    """Only known process facts, never command text, user values, paths or exception messages."""
    if returncode is None:
        return None
    if returncode >= 0:
        return {"exit": returncode}
    number = -returncode
    try:
        name = signal.Signals(number).name
    except ValueError:
        name = None
    return {"signal": number, "name": name}


def report(messages, context, wrapper, launched=False, saved=False, returncode=None):
    """One governed stderr emission, including all diagnostic boundaries and recoverable result facts.

    The final line is v1 JSON. If it (including its boundary with the human-readable messages) would
    reveal a protected value, encode ONLY the fixed-schema process facts using two safe word symbols:
    first symbol = zero, second = one, remaining symbols = MSB-first UTF-8 bits. Both symbols are absent
    from every protected string, so neither the line nor its edges can contain one. This is reversible
    transport, not encryption; it never transports user secrets. read_result accepts either form.
    """
    text = "".join(messages)
    if wrapper != RAN:
        ran = "ran (%s)" % child_outcome(returncode) if returncode is not None else (
            "ran (outcome unavailable)" if launched else "never ran")
        text += "evidence.py: run state: the check %s; evidence %s; wrapper status %d\n" % (
            ran, "was saved" if saved else "was not written", wrapper)
    human = context.scrub(text)
    # A line break belongs to the checked text, never to a print() suffix outside the boundary.
    if human and not human.endswith("\n"):
        human = context.scrub(human + "\n")
    record = json.dumps(dict(v=1, wrapper=wrapper, launched=launched, saved=saved,
                             child=child_result(returncode)), separators=(",", ":"))
    if context.spans(human + record + "\n") or human and not human.endswith("\n"):
        zero, one = symbols(context.values, 2)
        record = zero + one + "".join(one if byte & (1 << bit) else zero
                                      for byte in record.encode("utf-8") for bit in range(7, -1, -1))
        # An encoded line must start on its own line. Include the separator in the final human scrub;
        # a scrubbed trailing newline may disappear, so use a safe alphabet symbol as a terminator.
        if human and not human.endswith("\n"):
            human += zero + "\n"
    return human + record + "\n"


def read_result(stderr):
    """Decode the LAST stderr line, the wrapper-owned result (child stderr is captured into evidence).

    Reject missing, truncated or malformed records. A caller must also check the process status agrees
    with wrapper, then require child.exit == 0 for a passed check. Wrapper zero alone is never a pass.
    """
    try:
        if not stderr.endswith("\n"):
            raise ValueError
        line = stderr.splitlines()[-1]
        if line.startswith("{"):
            payload = line
        else:
            zero, one = line[:2]
            bits = line[2:]
            if zero == one or not bits or len(bits) % 8 or set(bits) - {zero, one}:
                raise ValueError
            data = bytearray()
            for at in range(0, len(bits), 8):
                value = 0
                for char in bits[at:at + 8]:
                    value = value * 2 + (char == one)
                data.append(value)
            payload = data.decode("utf-8")
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError
                result[key] = value
            return result

        result = json.loads(payload, object_pairs_hook=unique)
        if (not isinstance(result, dict) or set(result) != {"v", "wrapper", "launched", "saved", "child"}
                or type(result["v"]) is not int or result["v"] != 1
                or type(result["wrapper"]) is not int or result["wrapper"] not in (0, 1, 2, 3)
                or type(result["launched"]) is not bool or type(result["saved"]) is not bool):
            raise ValueError
        child = result["child"]
        if child is not None:
            if not isinstance(child, dict):
                raise ValueError
            if set(child) == {"exit"}:
                valid = type(child["exit"]) is int and child["exit"] >= 0
            else:
                valid = (set(child) == {"signal", "name"} and type(child["signal"]) is int
                         and child["signal"] > 0 and (child["name"] is None or isinstance(child["name"], str)))
            if not valid or not result["launched"]:
                raise ValueError
        if (result["saved"] and not result["launched"] or result["wrapper"] == RAN and
                (not result["saved"] or child is None) or result["wrapper"] == REFUSED and
                (result["launched"] or result["saved"]) or result["wrapper"] == INTEGRITY and not result["launched"]):
            raise ValueError
        return result
    except (ValueError, IndexError, KeyError, TypeError, UnicodeError):
        raise ValueError("missing or malformed wrapper result") from None


class Parser(argparse.ArgumentParser):
    """Collect from the actual parser's option table before parse_args can emit anything.

    Unique abbreviations follow argparse's grammar. Help goes through _print_message; an error's usage,
    prefix, diagnostic and result line are assembled before redaction, so their boundaries are covered.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = Context()

    def parse_args(self, args=None, namespace=None):
        argv = list(sys.argv[1:] if args is None else args)
        options = {key: 0 if action.nargs == 0 else 1 for key, action in self._option_string_actions.items()}
        self.context = Context(collect(argv, options))
        return super().parse_args(argv, namespace)

    def _print_message(self, message, file=None):
        if message:
            super()._print_message(self.context.scrub(message), file)

    def error(self, message):
        text = report([self.format_usage(), "%s: error: %s\n" % (self.prog, message)], self.context, REFUSED)
        # Already governed as one complete emission; do not re-scrub a lossless result record.
        sys.stderr.write(text)
        raise SystemExit(REFUSED)
