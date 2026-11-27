"""Owner-held aliases for path components. Only public names enter plan and map records."""
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import stat
import unicodedata

from trusted_tools import inside_project


def folded(text):
    return unicodedata.normalize("NFC", text).casefold()


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pieces = []
        self.attributes = []

    def handle_starttag(self, tag, attrs):
        self.attributes.extend(value for _, value in attrs if value)

    def handle_comment(self, data):
        self.attributes.append(data)

    def handle_data(self, data):
        self.pieces.append(data)


class NameMap:
    def __init__(self, pairs):
        if not isinstance(pairs, dict) or not pairs:
            raise ValueError("expected a nonempty JSON object of names and labels")
        self.public = {}
        self.original = {}
        for name, alias in pairs.items():
            if (not name or not name.isprintable() or "/" in name or "\\" in name
                    or folded(name) in (".", "..", ".git", ".vibe-to-engineering")
                    or not isinstance(alias, str) or not re.fullmatch(r"private-[a-z0-9]+(?:-[a-z0-9]+)*", alias)
                    or alias in self.original or folded(name) in self.public):
                raise ValueError("each confidential name needs a unique, neutral private- label")
            self.public[folded(name)] = alias
            self.original[alias] = name
        # A name denotes a complete path component. Preserve ordinary longer names
        # such as MyNotebook.py when the owner designates Notebook.py.
        alternatives = "|".join(re.escape(name) for name in self.public)
        self.terms = re.compile(r"(?<![\w.-])(?:" + alternatives + r")(?![\w.-])")
        for alias in self.original:
            if alias in self.public:
                raise ValueError("choose a neutral label distinct from confidential names")
            self.check_text(alias)

    def check_text(self, text):
        if self.terms.search(folded(text)):
            raise ValueError("a declared confidential name is still present")

    def check_html(self, document):
        visible = VisibleText()
        visible.feed(document)
        visible.close()
        for text in visible.pieces + visible.attributes:
            self.check_text(text)
        self.check_text("".join(visible.pieces))

    def check_values(self, value):
        if isinstance(value, str):
            self.check_text(value)
        elif isinstance(value, dict):
            for member in value.values():
                self.check_values(member)
        elif isinstance(value, list):
            for member in value:
                self.check_values(member)

    def display(self, name):
        key = folded(name)
        alias = self.public.get(key)
        if alias and unicodedata.normalize("NFC", self.original[alias]) != unicodedata.normalize("NFC", name):
            raise ValueError("name map spelling differs from inventory")
        if key in self.original:
            raise ValueError("an ordinary name already uses a confidential label")
        public = self.public.get(key, name)
        self.check_text(public)
        return public

    def disk_path(self, project, relative):
        parts = []
        for component in relative.split("/"):
            if component in self.original and os.path.lexists(project.joinpath(*parts, component)):
                raise ValueError("a confidential label collides with an existing name")
            parts.append(self.original.get(component, component))
        return "/".join(parts)


def unique_object(pairs):
    result = dict(pairs)
    if len(pairs) != len(result):
        raise ValueError("duplicate confidential name")
    return result


def load_name_map(filename, project):
    if filename is None:
        return None
    path = Path(filename)
    if not path.is_absolute():
        raise ValueError("the private name map needs an absolute location outside the project")
    resolved = path.resolve(strict=True)
    if inside_project(path, project) or inside_project(resolved, project):
        raise ValueError("keep the private name map outside the project")
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(resolved, flags), encoding="utf-8") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError("the private name map must be a regular file")
        return NameMap(json.load(source, object_pairs_hook=unique_object))
