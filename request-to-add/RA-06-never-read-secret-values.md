# RA-06 — report where secrets are, never what they are

## What is missing

INSPECT says `Read-only means: read files, …` (`SKILL.md:77`), and the standard's configuration check says `search for literals such as URLs, ports and keys` (`engineering-standard.md:105`). Nothing says how to handle a secret once found. An agent that follows the text literally opens `.env` and prints committed keys. The values then land in its transcript, the plan, the PDF and the ledger. Those files are shared with a reviewer (Codex) and may be sent around.

## How it showed up

Spendly's ignored `.env` holds `SECRET_KEY` and `EXCHANGE_API_KEY`. `config.py:14` commits a key-shaped value. In this run the agent printed `.env` with every value replaced (`sed 's/=.*/=<redacted>/'`), and the plan names `EXCHANGE_API_KEY` and `config.py:14` without the value. That was the agent's own choice; the skill doesn't require it.

## Where

- `SKILL.md:77` → `Read-only means: read files, list folders, search, …`
- `references/engineering-standard.md:105` → `- **Check:** search for literals such as URLs, ports and keys, and for every place the environment is read.`
- `references/engineering-standard.md:106` → `- A committed secret is a security finding: report it at once, in plain words. …`
- `SKILL.md`, "Files written in the project": the plan, ledger and evidence have no rule against holding secrets.

## Added means

1. A rule in INSPECT and in C9: files that hold secrets (`.env*`, key files, credential stores, anything the project's ignore rules mark as secret) are read **for their key names only**, never their values. A committed secret is reported by file, line and key name, and at most by the first 4 characters of the value if the owner needs to recognize which key it is.
2. No value that looks like a secret is written into the plan, the PDF, the ledger or `evidence/`. Check output saved as evidence is scanned for such values and masked before it's written.
3. A protocol test checks that the rule is in `SKILL.md` and the standard. A test with a fake key in a sample `.env` and in check output checks that it doesn't appear in evidence.

## Ideas (not tried)

- A tiny masking helper in `checkpoint.py` (or a new script) that evidence goes through: it matches `KEY=`, `sk_…`, `-----BEGIN … PRIVATE KEY-----` and long high-entropy tokens.
