"""Publish and recover the public map pair without a second browser print."""
from contextlib import ExitStack, suppress
import hashlib
import os
import re
import uuid
import zipfile

from gitrun import Fail

MAP_HTML = "Migration-Map.html"
MAP_PDF = "Migration-Map.pdf"
PENDING_PAIR = "Migration-Map.pending.zip"
PAIR_MARKER = b"vibe-to-engineering: map publication v1"
PDF_STAMP = re.compile(rb"\n<!-- v2e-printed-pdf: ([0-9a-f]{64}) -->\n\Z")


def read_digest(source, copy=None):
    digest = hashlib.sha256()
    for chunk in iter(lambda: source.read(128 * 1024), b""):
        digest.update(chunk)
        if copy is not None:
            copy.write(chunk)
    return digest.hexdigest().encode("ascii")


def check_pending(source, filenames):
    """The journal contains exactly two plain, uncompressed document entries."""
    try:
        with zipfile.ZipFile(source) as existing:
            if (existing.comment == PAIR_MARKER and existing.namelist() == filenames and
                    all(item.compress_type == zipfile.ZIP_STORED for item in existing.infolist())):
                return
    except zipfile.BadZipFile:
        pass
    raise Fail("the pending map filename is occupied by an unrecognized file")


def recover_pair(state, directory, open_state, pdf_name, html_name):
    """Only finish the PDF identified by the already-published regular HTML file."""
    with ExitStack() as files:
        try:
            source = files.enter_context(open_state(PENDING_PAIR))
            html = files.enter_context(open_state(html_name))
        except FileNotFoundError:
            return  # No journal, or the first HTML has never been published.
        check_pending(source, [pdf_name, html_name])
        try:
            with zipfile.ZipFile(source) as pair:
                public_digest = read_digest(html)
                html.seek(max(0, html.tell() - 120))
                stamp = PDF_STAMP.search(html.read())
                with pair.open(html_name) as archived:
                    if read_digest(archived) != public_digest:
                        if stamp:
                            with suppress(FileNotFoundError):
                                with open_state(pdf_name) as previous:
                                    if read_digest(previous) == stamp[1]:
                                        return  # The original public pair is still complete.
                            raise Fail("pending HTML differs from the incomplete public pair")
                        return  # A legacy pair still occupies the public names.
                if not stamp:
                    raise Fail("pending map has no matching published PDF digest")
                with pair.open(pdf_name) as archived:
                    restore_pdf(archived, stamp[1], state, directory, pdf_name)
        except zipfile.BadZipFile as error:
            raise Fail("pending map data failed its integrity check") from error
        os.unlink(state / PENDING_PAIR if directory is None else PENDING_PAIR, dir_fd=directory)


def restore_pdf(archived, digest, state, directory, pdf_name):
    # Only this fixed filename is restored. Archive content cannot choose paths,
    # replace the public HTML, or determine the digest used to authorize the PDF.
    name = ".v2e-map-recovery-%s.tmp" % uuid.uuid4().hex
    temporary = state / name if directory is None else name
    target = state / pdf_name if directory is None else pdf_name
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=directory)
    try:
        with os.fdopen(fd, "wb") as copy:
            if read_digest(archived, copy) != digest:
                raise Fail("pending PDF differs from the published HTML digest")
        os.replace(temporary, target, src_dir_fd=directory, dst_dir_fd=directory)
    finally:
        with suppress(FileNotFoundError):
            os.unlink(temporary, dir_fd=directory)


def publish_pair(draft_pdf, draft_html, state, directory):
    with draft_pdf.open("rb") as pdf, draft_html.open("ab") as html:
        html.write(b"\n<!-- v2e-printed-pdf: " + read_digest(pdf) + b" -->\n")
    draft_pair = draft_pdf.with_name(PENDING_PAIR)
    with zipfile.ZipFile(draft_pair, "x") as pair:
        pair.comment = PAIR_MARKER
        pair.write(draft_pdf, draft_pdf.name)
        pair.write(draft_html, draft_html.name)
    for source in (draft_pair, draft_html, draft_pdf):
        target = state / source.name if directory is None else source.name
        os.replace(source, target, dst_dir_fd=directory)
    os.unlink(state / PENDING_PAIR if directory is None else PENDING_PAIR, dir_fd=directory)
