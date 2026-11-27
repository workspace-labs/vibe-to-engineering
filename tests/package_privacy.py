"""Check public source paths and bytes; optionally check local reachable Git history.

Report counts only. An optional private JSON name map outside the checkout supplies
the names to look for. Run this on the development checkout or a source archive.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import unicodedata


HOME_PATH = re.compile(rb"~/" + rb"Desktop|/" + rb"Users/[a-z]", re.I)


def git(root, *args):
    env = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_NO_LAZY_FETCH": "1",
           "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}
    if os.name == "nt":
        system = Path(os.environ["SystemRoot"])
        programs = Path(os.environ.get("ProgramFiles", system.anchor + "Program Files"))
        env.update(SystemRoot=str(system), PATH=os.pathsep.join(map(str, (programs / "Git" / "cmd",
                                                                           system / "System32", system))))
    else:
        env["PATH"] = "/usr/bin:/bin"
    executable = shutil.which("git", path=env["PATH"])
    if not executable:
        raise OSError("system Git unavailable")
    return subprocess.run([executable, "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull,
                           *args], cwd=root, env=env, stdout=subprocess.PIPE,
                          stderr=subprocess.DEVNULL, check=True).stdout


def private_terms(root, path):
    if not path:
        return ()
    scripts = Path(__file__).resolve().parents[1] / "skills" / "vibe-to-engineering" / "scripts"
    sys.path.insert(0, str(scripts))
    try:
        from private_names import load_name_map
        return tuple(load_name_map(path, root).public)
    finally:
        sys.path.remove(str(scripts))


def matches(data, terms):
    if HOME_PATH.search(data):
        return True
    if terms:
        decoded = unicodedata.normalize("NFC", data.decode("utf-8", errors="replace")).casefold()
        return any(term in decoded for term in terms)
    return False


def source_paths(root):
    if (root / ".git").exists():
        raw = git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
        return (Path(os.fsdecode(name)) for name in raw.split(b"\0") if name)
    paths = []
    for directory, folders, files in os.walk(root):
        for folder in list(folders):
            child = Path(directory, folder)
            if folder in (".git", "__pycache__") or child.is_symlink():
                folders.remove(folder)
                if child.is_symlink():
                    paths.append(child.relative_to(root))
        paths.extend(Path(directory, name).relative_to(root) for name in files if not name.endswith(".pyc"))
    return paths


def scan_current(root, terms=()):
    counts = {"entries": 0, "matching_paths": 0, "matching_contents": 0, "unreadable": 0}
    for rel in source_paths(root):
        path = root / rel
        if any((root / parent).is_symlink() for parent in rel.parents):
            counts["unreadable"] += 1
            continue
        try:
            mode = path.lstat().st_mode
        except FileNotFoundError:
            continue  # tracked deletion in the working tree
        counts["entries"] += 1
        counts["matching_paths"] += matches(os.fsencode(rel.as_posix()), terms)
        if stat.S_ISLNK(mode):
            data = os.fsencode(os.readlink(path))
        elif stat.S_ISREG(mode):
            data = path.read_bytes()
        else:
            counts["unreadable"] += 1
            continue
        counts["matching_contents"] += matches(data, terms)
    return counts


def scan_history(root, terms=()):
    # Read objects and tree names directly; do not checkout, apply filters, or print
    # commit metadata, historical pathnames, matches or the supplied private names.
    if not (root / ".git").exists():
        return {"availability": "source archive; history unavailable"}
    commits = git(root, "rev-list", "--all").splitlines()
    names = set()
    blobs = set()
    for revision in commits:
        entries = git(root, "ls-tree", "-r", "-z", revision).split(b"\0")
        for entry in filter(None, entries):
            meta, name = entry.split(b"\t", 1)
            _, kind, oid = meta.split()
            names.add(name)
            if kind == b"blob":
                blobs.add(oid)
    def matching_objects(kind, ids):
        return sum(matches(git(root, "cat-file", kind, oid), terms) for oid in ids)
    shallow = git(root, "rev-parse", "--is-shallow-repository").strip() == b"true"
    return {"availability": "shallow local history" if shallow else "local reachable commits",
            "commits": len(commits), "unique_paths": len(names), "unique_blobs": len(blobs),
            "matching_paths": sum(matches(name, terms) for name in names),
            "matching_blobs": matching_objects("blob", blobs),
            "matching_commits": matching_objects("commit", commits)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--name-map", type=Path)
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        if not (root / ".git").exists() and not (root / "skills").is_dir():
            raise ValueError("expected a development checkout or a source archive")
        terms = private_terms(root, args.name_map)
        current = scan_current(root, terms)
        report = {"current": current, "declared_names": len(terms)}
        if args.history:
            report["history"] = scan_history(root, terms)
        print(json.dumps(report, indent=2))
        history = report.get("history", {})
        findings = any(value for part in (current, history)
                       for key, value in part.items() if key.startswith("matching_"))
        incomplete = not current["entries"] or current["unreadable"] or (
            args.history and history["availability"] != "local reachable commits")
        return int(bool(findings or incomplete))
    except (OSError, ValueError, subprocess.SubprocessError):
        print("Privacy check incomplete; source, history or external name map unavailable.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
