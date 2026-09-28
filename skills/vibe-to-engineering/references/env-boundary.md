# The literal `.env` boundary (v0.1, owner decision A1, approved 2026-09-27)

A recognized `.env` file (names matching `.env`, `.env.*`, `*.env` — a data-format extension wins first, so
`.env.yaml` is YAML) reaches a check only when it fits the literal grammar below. Anything else refuses before
launch: exit 2, nothing runs, no evidence. The guiding rule: **every claimed reader reads admitted bytes
literally, or the file refuses.** The boundary replaces the reader-modeling approach (ported shell, Node and
dotenv parsers, interpolation computed from the constructed environment) with a positive grammar; those models
are no longer wired into the reader. The grammar is implemented in `scripts/envliteral.py` and wired into
`secretformats.dotenv_values`.

## The grammar

**File:** UTF-8, LF-only (a carriage return anywhere refuses), no byte order mark.

**Line:** blank (spaces/tabs only) · a comment (`#` after optional leading spaces or tabs) · one assignment.

**Assignment:** optional leading spaces · an optional single `export ` prefix · `NAME` =
`[A-Za-z_][A-Za-z0-9_]*` · no spaces around `=` · each name assigned at most once per file · then one VALUE:

- **empty** — `A=`, `A=''`, `A=""` (trailing spaces/tabs after an unquoted value are stripped by every
  claimed reader, the empty case included);
- **unquoted** — one or more characters **only** from `A–Z a–z 0–9` and `! % * + , - . / : = ? @ [ ] ^ _`,
  with `~` additionally allowed except at the value's start or immediately after `:`; then optional trailing
  spaces or tabs;
- **single-quoted** — one line; no `'`; no `$` or backtick; no consecutive backslashes (python-dotenv decodes
  the pair); no Unicode control character (category Cc) except a literal tab; no
  leading/trailing Unicode whitespace, including U+FEFF, inside the quotes; nothing after the closing quote;
- **double-quoted** — the same, and no `\` either.

**Refused** (each grounded in the experiment's demonstrated divergence or execution): a `$` or backtick
anywhere in a value — single quotes included, where dotenv 0.3–1.2 interpolate; an unquoted `#` (cut vs
keep); whitespace inside an unquoted value or around `=`; any other byte in an unquoted value — `{` and `}`
included (bash brace expansion: Codex's reproduced case, `export A=x{a,b}` reads `xb` under bash while Node
and python-dotenv read it literally — the combination, never the isolated character, is the operator, and its
trigger conditions are too subtle to characterize, so both braces are out of the set); `~` at a value's start
or after `:` (bash expands it through the account database, even with an empty environment); a duplicate name
(first- vs last-wins); a quote never closed, text after one, or a line break inside one; adjacent quotes;
whitespace at a quoted value's edge (dotenv 0.2.5–6.2.0 trim inside quotes); a control character other than a
literal tab inside quotes (stricter than the evidence requires — kept out for output-channel hygiene); CRLF
(bash keeps the `\r`); a BOM (bash reads it into the first word); a bare line (a command to a shell).

**Deliberately stricter than the evidence, recorded:** non-ASCII is admitted only inside quotes (the unquoted
set is the probed ASCII set, although the UTF-8 probe read unanimously; quoted non-ASCII is admitted by the
grammar and proven live by the in-suite matrix); a tab before a name (only spaces were probed); anything after
a closing quote, including whitespace (unprobed). Comment text is unrestricted: no claimed reader in range
reads it (the releases that did, dotenv 0.1.1–0.2.0, are outside the claimed range).

## The masked set

Per admitted line: the line's single unanimous decode — the unquoted characters as written, or the content
between the quotes — **plus**, for a quoted-empty line, the two-character form `''` or `""` that npm dotenv
15.0.0 alone reads. The generic masking rules apply on top: every form a check may print the value in
(escaped, stripped, parts, values named inside it) is masked; a number or yes/no word under a name that does
not say secret stays a readable setting. No reading depends on the environment; a declared `--env` value is
masked wherever the check prints it, under its declared name.

## The claimed readers

