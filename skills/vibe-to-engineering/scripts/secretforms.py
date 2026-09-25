"""The forms of a value, behind secretformats.py's readers: every way a check may print a value a secret file holds —
as written; decoded as each standard reader of its format reads it (python-dotenv, Node and a POSIX shell sourcing a
.env file, configparser filling in %(name)s, Java reading .properties as ISO-8859-1); as the number or the date and
time a reader makes of it (PyYAML, tomllib); escaped as JSON, Python and YAML write it; and each part of it a check may
print alone (its first word, a list's members, a URL's password and query values, percent-decoded) — and which texts
are names, never values: a setting's name followed by '=' or ':' with nothing after it (API_KEY=, an empty setting),
and a would-be name that is a token instead (token_like). Standard library only.
"""

import ast
import codecs
import datetime
import json
import os
import re
import string
from urllib.parse import unquote, unquote_plus

STEM = r"key|secret|token|passw(?:or)?d|pwd|credential|private|salt|pin"
# A name that says secret: evidence.py's one test of it, here so that the readers can use it too
SECRET_NAME = re.compile(r"(?i)key|secret|token|passw(?:or)?d|pwd|credential|private|salt|(?<![a-z])pin(?![a-z])")
LIST = "\x00list"   # after a name: the value is a member of the list of that name (evidence.py's member() reads it)
BARE = "\x00bare"   # after a file's name: the value is a line that gives no name a value (member() reads it too)
# Only a name: [export ]NAME= or 'NAME': with nothing after it — an empty setting, never a value
ONLY_NAME = re.compile(r"""[ \t]*(?:export[ \t]+)?(["']?)([A-Za-z0-9_][\w .-]*?)\1[ \t]*[=:][ \t]*""")
# The number a reader makes of a value: 017 and 1:30 (and 1:30.5) as YAML 1.1 reads them, 0x1F 0o17 0b101 1_000, 1e3
NUMBERS = ((r"0[0-7]+", lambda body: int(body, 8)),
           (r"[0-9]+(?::[0-5]?[0-9])+", lambda body: sexagesimal(body, int)),
           (r"[0-9]+(?::[0-5]?[0-9])+\.[0-9]*", lambda body: sexagesimal(body, float)),
           (r"0[xX][0-9a-fA-F]+|0[oO][0-7]+|0[bB][01]+|0|[1-9][0-9]*", lambda body: int(body, 0)),
           (r"(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", float))
# A date and time as PyYAML and tomllib read it into a Python value, and a TOML local time
TIMESTAMP = re.compile(r"([0-9]{4})-([0-9]{1,2})-([0-9]{1,2})(?:(?:[Tt]|[ \t]+)([0-9]{1,2}):([0-9]{2}):([0-9]{2})"
                       r"(?:\.([0-9]*))?(?:[ \t]*([Zz])|[ \t]*([-+])([0-9]{1,2})(?::([0-9]{2}))?)?)?")
CLOCK = re.compile(r"([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]+))?")
# The parts of a value: its members, a URL's user and password (the scheme starting a word), a URL's query values
MEMBERS = re.compile(r"[\s,;\[\]{}\"'`]+")
USER_INFO = re.compile(r"(?<![A-Za-z0-9+.-])[A-Za-z][A-Za-z0-9+.-]*://([^/?#\s]*)@")   # to the host's own '@'
QUERY = re.compile(r"[?&;#]([^=&;#\s]+)=([^&;#\s]*)")   # a query's parameters, and a fragment's (#access_token=…)
QUERY_AMP = re.compile(r"[?&#]([^=&#\s]+)=([^&#\s]*)")   # as Python 3.9.2 and later split a query: at '&' only
# .env as python-dotenv reads a quoted value, and the escapes it decodes; a C escape in a shell's $'…'
PY_QUOTED = {"'": (re.compile(r"'((?:\\'|[^'])*)'"), re.compile(r"\\[\\']")),
             '"': (re.compile(r'"((?:\\"|[^"])*)"'), re.compile(r"\\[\\'\"abfnrtv]"))}
NPM_QUOTED = {"'": re.compile(r"'((?:\\'|[^'])*)'"), '"': re.compile(r'"((?:\\"|[^"])*)"'),
              "`": re.compile(r"`((?:\\`|[^`])*)`")}
