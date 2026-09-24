"""Files git ignores: watched, not saved (G10).

Each checkpoint records every ignored file by name, and — outside dependency, build-output and cache folders — a
fingerprint of its bytes, so that diff and restore can report one that changed although no checkpoint holds it. A
file that holds secrets gets a keyed fingerprint (fingerprint_key), which tells nothing about the file to anyone
without the key. The same lists say which ignored files evidence.py reads for masking.
"""

import fnmatch
import hashlib
import hmac
import os
import secrets
import stat
from gitrun import Fail, is_link, local_path, show

DEFAULT_EXCLUDES = (
    "node_modules/", "bower_components/", ".venv/", "venv/", "__pycache__/", "*.pyc",
    ".pytest_cache/", ".mypy_cache/", ".tox/", ".gradle/", ".next/", ".nuxt/",
    ".parcel-cache/", ".turbo/", ".DS_Store", "Thumbs.db",
)
CONTENTS_MARK = "ignored-contents: "  # ...and the one that records each watched ignored file's size and fingerprint
KEY_NAME = "fingerprint.key"  # in the state folder: the key that fingerprints files holding secrets (G10)
# Ignored files that change by themselves and are too many to fingerprint: dependency, build-output and cache folders,
# and the default excluded files. Every other ignored file is watched for changes (G10).
UNWATCHED_FOLDERS = frozenset([entry[:-1] for entry in DEFAULT_EXCLUDES if entry.endswith("/")]
                              + ["dist", "build", "target", "coverage", ".cache"])
UNWATCHED_FILES = tuple(entry for entry in DEFAULT_EXCLUDES if not entry.endswith("/"))
# Files that hold secrets are never read: their fingerprint is their modification time, not a hash of their bytes.
SECRET_FILES = (".env", ".env.*", "*.env", "*.pem", "*.key", "*.p12", "*.pfx", "*.keystore", "*.jks", "id_rsa*",
                "id_ecdsa*", "id_ed25519*", "*credential*", "*secret*")


def fingerprint_key(key_path):
    """The key that fingerprints files holding secrets (G10): 32 random bytes made on first use, kept in the state
    folder next to the store and readable by the owner only. A keyed fingerprint in a checkpoint's message tells
    nothing about the file to anyone who has the message but not this key — a plain hash would let a short secret be
    guessed offline. Never copied into a checkpoint: the state folder is excluded from every one."""
    path = key_path
    if is_link(str(path)) or (os.path.lexists(str(path)) and not path.is_file()):
        raise Fail("%s is a link or not a plain file. Nothing was changed" % path)
    if not path.exists():
        try:
            handle = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)  # O_EXCL: never through a link
        except FileExistsError:
            pass  # another command made it first
        else:
            with os.fdopen(handle, "w") as out:
                out.write(secrets.token_hex(32) + "\n")
    try:
        key = bytes.fromhex(path.read_text(encoding="ascii").strip())
    except (OSError, ValueError) as error:
        raise Fail("cannot read the fingerprint key %s (%s)" % (path, error))
    if len(key) < 16:
        raise Fail("the fingerprint key %s is too short to trust" % path)
    return key


def watched_contents(project, ignored, key_path):
    """name -> [size, fingerprint] for every ignored file outside dependency, build-output and cache folders, so that
    diff and restore can tell when one changed, though no checkpoint holds it (G10). The fingerprint is the SHA-256 of
    the bytes — for a file that holds secrets, a keyed one (HMAC-SHA256 with fingerprint_key), so the checkpoint's
    message gives away nothing about the file. Neither reads a byte into any output. A watched file that cannot be
    read stops the command: a change to it could not be noticed."""
    contents, key = {}, None
    for rel in ignored:
        parts = os.fsdecode(rel).split("/")
        if rel.endswith(b"/") or UNWATCHED_FOLDERS.intersection(parts[:-1]) or any(
                fnmatch.fnmatchcase(parts[-1], pattern) for pattern in UNWATCHED_FILES):
            continue
        path = local_path(project, rel)
        secret = any(fnmatch.fnmatchcase(parts[-1].lower(), pattern) for pattern in SECRET_FILES)
        if secret and key is None:
            key = fingerprint_key(key_path)
        digest = hmac.new(key, digestmod="sha256") if secret else hashlib.sha256()
        try:
            info = os.lstat(path)
            if stat.S_ISLNK(info.st_mode):
                digest.update(os.fsencode(os.readlink(path)))
            else:
                with open(path, "rb") as handle:
                    for piece in iter(lambda: handle.read(1 << 20), b""):
                        digest.update(piece)
        except OSError as error:
            raise Fail("cannot read %s, a file git ignores (%s) — without reading it, a change to it could not be "
                       "noticed" % (show(rel), error.strerror or error))
        contents[os.fsdecode(rel)] = [info.st_size, ("hmac:" if secret else "sha256:") + digest.hexdigest()]
    return contents


def changed_since(before, contents):
    """Watched ignored files whose contents differ from what a checkpoint recorded, or cannot be compared with it
    (G10): (name, then, now), each side its [size, fingerprint] record or None where that side recorded nothing. Two
    fingerprints of the bytes are compared; a record of only a modification time (a checkpoint from before keyed
    fingerprints) or no record at all says nothing about the bytes, so such a file is listed as one whose change
    cannot be told — never called unchanged. `before` is what the checkpoint recorded (its CONTENTS_MARK line) and
    `contents` what the other side holds, each None where nothing was recorded."""
    changed = []
    for name in sorted(set(before or ()) | set(contents or ())):
        then, now = (before or {}).get(name), (contents or {}).get(name)
        if before is not None and contents is not None and (then is None or now is None):
            continue  # gone since the checkpoint (gone_since reports it), or new since
        comparable = (then is not None and now is not None
                      and not then[1].startswith("mtime:") and not now[1].startswith("mtime:"))
        if not comparable or then != now:
            changed.append((name, then, now))
    return changed


def report_changed(changed, label, other="the current files"):
    """The list changed_since found, one line each: `changed` with the sizes, or `unknown` with what is missing —
    `label` names the checkpoint, `other` the side it is compared with."""
    print("files git ignores whose contents changed since %s, or cannot be compared with it — checkpoints do not "
          "hold them, so their earlier contents cannot be restored from here:" % label)
    for name, then, now in changed[:40]:
        if then is None or now is None:
            print("  unknown  %s  (%s recorded nothing about its contents)" % (name, label if then is None else other))
        elif then[1].startswith("mtime:") or now[1].startswith("mtime:"):
            print("  unknown  %s  (%s recorded only its modification time, which says nothing about its contents)"
                  % (name, label if then[1].startswith("mtime:") else other))
        else:
            print("  changed  %s  (%s)" % (name, "the same size" if then[0] == now[0]
                                           else "%d bytes, was %d" % (now[0], then[0])))
    if len(changed) > 40:
        print("  … and %d more" % (len(changed) - 40))