- **bash 3.2 as `/bin/sh`** (measured 3.2.57).
- **Node `--env-file`** — tested exactly: **v20.7.0, v20.20.2, v22.0.0, v22.16.0, v24.21.0, v26.10.0**.
  Anything broader (e.g. "v20.7–v26.10") is an expectation from the source-ported parser forms plus these six
  live points, not a survey. Recorded: v20.7.0 silently ignores an absolute `--env-file` path (the skill
  launches checks with `cwd=project`).
- **npm dotenv 0.4.0–18.0.4** — 87 stable releases, every one live-tested. The range begins at 0.4.0 because
  0.1.1–0.2.0 truncate any value at its second `=` (`A='x=y'` → `x`) and 0.1.1–0.3.0 strip quote characters
  anywhere in a value (`A="it's"` → `its`) — both diverge from every other claimed reader on legitimate
  literal values. Recorded limitation inside the range: **0.5.0** fails with empty environment state when
  `.env.<NODE_ENV>` is absent (its `load()` applies values only when both `.env` and the env-specific file
  load, so nothing is applied — fail-closed, never a wrong reading) and decodes normally in its two-file
  setup. Old releases' safe direction stands: dotenv ≤ 14.3.2 reads nothing for an `export` line.
- **python-dotenv 1.2.3** (official wheel; its metadata declares `requires-python >=3.10`, and its
  pure-Python code imported and ran correctly on this Mac's 3.9.6 — recorded honestly, not generalized).

(The 2026-09-27 release handoff's "84 of 99" count for this range was a miscount: the range holds 87 of the
99 tested releases, per the experiment's provenance table.)

## The evidence

- **The reader-compatibility experiment (2026-09-27)** — 107 readers × 83 fixtures + 5 two-file cases = 8,891
  recorded observations under `env -i`: bash sourcing; six Node versions; all 99 stable dotenv releases
  0.1.1–18.0.4 driven per era; the python-dotenv wheel. Sources, versions, sha256 and publisher digests in
  `~/Desktop/Vibe-to-Engineering/vibe-to-engineering-reader-compat-2026-09-27/` (`PROVENANCE.md`,
  `results.jsonl`, `analysis.txt`).
- **The in-suite differential matrix** (`tests/test_literal_matrix.py`) — the implemented grammar and masking
  logic against every claimed reader, live, over the admitted corpus, the combination cases with and without
  `export`, and the divergent corpus: every claimed reader's decode stays inside the masked set on every
  admitted form, and every divergent form refuses. Artifacts are prepared separately from test execution
  (`tests/reader_matrix_prepare.py`) by reusing the experiment's hash-verified copies or fetching the exact
  recorded versions, and are re-verified against `tests/reader_matrix_provenance.json` before reader execution.
  Archive hashes alone are insufficient: `tests/reader_artifacts.py` checks the actual extracted tree,
  imported files, entry paths and harness. Altered or extra files refuse (stale bytecode included);
  the Python reader runs with `-B`. Reader crashes, invalid/missing results, and harness failures are
  explicit NOT VERIFIED failures. A nonempty smoke fixture prevents an all-empty reader from passing;
  a missing or unverified reader is NOT VERIFIED, never a pass.
- **The boundary tests** (`tests/test_env_literal.py`) — the grammar itself, the end-to-end admission/refusal
  contract, Codex's brace case as a regression (with the real `/bin/sh` expansion re-proven), and the
  combination tests with and without `export` against the real local readers.

## Regression supersession mapping

The owner-approved rule: regressions are preserved where behavior stays supported; superseded expectations
become explicit refusal tests, each proving the check never launched (exit 2, no ran-marker, no evidence
file, the file named in the report, no secret text shown), with the reason recorded here and in a
`# SUPERSEDED (A1 literal boundary, 2026-09-27):` comment at each changed test. Refusal tests throughout were
retained — the boundary still refuses every one of those forms.

The handoff's recorded mapping listed only the headline tests; the owner then approved **full mechanical
supersession** (2026-09-27): every expectation directly contradicted by the grammar is converted, and each is
recorded below. Deviations from the handoff's "retained unchanged" notes are marked *.

**tests/test_evidence_readings.py**

- `test_a_yaml_tag_or_a_shell_expansion…` — the masked shell-expansion cases (arithmetic, `$((…))`, `$[…]`,
  `${#NAME}`, command output, same-line further assignments, `$$`/`$()` in single quotes) → refusal: a `$` or
  backtick anywhere in a value refuses; a line past one literal assignment refuses. YAML masked cases and all
  refused cases retained.
- `test_a_shell_value_is_read_with_the_shell_s_own_variables…` — all masked cases (the shell's own-variable
  readings) → refusal: every fixture holds `$`, an escape, a continued line, `+=`, `&`, or a
  multi-assignment/builtin-prefix line. Refusal cases retained.
- `test_a_reference_the_file_does_not_decide_is_computed_from_the_constructed_environment` — the computed
  cases (in both environments) and the "shell never reads SECRET" masked cases → refusal: `$` in a value.
  Still-refused cases (`:?`, readonly-then-assign) retained.
- `test_a_value_the_file_does_not_decide_stops_the_run_and_the_shell_reads_every_line_as_written` — the
  computed `~`/constructed-HOME and dotenv-quote cases, and the masked cases (array element, `${…}`, `$` in
  single quotes, arithmetic, CRLF, `~` with the file's HOME) → refusal. Refusal cases retained.
- `test_no_inherited_function_can_stand_in_for_a_command_under_the_constructed_environment` — the computed
  and control cases → refusal: bare command lines and `readonly` prefixes are not literal assignments. The
  D3 prohibition they demonstrated stands (childenv admits no `BASH_FUNC_*`); the standalone still-refused
  case retained.
- `test_json_text_in_a_env_file_never_stands_in_for_the_shell_reading_it_refuses` — *the masked "JSON line
  the shell reading accepts" case → refusal (a `{`-led line is no literal assignment; a `.env` file is never
  read as JSON). The refused JSON cases retained. (Recorded "retained" in the handoff; one masked case was
  mechanically contradicted.)
- `test_a_construct_in_a_part_the_shell_skips_never_stops_the_run…` and
  `test_valid_syntax_in_a_part_the_shell_skips_is_masked_and_stops_the_run_where_the_shell_reads_it` (the two
  B4 tests) — all masked skipped-part cases → refusal: `${…}` refuses regardless of skip analysis. All
  refused cases retained.
- `test_a_home_folder_the_user_database_decides_stops_the_run` (B5) — the masked `~`-with-file's-HOME case →
  refusal (`~` at value start). The `~name` refusals retained.
- `test_a_value_python_dotenv_takes_from_the_environment_is_computed_never_guessed` (B6) — the fill-in,
  parent-environment and file-alone masked/computed cases → refusal: `${…}` even in single quotes and `$'…'`,
  escaped `$`, bare lines, quoted/dotted keys. *One case kept green as masked: "a name the file sets" —
  `DB_PASSWORD=from-file` is literal.
- `test_a_name_followed_by_anything_but_an_operator_stops_the_run_where_the_shell_reads_it` — the masked
  skipped-part case → refusal (`$`). Bad-substitution refusals retained.
- `test_a_backslash_before_a_byte_bash_keeps_its_escape_byte_for_stops_the_run` — the masked cases → refusal
  (backslash in double quotes, control bytes). The DEL/SOH refusals retained.
- Unchanged: the YAML template test, the BOM test (the boundary keeps the BOM refusal), the unclosed-quote
  test.

**tests/test_evidence_node.py** *(recorded "retained unchanged" in the handoff; mechanically superseded)*

- `test_a_key_a_node_loader_reads_that_the_environment_already_holds_stops_the_run` and
  `test_each_key_the_real_node_keeps_an_inherited_value_for_stops_the_run` — NODE-PRECEDENCE is superseded by
  the boundary: every quoted/tabbed/space-bearing key, colon separator and bare-line fixture refuses before
  launch, so such a file no longer reaches a check for Node to read at all (the real-Node probing was dropped
  with the modeling). *Three comment-only fixtures (`#DB_PASSWORD=…` after a literal line) are inside the
  grammar and keep their run-and-masked expectations; the `--env`-validation subtest is unaffected and kept
  exactly.

**tests/test_evidence_stage1.py**

- `test_old_npm_dotenv_interpolation_is_computed_from_known_inputs` → renamed
  `test_old_npm_dotenv_interpolation_is_refused_by_the_boundary`: interpolation is refused outright (a `$`
  anywhere in a value, single quotes included), so the ported model is no longer wired (nothing in the .env
  reader calls `nodekeys.py` now) and the cases are end-to-end refusal proofs with a declared value present.

**tests/test_final_review_r1.py**

- `test_a_shell_reading_the_file_does_not_decide_is_computed_from_the_constructed_environment` (the R1-F7
  mechanism) → renamed `…_is_refused_by_the_boundary`: declared and undeclared reference cases both refuse.
- `test_the_reader_alone_without_the_mapping_still_refuses` — the with-mapping half superseded: the reader
  refuses a reference with or without the mapping (`environ` is no longer consulted).

**tests/test_stage1_acceptance.py**

- `test_a_real_shell_reads_only_what_the_model_reads` — rewritten over the literal subset (a real `/bin/sh`
  sources an admitted file and reads exactly the boundary's decode, under plain and hostile parents); the
  arithmetic, `${#NAME}` and `~` cases became refusal assertions, per the mapping.

**tests/test_evidence.py** *(not enumerated in the handoff's mapping; mechanically superseded)*

- The contradicted .env cases across seven methods (inline comments after unquoted values, multiline quoted
  values, duplicate names, bare token lines, unquoted `&`/`;`/spaces/`#`, `$` or `\` in quoted values, quoted
  or digit-leading names, non-ASCII unquoted values) → refusal, with the same proof shape.
- *Six admitted-but-reclassified fixtures (bare-token readings the grammar abolished — e.g. `KEYA====` is now
  the ordinary assignment NAME=`KEYA`, value `====`) keep running with corrected exact-output expectations,
  recorded in the tests' supersession comments. If such lines should refuse instead, that is a grammar
  question for a future owner decision, not a test matter.

## What stays reachable, and what does not

`nodekeys.py` (the ported Node/dotenv loader profiles and the old-npm interpolation model) and the shell
word/expansion machinery in `secretforms.py` are no longer called by the `.env` reader. They are retained in
the tree unmodified as the provenance record of the rounds that built them; the documentation claims no
capability from them. Physical removal is a separate owner decision (checklist B1), not part of this slice.
The supported-check registry (`references/supported-checks.md`) is unaffected: the runner gate and its Node
version bounds stand.

## A1 corrective round (2026-09-28)

The owner's request to fix the four independently demonstrated A1 findings authorizes the narrow
single-quoted grammar correction: consecutive backslashes now refuse. The earlier A1 grammar allowed
these bytes, but bash and python-dotenv disagree: two backslashes become one in python-dotenv, exposing
an unmasked decoded secret. This is an admission correction, not restoration of the retired reader models.
Single literal backslashes before `n`, ordinary quoted Unicode and interior TAB remain supported.
Unicode whitespace/U+FEFF at quoted edges and all Unicode Cc controls except TAB also refuse, fulfilling
the existing rules beyond ASCII. The remaining language and claimed-reader set are unchanged.

`tests/test_a1_boundary_regressions.py` retains the exact leak and Unicode cases as pre-launch refusal
regressions, with positive end-to-end controls. No old supported test was removed or weakened for these
corrections. `tests/test_a1_matrix_regressions.py` exercises execution failures and tampered reader
artifacts. The live matrix re-proves the divergent backslash/NBSP readings, rejects the newly excluded
forms, and retains the approved 0.5.0 and old-export no-read limitations. Corpus counts are derived from
the code rather than inherited from the first handoff.

Artifact checks establish pre-execution provenance. They do not claim isolation from a concurrent writer
or provide the separately planned A2 runner-enrollment guarantee. Downloads remain a preparation-only
operation. If an old prepared directory contains changed files or generated bytecode, preserve it and
prepare into a fresh directory; tests never repair it silently.

These corrections remain uncommitted and require independent re-review. A2/A3/A4, B/C/D and release
acceptance are outside this repair; no whole-skill readiness is claimed.