ANSI_C = re.compile(r"\\(?:([abeEfnrtv\\'\"?])|([0-7]{1,3})|x([0-9a-fA-F]{1,2})|u([0-9a-fA-F]{1,4})|U([0-9a-fA-F]{1,8})"
                    r"|c(.))")
ANSI_LETTERS = {"a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
INTERPOLATION = re.compile(r"%%|%\(([^)]*)\)s")


def camel(word):
    """True when one word of a name is written as people write camelCase: a first run of two lower-case letters or
    more, or capitals; each later capitalized word with two lower-case letters or more (one in the last, as in
    userId); an acronym of two capitals or more before a capitalized word (APIKey); digits only at the end (apiKey,
    DBPassword2, tokenV2). A base64 token's letters change case at random (cjMtZW52…) and fail it. Read run by run,
    so a long token costs no more than its length."""
    letters = word.rstrip("0123456789")
    runs = re.findall(r"[a-z]+|[A-Z]+", letters)
    if not letters or "".join(runs) != letters:
        return False
    for index, run in enumerate(runs):
        last = index == len(runs) - 1
        if run.islower() and len(run) < 2 and (not last or not index):
            return False
        if run.isupper() and not last and len(run) == 2:   # one capital before a capitalized word is no acronym
            return False
    return True


def name_like(name, strict=False):
    """True when `name` is written as people write a setting's name: words joined by _ . - (or spaces, as an INI key may
    have), each in one case or in camelCase, digits allowed (API_KEY, db.password, apiKey, 2FA_SECRET) — never a base64
    token, whose letters change case at random (cjMtZW52…), a text with no letter, or one holding + / = or quotes.
    Strict: every word in camelCase as camel() reads it, which no piece of a secret such as r3Horse or r3keyid4471 is —
    the test for a name found inside another value."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+(?: [A-Za-z0-9_.-]+)*", name) or not re.search(r"[A-Za-z]", name):
        return False
    words = [word for word in re.split(r"[ _.-]+", name) if word]
    return bool(words) and all(camel(word) or (not strict and (word.lower() == word or word.upper() == word))
                               for word in words)


def token_like(name, rest):
    """True when a line's would-be name, with `rest` the text after its '=' or ':', makes the line a bare token: the
    name is not written as a name (name_like); two '=' of padding or more follow its sign (cjMt…Nw==, JBSW…KE======
    — a name's value is never only '='); one '=' of padding follows a name that holds no secret word (deadbeef0123=);
    or the would-be name is one run of sixteen letters and digits or more with a digit between letters, as a base32 or
    hexadecimal token is written (MFRGGZDFKEYXG5LBNZ2GS3TH). API_KEY= stays an empty setting."""
    padding = re.fullmatch(r"(=+)(?:[ \t]*[#;].*|[ \t]*)", rest.strip())
    if not name_like(name) or (padding and (len(padding.group(1)) > 1 or not re.search(STEM, name, re.I))):
        return True
    return bool(re.fullmatch(r"[A-Za-z0-9]{16,}", name) and re.search(r"[A-Za-z][0-9]+[A-Za-z]", name))


def listed(name):
    """name marked as a list's name (LIST): the value read under it is one of its members."""
    return name if name.endswith(LIST) else name + LIST


def qualified(parent, key):
    """The name a value under `key` is masked under, inside a mapping, table or section named `parent`: the key — or,
    when the key says nothing secret and the name around it does ([pin] value = 4821, credentials: code: 4821), the
    two joined, so that it still says secret and a number there is never left readable as a setting."""
    if not parent or SECRET_NAME.search(key) or not SECRET_NAME.search(parent.replace(LIST, "")):
        return key
    return parent.replace(LIST, "") + "." + key


CLASSES = {"alnum": "A-Za-z0-9", "alpha": "A-Za-z", "blank": " \\t", "cntrl": "\\x00-\\x1f\\x7f", "digit": "0-9",
           "graph": "!-~", "lower": "a-z", "print": " -~", "punct": "".join("\\" + char for char in string.punctuation),
           "space": " \\t\\n\\r\\f\\v", "upper": "A-Z", "xdigit": "0-9A-Fa-f"}   # a shell pattern's [:class:]s


def shell_pattern(pattern):
    """A shell's pattern as a regular expression: * and ? for any text and any one character, [...] with ! or ^ for
    "not" and [:digit:] and the other classes inside, and a backslash before a character that stands for itself."""
    out, i = [], 0
    while i < len(pattern):
        char = pattern[i]
        if char == "\\" and i + 1 < len(pattern):
            out.append(re.escape(pattern[i + 1]))
            i += 2
            continue
        if char == "[":
            j = i + 1 + (pattern[i + 1:i + 2] in ("!", "^"))
            body, first = [], True
            while j < len(pattern) and (pattern[j] != "]" or first):
                named = re.match(r"\[:(\w+):\]", pattern[j:])
                if named and named.group(1) in CLASSES:
                    body.append(CLASSES[named.group(1)])
                    j += named.end()
                else:
                    body.append("\\" + pattern[j] if pattern[j] in "\\]^[" else pattern[j])
                    j += 1
                first = False
            if j < len(pattern):   # closed: a set of characters; never closed: a [ that stands for itself
                out.append("[" + "^" * (pattern[i + 1:i + 2] in ("!", "^")) + "".join(body) + "]")
                i = j + 1
                continue
        out.append("[\\s\\S]*" if char == "*" else "[\\s\\S]" if char == "?" else re.escape(char))
        i += 1
    return "".join(out)


def trimmed(value, operator, pattern):
    """value as a shell's ${NAME#pattern}, ${NAME##pattern}, ${NAME%pattern} or ${NAME%%pattern} makes it: the shortest
    (# %) or longest (## %%) prefix (#) or suffix (%) the pattern matches removed; value itself when none matches."""
    try:
        whole = re.compile(shell_pattern(pattern))
    except re.error:   # a pattern this reading does not know: the value as it is
        return value
    cuts = [at for at in range(len(value) + 1)
            if whole.fullmatch(value[:at] if operator[0] == "#" else value[at:])]
    if not cuts:
        return value
    if operator[0] == "#":
        return value[(cuts[-1] if operator == "##" else cuts[0]):]
    return value[:(cuts[0] if operator == "%%" else cuts[-1])]


def worth(value):
    """True for a text worth masking as a value — never an empty one, one made only of '=' and spaces (a base64 token's
    padding would mask every '='), or only a setting's name and its '=' or ':' with nothing after it (API_KEY=, an
    empty setting). A word that names a secret is masked when a file gives it as a value (REDIS_PASSWORD=secret, a list
    of field names): evidence.py finds every match in the text as the check printed it, so masking one never hides
    NAME=… from its net for named values."""
    body = value.strip()
    if not re.sub(r"[\s=]+", "", body):
        return False
    only = body[-1:] in ("=", ":") and ONLY_NAME.fullmatch(body)
    return not (only and name_like(only.group(2).strip()))


def sexagesimal(body, kind):
    """A YAML 1.1 base-60 number (1:30, 190:20:30.15) added up as PyYAML adds it, from its last part."""
    value, base = kind(0), 1
    for digit in reversed([kind(part) for part in body.split(":")]):
        value += digit * base
        base *= 60
    return value


def moment(text):
    """A date and time as PyYAML and tomllib make it a Python value, printed and as isoformat() writes it
    (2001-12-14t21:59:43.10-05:00 is 2001-12-14 21:59:43.100000-05:00; a fraction keeps six digits, cut, as both
    readers cut it), and a TOML local time (07:32:00.999999999 is 07:32:00.999999). Nothing for any other text."""
    clock, match = CLOCK.fullmatch(text), TIMESTAMP.fullmatch(text)
    try:
        if clock:
            hour, minute, second, fraction = clock.groups()
            value = datetime.time(int(hour), int(minute), int(second), int((fraction or "")[:6].ljust(6, "0")))
            return [str(value), value.isoformat()]
        if not match or not match.group(4):
            return []
        year, month, day, hour, minute, second, fraction, utc, sign, zone_hour, zone_minute = match.groups()
        shift = datetime.timedelta(hours=int(zone_hour or 0), minutes=int(zone_minute or 0))
        zone = datetime.timezone(-shift if sign == "-" else shift) if sign else datetime.timezone.utc if utc else None
        value = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second),
                                  int((fraction or "")[:6].ljust(6, "0")), tzinfo=zone)
    except ValueError:   # a date or time that does not exist
        return []
    return [str(value), value.isoformat()]


