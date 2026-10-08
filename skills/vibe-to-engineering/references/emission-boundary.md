# Evidence output and result contract

R2-F2/F3/F6 corrective, delivered for independent review. The accepted literal `.env` boundary (A1),
runner enrollment/pinning (A2), retained `--with-path` entries (R2-F4) and wrapper exit namespace stay
unchanged. This document describes output from the check-running form of `scripts/evidence.py`.
Enrollment and help are separate command forms; their successful status 0 does not describe a check.

## One context for complete emissions

Before argument parsing, `emission.Parser` collects maskable `--env` values using its actual option
table: full names, unique abbreviations, attached values, separate operands and missing-operand errors.
Ambiguous prefixes whose candidates include `--env` also protect attached values (`--e=A=value`,
`--en=A=value`) while still refusing to parse. Spaces in such a value do not end collection of later
declarations. Exact option names take precedence over prefix matches; no command grammar is changed.
Collection ends at `--` or the command's first positional argument. The command's own `--env` arguments
are not wrapper declarations. Prohibited, malformed and duplicate declarations still supply protection
for parser/admission diagnostics before they are refused. No parent environment supplies secret values.

After recognized-file analysis succeeds, those classified secret values join the declared values in
the context for subsequent output, including summary paths and write errors. Declared values are
protected everywhere. Short (fewer than four characters) or all-numeric file values retain the existing
whole-word policy (`[\w-]` is a word character); other file values are protected everywhere. Ordinary
numeric/boolean settings classified as readable stay readable. Before file analysis, only the declared
values are known. Unreadable files still cause pre-launch refusal; this correction adds no reader.

Named and generic masking happens first. The complete evidence text, including its final newline, then
passes `emission.Context.scrub` before the same bytes are saved and echoed. All terminal stderr messages
are accumulated through final scratch validation and emitted together. Prefixes, labels, usage, help and message boundaries
are inside protection, so independently safe pieces cannot assemble a protected value afterward.

The scrubber finds all overlapping matches in the original text and substitutes readable masks. It checks
the assembled result for newly created matches, replacing those once with a printable word character
absent from every protected string. That character cannot participate in a secret across either edge;
its word status also cannot expose an adjacent embedded short file value as a whole word. There is no
replace-until-clean loop. Ordinary safe attribution remains visible. Symbol selection searches ASCII,
then Unicode word characters; it is finite and never echoes inputs if no output alphabet is available.

## Wrapper status and retained facts

- **0:** the check ran and its evidence was saved. This says nothing about whether the check passed.
- **1:** a wrapper operational failure, such as spawn failure or inability to save evidence.
- **2:** refusal before the check; this attempt ran nothing and produced no new evidence.
- **3:** integrity failure after the check ran. Evidence may or may not have been saved.

The known child return code is retained immediately when `subprocess.run` completes, before masking,
writing or scratch validation. Human diagnostics include the outcome when it can be displayed without a protected
value. A separate recoverable result always carries the available facts on contracted check terminal
paths, including post-launch failure. A positive child code is an exit, a negative one is a signal;
neither is substituted for the wrapper's process status.

The **last stderr line** is a versioned record with exactly these fields, normally compact JSON:

```json
{"v":1,"wrapper":0,"launched":true,"saved":true,"child":{"exit":2}}
```

`child` is `{"exit":N}`, `{"signal":N,"name":"SIGTERM"}` (name may be null for an unknown signal),
or null when no outcome is available. `launched` and `saved` describe this attempt, not pre-existing
evidence files. Child stdout/stderr are captured into evidence; neither can supply this wrapper-owned
stderr record. The record is emitted after non-destructive scratch validation, so an integrity failure
cannot leave a success record.

If literal JSON or its boundary with the human messages would contain a protected value, only this
fixed-schema record is encoded using two distinct printable word symbols absent from all protected
strings. The first symbol denotes zero, the second one; the remaining symbols encode UTF-8 bytes as
eight bits each, most significant bit first. A newline terminates either representation. This is a
lossless representation, **not encryption**: it encodes only process facts, never commands, paths,
exception text or secret values. It avoids the previous conflict where masking the digit `2` erased
the only record of a child exit 2. No sidecar file or new CLI flag is introduced.

`emission.read_result(stderr)` decodes and validates either representation, rejecting missing,
truncated, duplicate-key, wrong-shape/type and contradictory records. For a caller that already captured
`done = subprocess.run(..., capture_output=True)` (with a check, not help/enrollment):

```python
import emission  # from this skill's scripts directory

try:
    result = emission.read_result(done.stderr.decode("utf-8"))
except (UnicodeError, ValueError):
    check_passed = False  # unverified; never infer a pass from wrapper 0
else:
    check_passed = (done.returncode == result["wrapper"] == 0
                    and result["launched"] and result["saved"]
                    and result["child"] == {"exit": 0})
```

A caller also judges the check's assertions/numbers. Preserve captured stderr with the run when a
durable result is needed: the check-output file alone is not a wrapper-outcome record. Closed output
pipes, process termination or other failures that prevent a complete record leave the result unverified.

## Verification and scope

`tests/test_emission_corrective.py` covers marker boundaries, overlap/order, safe-text controls and
collector grammar. `tests/test_r2_emission_corrective.py` runs real checks for complete-stream/file
confidentiality, parser refusals, exit codes, signals, write/spawn failures and post-launch integrity;
its oracle is the actual fixture's outcome, decoded independently by `tests/result_record.py`.
`tests/test_emission_result.py` covers the result format, generated collisions and decoder refusals.

The existing `test_r2_confidentiality.py` battery now scans every complete output even for a one-character
value, and asserts the recoverable outcome for every case. Its old body-only exception and conditional
outcome exemption are superseded by stronger assertions; its cases and safe human-summary control remain.
Existing R2/R1, A1/A2, child environment, protocol and reader-matrix checks remain required.
`tests/test_f3_ambiguous.py` adds the F3-R1 ambiguous-attached refusal regressions, including malformed
settings, spaces/equals signs, value collisions with diagnostics, later declarations and boundary controls.

The A3/A4 follow-up retains scratch and refuses unsupported execution platforms. Allocated scratch paths
and sensitive-output notices pass through the existing complete-message context, including on refusals
after allocation and operational failures. A path that collides with a protected value stays masked;
callers must preserve that masking when recording it in the ledger. Paths are never added to the lossless
process-facts record. Enrollment has no admitted --env declarations and reports its retained scratch too.
An interruption emits the governed retained-scratch notice before propagating; when the subprocess call
did not return, the wrapper does not invent launch or child-outcome facts. No complete result record means
the interrupted check remains unverified, even when its scratch files survive.

This is output confidentiality under the existing literal policies, not a sandbox or protection from
an account-controlling attacker. The supported macOS runner identities, registry, masking algorithm and
result schema are unchanged. This work remains Unreleased, pending native macOS regression/workflow
verification, independent review and owner acceptance; it does not establish whole-skill readiness.
