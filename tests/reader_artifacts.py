"""Offline provenance checks for the matrix's *executed* files, not just its archive cache.

Archive hashes come from the checked-in provenance. Every extracted file/link and its entry path must
match that archive; extra files (including stale Python bytecode) refuse. No downloads or execution.
This is pre-execution integrity verification, not protection against a concurrent writer.
"""
import hashlib
import json
import os
import posixpath
import stat
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(1 << 20), b''):
        h.update(block)
    return h.hexdigest()


def file_hash(path):
    with open(path, 'rb') as stream:
        return digest(stream)


def relative(name):
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or not p.parts:
        raise ValueError('unsafe archive member path')
    return str(p)


def records(archive):
    """Expected path -> (kind, hash/link/None, executable-bit) from a verified archive."""
    result = {}
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            for member in source.infolist():
                name = relative(member.filename)
                mode = member.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise ValueError('unsupported symlink in wheel')
                with source.open(member) as stream:
                    value = ('dir', None, False) if member.is_dir() else ('file', digest(stream), False)
                if name in result:
                    raise ValueError('duplicate archive member')
                result[name] = value
    else:
        with tarfile.open(archive, 'r:*') as source:
            for member in source:
                name = relative(member.name)
                if member.isdir():
                    value = ('dir', None, False)
                elif member.isfile():
                    with source.extractfile(member) as stream:
                        value = ('file', digest(stream), bool(member.mode & 0o111))
                elif member.issym():
                    target = posixpath.normpath(posixpath.join(posixpath.dirname(name), member.linkname))
                    relative(target)
                    if member.linkname.startswith('/'):
                        raise ValueError('absolute archive symlink')
                    value = ('link', member.linkname, False)
                else:
                    raise ValueError('unsupported archive member type')
                if name in result:
                    raise ValueError('duplicate archive member')
                result[name] = value
    for name in list(result):
        for parent in PurePosixPath(name).parents:
            if str(parent) != '.':
                existing = result.setdefault(str(parent), ('dir', None, False))
                if existing[0] != 'dir':
                    raise ValueError('archive parent is not a directory')
    return result


def extraction(target, name):
    return Path(target) / 'extract' / ('pydotenv' if name == 'python-dotenv-1.2.3' else name)


def verify_extraction(archive, dest):
    """Check all files, implicit directories, symlinks and executable bits, without following links."""
    dest = Path(dest)
    if not dest.is_dir() or dest.is_symlink() or dest.parent.is_symlink():
        raise ValueError('missing or redirected extraction directory')
    expected = records(archive)
    actual = set()
    for folder, dirs, files in os.walk(dest, followlinks=False):
        for child in dirs + files:
            path = Path(folder) / child
            name = path.relative_to(dest).as_posix()
            actual.add(name)
            wanted = expected.get(name)
            if wanted is None:
                raise ValueError('unexpected extracted file: %s' % name)
            kind, value, executable = wanted
            mode = path.lstat().st_mode
            if kind == 'link':
                if not stat.S_ISLNK(mode) or os.readlink(path) != value:
                    raise ValueError('changed extracted link: %s' % name)
            elif kind == 'dir':
                if not stat.S_ISDIR(mode):
                    raise ValueError('changed extracted directory: %s' % name)
            elif (not stat.S_ISREG(mode) or file_hash(path) != value
                  or bool(mode & 0o111) != executable):
                raise ValueError('changed extracted file: %s' % name)
    if actual != set(expected):
        raise ValueError('missing extracted files')


def entry_path(dest, name):
    if name.startswith('dotenv-'):
        main = json.loads((dest / 'package/package.json').read_text()).get('main', 'index.js')
        entry = dest / 'package' / relative(main)
    elif name.startswith('node-'):
        entry = dest / (name + '-darwin-arm64') / 'bin/node'
    else:
        entry = dest
    if not entry.exists() or not entry.resolve().is_relative_to(dest.resolve()):
        raise ValueError('invalid reader entry')
    return entry


def verified_entries(target, provenance, harness):
    target = Path(target)
    if target.is_symlink() or (target / 'extract').is_symlink():
        raise ValueError('redirected prepared-reader directory')
    manifest = json.loads((target / 'manifest.json').read_text())['entries']
    if set(manifest) != set(provenance):
        raise ValueError('manifest reader set differs from provenance')
    if (target / 'harness.js').is_symlink() or (target / 'harness.js').read_bytes() != Path(harness).read_bytes():
        raise ValueError('changed reader harness')
    entries = {}
    for name, meta in sorted(provenance.items()):
        archive = target / 'artifacts' / meta['file']
        if archive.is_symlink() or file_hash(archive) != meta['sha256']:
            raise ValueError('%s: archive hash mismatch' % name)
        dest = extraction(target, name)
        verify_extraction(archive, dest)
        entry = entry_path(dest, name)
        if os.path.abspath(manifest[name]) != os.path.abspath(entry):
            raise ValueError('%s: redirected manifest entry' % name)
        entries[name] = str(entry)
    return entries