def forms(*texts):
    """Every form a value may be printed in: each text whole, each of its lines stripped when it has several, the text
    escaped as JSON, Python and a YAML single-quoted value write it (a check that prints its settings), and the number
    or the date and time a reader makes of it (NUMBERS, moment)."""
    found = []
    for text in (text for text in texts if text is not None):
        body = text.strip().replace("_", "").lstrip("+-") if len(text) <= 64 else ""   # no number is longer
        found += [text, json.dumps(text)[1:-1], json.dumps(text, ensure_ascii=False)[1:-1], repr(text)[1:-1],
                  text.replace("'", "''")] + [
            ("-" if text.strip().startswith("-") else "") + str(read(body)) for pattern, read in NUMBERS
            if re.fullmatch(pattern, body)][:1] + (moment(text.strip()) if len(text) <= 64 else []) + (
            [line.strip() for line in text.split("\n")] if "\n" in text else [])
    return list(dict.fromkeys(found))


def parts(value):
    """(name, part, how) for each part of a value a check may print alone: its first word; its text up to the first
    ',' ';' or '}'; each member between spaces, commas, semicolons, brackets and quotes (a list's member, a header's
    second word, the value without its quotes) — a letter or two alone is too common a word to mask — all with no
    name and how "part"; a URL's password (scheme://user:PASS@host), as written and percent-decoded, how "password";
    and each URL query value, as written and percent-decoded, under its parameter's name, how "=" (a pair found
    inside the value). evidence.py names each one (named)."""
    words = value.split()
    found = [(None, part, "part") for part in words[:1] + [re.split(r"[,;}]", value)[0].strip()]]
    found += [(None, member, "part") for member in MEMBERS.split(value)
              if member != value and (len(member) > 3 or (len(member) > 1 and not member.isalpha()))]
    for info in USER_INFO.findall(value) if "://" in value else ():
        user, colon, password = info.partition(":")   # a user shaped like a token is a token too (https://TOKEN@host,
        token = len(user) >= 8 and re.search(r"[0-9]", user)   # https://TOKEN:x-oauth-basic@host); postgres, git: no
        found += [(None, form, "password") for form in ((password, unquote(password)) if colon else ())
                  + ((user, unquote(user)) if token else ())]
    for name, part in QUERY.findall(value) + QUERY_AMP.findall(value) if "=" in value else ():   # names as read
        found += [(unquote_plus(name), form, "=") for form in (part, unquote(part), unquote_plus(part))]
    return found


