#!/usr/bin/env python3
"""Prepare the isolated reader-artifact directory for tests/test_literal_matrix.py — the v0.1 literal .env
boundary's differential matrix. This is a STANDALONE step, deliberately separate from test execution: nothing
downloads during a test run.

    python3 tests/reader_matrix_prepare.py [target-dir]     (default: /tmp/v2e-reader-matrix)

For every artifact in tests/reader_matrix_provenance.json (npm dotenv 0.4.0–18.0.4, Node v20.7.0, v22.0.0,
v22.16.0, v24.21.0, v26.10.0, the python-dotenv 1.2.3 wheel):

1. REUSE the 2026-09-27 experiment's working copy (/tmp/v2e-reader-compat.zVqLvR/artifacts) when the file there
   hashes to the recorded sha256 — the saved evidence, not a new download; otherwise
2. FETCH the exact artifact from the recorded URL (network, this step only) and verify the same sha256.

Anything that fails verification stops the preparation — the matrix test never sees an unverified artifact.
Existing extractions are verified file-for-file against the archive before reuse; changed files, links,
extra files (including stale Python bytecode), or a redirected entry refuse. Use a new target directory rather
than overwriting a refused one. The matrix also verifies its actual harness against the repository copy.

The artifacts are then extracted under the target directory (each dotenv release's real entry file resolved from
its own package.json "main", each Node dist's bin/node, the wheel unzipped), tests/reader_matrix_harness.js is
copied beside them (byte-identical to the experiment's v3 harness — the bytes, not a copy by reference), and
manifest.json records the resolved entry paths and the provenance of each artifact (reused or fetched).
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile

sys.dont_write_bytecode = True

from reader_artifacts import verify_extraction, entry_path, extraction
from reader_platform import reader_prerequisites

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROVENANCE = json.load(open(os.path.join(ROOT, "tests", "reader_matrix_provenance.json")))
COMPAT = "/tmp/v2e-reader-compat.zVqLvR/artifacts"   # the experiment's working copy, reused when it verifies
TARGET = sys.argv[1] if len(sys.argv) > 1 else "/tmp/v2e-reader-matrix"


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact(name, meta, target):
    """The artifact file inside the target dir, verified against the recorded sha256 — reused from the
    experiment's working copy when it verifies, fetched from the recorded URL otherwise."""
    dest = os.path.join(target, "artifacts", meta["file"])
    if os.path.exists(dest) and sha256(dest) == meta["sha256"]:
        return "kept"
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    reuse = os.path.join(COMPAT, meta["file"])
    if os.path.exists(reuse) and sha256(reuse) == meta["sha256"]:
        shutil.copyfile(reuse, dest)
        return "reused (the experiment's verified copy)"
    with urllib.request.urlopen(meta["url"]) as response:   # nosec — the recorded URL, verified below
        data = response.read()
    staging = dest + ".part"
    with open(staging, "wb") as stream:
        stream.write(data)
    if sha256(staging) != meta["sha256"]:
        os.remove(staging)
        raise SystemExit("sha256 mismatch for %s from %s — refusing to prepare an unverified reader" % (name, meta["url"]))
    os.replace(staging, dest)
    return "fetched (recorded URL, hash-verified)"


def main():
    _, problems = reader_prerequisites()
    if problems:
        raise SystemExit('NOT VERIFIED: ' + '; '.join(problems) +
                         ' — no reader artifacts were written or downloaded')
    target = os.path.abspath(TARGET)
    entries, sources = {}, {}
    for name in sorted(PROVENANCE["artifacts"]):
        meta = PROVENANCE["artifacts"][name]
        sources[name] = artifact(name, meta, target)
    for name in sorted(PROVENANCE["artifacts"]):
        path = os.path.join(target, "artifacts", PROVENANCE["artifacts"][name]["file"])
        dest = extraction(target, name)
        if not dest.exists():
            os.makedirs(dest)
            if name == "python-dotenv-1.2.3":
                zipfile.ZipFile(path).extractall(dest)
            else:
                subprocess.run(["tar", "-xzf", path, "-C", str(dest)], check=True)
        # Never reuse an unchecked extraction. Refuse rather than overwrite somebody else's files.
        verify_extraction(path, dest)
        entries[name] = str(entry_path(dest, name))
    shutil.copyfile(os.path.join(ROOT, "tests", "reader_matrix_harness.js"),
                    os.path.join(target, "harness.js"))
    with open(os.path.join(target, "manifest.json"), "w") as stream:
        json.dump({"entries": entries, "sources": sources,
                   "provenance": "tests/reader_matrix_provenance.json (sha256 re-verified at preparation)"},
                  stream, indent=1, sort_keys=True)
    print("prepared %d readers in %s" % (len(entries), target))
    for name in sorted(sources):
        print("  %-22s %s" % (name, sources[name]))


if __name__ == "__main__":
    main()
