"""Find and read the evidence wrapper's protected sources before launching a check."""
import codecs
import fnmatch
import os
import stat

from checkpoint import STATE_DIR
from gitrun import Fail, is_link
from watched import SECRET_FILES, UNWATCHED_FOLDERS

BOMS = ((codecs.BOM_UTF8, "utf-8-sig"), (codecs.BOM_UTF32_LE, "utf-32"), (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF16_LE, "utf-16"), (codecs.BOM_UTF16_BE, "utf-16"))  # UTF-32 first: its mark begins like UTF-16's
LARGEST_SECRET_FILE = 1 << 20  # a secret file bigger than this is not a secret file


def secret_text(path):
    """A secret file's text: decoded by its byte order mark (UTF-8, UTF-16, UTF-32), otherwise as UTF-8 — the mark
    kept as a leading U+FEFF, for the one reading that takes the file as written (a shell sourcing a .env file reads the
    mark's bytes as part of its first word). A file that is not text this tool can read — bytes that are not UTF-8, or a
    NUL character, as in UTF-16 without a mark or a binary key container — stops the run: its values could not be
    masked."""
    before = os.stat(path)   # follows supported links to a regular file
    if not stat.S_ISREG(before.st_mode):
        raise Fail("%s is not a regular file; its values cannot be masked" % path)
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    # A replacement between stat and open must neither block on a pipe nor supply different bytes.
    with open(path, "rb", opener=lambda name, _: os.open(name, flags)) as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or not os.path.samestat(before, opened):
            raise Fail("%s changed before it could be read; its values cannot be masked" % path)
        data = stream.read(LARGEST_SECRET_FILE + 1)
        if len(data) > LARGEST_SECRET_FILE or opened.st_size > LARGEST_SECRET_FILE:
            raise Fail("%s is larger than a secret file; its values cannot be masked" % path)
        after = os.stat(path)
        if (not os.path.samestat(opened, after) or len(data) != opened.st_size
                or (after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                != (opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)):
            raise Fail("%s could not be read completely and consistently; its values cannot be masked" % path)
    encoding = next((encoding for mark, encoding in BOMS if data.startswith(mark)), "utf-8")
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError:
        text = "\0"
    if "\0" in text:
        raise Fail("%s is not text this tool can read (binary, or an encoding without a byte order mark), so its "
                   "values cannot be masked — keep it outside the project for the migration" % path)
    return ("\ufeff" if encoding != "utf-8" else "") + text


def secret_files(project):
    """Every secret file in the project, outside dependency, build-output and cache folders — through a link to a
    plain file too. A folder that cannot be listed, or that is a link, stops the run: a secret file inside it would
    not be found, and its values would reach the evidence unmasked."""
    def unreadable(error):
        raise Fail("cannot list the folder %s to find secret files (%s)" % (error.filename, error.strerror or error))
    def recognized(name):
        return any(fnmatch.fnmatchcase(name.lower(), pattern) for pattern in SECRET_FILES)

    found = []
    for folder, dirs, names in os.walk(str(project), onerror=unreadable):
        kept = []
        for name in dirs:
            path = os.path.join(folder, name)
            if name in UNWATCHED_FOLDERS or name in (".git", STATE_DIR):
                continue
            if recognized(name):
                raise Fail("%s is a directory; its values cannot be masked" % path)
            if is_link(path):
                raise Fail("%s is a link to a folder — secret files inside it would not be found; run the check "
                           "with that folder in place, or add it to the plan as out of scope" % path)
            kept.append(name)
        dirs[:] = kept
        for name in names:
            if recognized(name):
                found.append(os.path.join(folder, name))
    return found