def python_dotenv(text, at):
    """The value python-dotenv reads at text[at], after '=' and its spaces: '…' with only \\\\ and \\' decoded, "…" with
    only \\\\ \\' \\" \\a \\b \\f \\n \\r \\t \\v (octal-looking, \\x and \\u text left as written), else the rest of
    the line without a comment after a space, right-stripped. None for a quote python-dotenv cannot close."""
    char = text[at:at + 1]
    if char in PY_QUOTED:
        quoted, escape = PY_QUOTED[char]
        match = quoted.match(text, at)
        return match and escape.sub(lambda one: codecs.decode(one.group(), "unicode-escape"), match.group(1))
    end = text.find("\n", at)
    return re.sub(r"\s+#.*", "", text[at:len(text) if end < 0 else end]).rstrip()


def node_dotenv(text, at):
    """The values Node reads at text[at], after '=' and its spaces: util.parseEnv's (a quoted value up to the next
    same quote, a line break for each \\n in "…") and npm dotenv's (a quote closed as its LINE pattern closes it, a
    line break for \\n and a carriage return for \\r in "…"); an unquoted value up to '#', trimmed."""
    char = text[at:at + 1]
    if char not in NPM_QUOTED:
        end = text.find("\n", at)
        return [text[at:len(text) if end < 0 else end].split("#")[0].strip()]
    found, close = [], text.find(char, at + 1)
    if close > 0:
        found.append(text[at + 1:close].replace("\\n", "\n") if char == '"' else text[at + 1:close])
    match = NPM_QUOTED[char].match(text, at)
    if match:
        found.append(match.group(1).replace("\\n", "\n").replace("\\r", "\r") if char == '"' else match.group(1))
    return found


def ansi_c(raw):
    """A shell's $'…' text with its C escapes decoded, as bash decodes them."""
    def one(escape):
        letter, octal, hex2, hex4, hex8, control = escape.groups()
        if letter:
            return ANSI_LETTERS.get(letter, letter)
        if control:
            return chr(ord(control.upper()) ^ 0x40) if control != "?" else "\x7f"
        number = int(octal, 8) if octal else int(hex2 or hex4 or hex8, 16)
        return chr(number & 0xFF if octal or hex2 else min(number, 0x10FFFF))
    return ANSI_C.sub(one, raw)


