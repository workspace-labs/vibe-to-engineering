"""Native prerequisites for the reviewed macOS ARM64 reader matrix.

Keep executable identity checks separate from archive integrity checks, so synthetic
artifact tests do not accidentally depend on the host's shell or Node installation.
"""
import platform
import re
import shutil
import subprocess
import sys


def reader_prerequisites():
    """Return (local Node path, unmet prerequisites), without writing or downloading."""
    if sys.platform != 'darwin' or platform.machine() != 'arm64':
        return None, ['the reviewed reader matrix requires macOS arm64']
    problems = []
    probe_env = {'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'LC_ALL': 'C'}
    try:
        shell = subprocess.run(['/bin/sh', '--version'], env=probe_env,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if shell.returncode or not re.search(br'GNU bash, version 3\.2(?:\.|\()', shell.stdout):
            problems.append('/bin/sh is not the claimed GNU bash 3.2 reader')
    except (OSError, subprocess.TimeoutExpired):
        problems.append('the claimed /bin/sh (bash 3.2) reader cannot be verified')
    local = shutil.which('node')
    if not local:
        problems.append('no local Node (the v20.20.2 claimed point)')
    else:
        try:
            node = subprocess.run([local, '--version'], env=probe_env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if node.returncode or node.stdout.strip() != b'v20.20.2':
                problems.append('the local Node does not verify as the claimed v20.20.2')
        except (OSError, subprocess.TimeoutExpired):
            problems.append('the claimed local Node v20.20.2 cannot be verified')
    return local, problems
