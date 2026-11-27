"""Build a clean validation worker environment and identify its native prerequisites."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

# Git substitutes this token when exporting a reviewed revision with git archive.
ARCHIVE_REVISION = '$Format:%H$'


def file_digest(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as source:
        for chunk in iter(lambda: source.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def worker_environment(base, native, parent):
    home, temp = base / 'home', base / 'temp'
    tools = base / 'tools'
    tools.mkdir(mode=0o700)
    drive, tail = os.path.splitdrive(str(home))
    env = dict(HOME=str(home), USERPROFILE=str(home), HOMEDRIVE=drive, HOMEPATH=tail,
               APPDATA=str(home / 'AppData' / 'Roaming'), LOCALAPPDATA=str(home / 'AppData' / 'Local'),
               TMP=str(temp), TEMP=str(temp), TMPDIR=str(temp), GIT_CONFIG_GLOBAL=str(home / 'gitconfig'),
               GIT_CONFIG_NOSYSTEM='1', PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1',
               V2E_VALIDATION_ROOT=str(base))
    if os.name == 'nt':
        system = Path(parent['SystemRoot'])
        programs = Path(parent.get('ProgramFiles', system.anchor + 'Program Files'))
        env.update(SystemRoot=str(system), WINDIR=str(system), COMSPEC=str(system / 'System32' / 'cmd.exe'),
                   PATHEXT='.COM;.EXE;.BAT;.CMD')
        folders = [system / 'System32', system, programs / 'Git' / 'cmd']
    else:
        folders = [Path(folder) for folder in ('/usr/bin', '/bin', '/usr/sbin', '/sbin')]
    if native:
        env.update(V2E_REQUIRE_NODE='1', V2E_REQUIRE_MATRIX='1')
        for name in ('V2E_NODE', 'V2E_BROWSER', 'V2E_READER_MATRIX_DIR'):
            value = parent.get(name)
            if value and Path(value).is_absolute():
                env[name] = str(Path(value).resolve())
        if 'V2E_NODE' in env and os.access(env['V2E_NODE'], os.X_OK) and Path(env['V2E_NODE']).is_file():
            (tools / 'node').symlink_to(env['V2E_NODE'])
        # Make only the two needed Poppler programs visible from common macOS installations.
        for name in ('pdfinfo', 'pdftotext'):
            path = shutil.which(name, path='/usr/bin:/opt/homebrew/bin:/usr/local/bin')
            if path:
                (tools / name).symlink_to(path)
    env['PATH'] = os.pathsep.join(str(path) for path in [tools, *folders])
    return env


def source_identity(root, env):
    # A dirty checkout or a locally edited export must distinguish the tested bytes from
    # the named commit. Hash the same source/docs inputs the harness copies, before redirection.
    files = [*root.glob('*.md'), root / 'LICENSE']
    for name in ('skills', 'tests'):
        files.extend(p for p in (root / name).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode('utf-8') + b'\0')
        digest.update(bytes.fromhex(file_digest(path)))
    result = {'input_sha256': digest.hexdigest(), 'revision': None, 'source': 'unversioned or unavailable'}
    if re.fullmatch('[0-9a-f]{40,64}', ARCHIVE_REVISION):
        result.update(revision=ARCHIVE_REVISION, source='git archive')
        return result
    git = shutil.which('git', path=env['PATH'])
    if git and (root / '.git').exists():
        def git_output(*args):
            return subprocess.check_output([git, '--no-optional-locks', '-C', str(root), *args], env=env,
                                           stderr=subprocess.DEVNULL, text=True, timeout=15).strip()
        try:
            result.update(revision=git_output('rev-parse', '--verify', 'HEAD'), source='checkout',
                          dirty=bool(git_output('status', '--porcelain', '--untracked-files=normal')))
        except (OSError, subprocess.SubprocessError):
            pass
    return result


def executable_identity(path, env):
    info = {'path': path, 'sha256': None, 'version': None}
    if path:
        try:
            info['sha256'] = file_digest(path)
            result = subprocess.run([path, '--version'], env=env, cwd=env['TMPDIR'], capture_output=True,
                                    text=True, timeout=15)
            if result.returncode == 0:
                lines = (result.stdout or result.stderr).strip().splitlines()
                info['version'] = lines[0] if lines else None
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return info


def validation_identity(root, env, native):
    identity = {'host': {'platform': platform.platform(), 'machine': platform.machine()},
                'python': {'version': sys.version, 'executable': sys.executable},
                'source': source_identity(root, env)}
    problems = []
    if native:
        for key, name in (('node', 'V2E_NODE'), ('browser', 'V2E_BROWSER')):
            info = executable_identity(env.get(name), env)
            identity[key] = info
            if not info['sha256'] or not info['version']:
                problems.append('set %s to an absolute executable with a working --version' % name)
        if identity['node']['version'] and identity['node']['version'] != 'v20.20.2':
            problems.append('V2E_NODE must verify as v20.20.2')
        target = env.get('V2E_READER_MATRIX_DIR')
        bundle = {'directory': target, 'manifest_sha256': None, 'harness_sha256': None,
                  'provenance_sha256': file_digest(root / 'tests/reader_matrix_provenance.json')}
        identity['readers'] = bundle
        try:
            folder = Path(target)
            bundle['manifest_sha256'] = file_digest(folder / 'manifest.json')
            bundle['harness_sha256'] = file_digest(folder / 'harness.js')
            bundle['archive_count'] = len(json.loads((folder / 'manifest.json').read_text())['entries'])
            if bundle['harness_sha256'] != file_digest(root / 'tests/reader_matrix_harness.js'):
                problems.append('prepared harness differs from this checkout; prepare a fresh reader directory')
        except (TypeError, ValueError, OSError, KeyError):
            problems.append('set V2E_READER_MATRIX_DIR to the prepared reader directory')
        for name in ('git', 'cc', 'pdfinfo', 'pdftotext'):
            if not shutil.which(name, path=env['PATH']):
                problems.append('required native validation tool missing: ' + name)
    return identity, problems