def shell_word(text, at):
    """The word a POSIX shell (bash) reads at text[at] when it sources a .env file: quoted and unquoted parts joined,
    '…' as written, "…" with \\\\ \\" \\$ \\` escaped and a line break after a backslash dropped, $'…' with its C
    escapes, and outside quotes a backslash dropped before the character it keeps (a line break after it dropped too,
    so the value goes on on the next line). None when a quote is never closed, or at a $( … ) whose output only the
    shell knows; $NAME is left as written."""
    out, i = [], at
    while i < len(text) and text[i] not in " \t\n;&|<>()":
        if text.startswith("$((", i):   # arithmetic on whole numbers, worked out as the shell works it out
            close = text.find("))", i)
            number = arithmetic(text[i + 3:close]) if close > 0 else None
            if number is None:
                return None
            out.append(str(number))
            i = close + 2
            continue
        if text.startswith("$(", i):
            return None
        char = text[i]
        if char == "\\":
            out.append(text[i + 1:i + 2].replace("\n", ""))
            i += 2
        elif char == "'" or (char == "$" and text[i + 1:i + 2] == "'"):
            start = i + 1 + (char == "$")
            close = re.compile(r"(?:[^'\\]|\\.)*'" if char == "$" else r"[^']*'", re.S).match(text, start)
            if not close:
                return None
            raw = text[start:close.end() - 1]
            out.append(ansi_c(raw) if char == "$" else raw)
            i = close.end()
        elif char == '"':
            close = re.compile(r'(?:[^"\\]|\\.)*"', re.S).match(text, i + 1)
            if not close:
                return None
            out.append(re.sub(r'\\(\n|[\\"$`])', lambda one: one.group(1).replace("\n", ""),
                              text[i + 1:close.end() - 1]))
            i = close.end()
        elif char == "~" and (i == at or text[i - 1] == ":") and text[i + 1:i + 2] in ("", "/", ":", " ", "\t", "\n"):
            out.append(os.path.expanduser("~"))   # the home folder, at a word's start or after ':' in an assignment
            i += 1
        else:
            out.append(char)
            i += 1
    return "".join(out)


def arithmetic(expression):
    """A shell's $(( … )) over whole numbers with + - * / % and brackets, as the shell works it out, or None for
    anything else (a name, a comparison) — never evaluated as Python."""
    if not re.fullmatch(r"[0-9+\-*/%() \t]+", expression):
        return None
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError:
        return None
    operations = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
                  ast.Div: lambda a, b: int(a / b), ast.Mod: lambda a, b: a - b * int(a / b)}

    def number(node):
        if isinstance(node, ast.Expression):
            return number(node.body)
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return operations[type(node.op)](number(node.left), number(node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return -number(node.operand) if isinstance(node.op, ast.USub) else number(node.operand)
        if isinstance(node, ast.Constant if hasattr(ast, "Constant") else ast.Num) and type(getattr(
                node, "value", getattr(node, "n", None))) is int:
            return getattr(node, "value", getattr(node, "n", None))
        raise ValueError("not a whole-number sum")
    try:
        return number(tree)
    except (ValueError, ZeroDivisionError, RecursionError):
        return None


def interpolated(value, section, defaults, depth=0):
    """An INI value as configparser's BasicInterpolation reads it: each %(name)s filled in from the same section and
    [DEFAULT] (names lower-cased, as configparser keeps them), again inside what it filled in, ten deep at most; %%
    read as %. A reference to nothing is left as written (configparser stops there)."""
    def one(match):
        if match.group() == "%%":
            return "%"
        name = match.group(1).lower()
        found = section.get(name, defaults.get(name))
        if found is None or depth >= 10:
            return match.group()
        return interpolated(found, section, defaults, depth + 1)
    return INTERPOLATION.sub(one, value)


def latin1(text):
    """text as a reader that takes its UTF-8 bytes one byte a character reads it — Java's Properties.load(InputStream),
    which reads ISO-8859-1 (café is cafÃ©)."""
    return text.encode("utf-8", "surrogatepass").decode("latin-1")
