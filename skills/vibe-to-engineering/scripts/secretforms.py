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
import re
import string
from urllib.parse import unquote, unquote_plus

STEM = r"key|secret|token|passw(?:or)?d|pwd|credential|private|salt|pin"
# A name that says secret, and a number or a yes/no word (a setting under a name that does not): evidence.py's one
# test of each, here so that the readers can use them too
SECRET_NAME = re.compile(r"(?i)key|secret|token|passw(?:or)?d|pwd|credential|private|salt|(?<![a-z])pin(?![a-z])")
SETTING = re.compile(r"(?i)[0-9][0-9._-]*|true|false|yes|no|on|off|null|none")
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
                    r"|c([\s\S]?))")   # \c before any character, a line break or nothing
ANSI_LETTERS = {"a": "\a", "b": "\b", "e": "\x1b", "E": "\x1b", "f": "\f", "n": "\n", "r": "\r", "t": "\t", "v": "\v"}
INTERPOLATION = re.compile(r"%%|%\(([^)]*)\)s")
# A shell's special parameters whose value only the running shell knows — its process id, the last background job's,
# its flags, its own name, the last word it ran — as $X, and as what a ${…} holds (${$}, ${#-}, ${0:-x})
UNKNOWN = re.compile(r"\$(?:[$!0-]|_(?!\w))")
UNKNOWN_BRACED = re.compile(r"#?(?:[$!-]|0(?![0-9])|_(?!\w))(?:$|[:#%=+?-])")
# What a ${…} may hold for secretformats.filled() to read it: ${#NAME}, ${NAME}, and ${NAME<op>word} for each of a
# shell's :- - := = :+ + :? ? # ## % %% — a name, a positional parameter, or one of # ? @ *
BRACED = re.compile(r"#(?:\w+|[#?@*])|(?:\w+|[#?@*])(?:(?::?[-=+?]|##?|%%?)[^}]*)?")
CONTINUED = re.compile(r"(?:[ \t]|\\\n)*")   # the space between a shell's words: blanks, and a line break after \
ASSIGNMENT = re.compile(r"[A-Za-z_]\w*\+?=")   # a word that gives a name a value
ARRAY = re.compile(r"[A-Za-z_]\w*\[[^\]\n]*\]\+?=")   # NAME[…]= : a value for an array's element
REDIRECTION = re.compile(r"(?:[0-9]*[<>]|&>)[<>&|-]*")   # >file, 2>file, >>file, >&2, &>file, <file, <<word
DECLARING = ("export", "readonly")   # the builtins whose NAME=value words this reader follows
# Commands that set variables in their own way, or read lines of their own — never followed: a line that runs one is
# refused (: is here because its NAME=value words stay after it, as a special builtin's do)
STATEFUL = frozenset(". : source eval exec read readarray mapfile let unset set shift getopts printf alias unalias "
                     "command builtin enable trap cd pushd popd declare typeset local if then else elif fi for while "
                     "until do done case esac select function { } [[ ]] ! time coproc".split())
LIMIT = 1 << 63   # a shell works out $(( … )) in signed 64-bit numbers
# The shell's own variables: set as it starts, worked out again at each reference (RANDOM, SECONDS, LINENO…), read-only
# (UID…) or read as arithmetic (OPTIND) — a file's assignment never decides what a reference to one gives. Measured on
# bash 3.2, this Mac's sh, with the ones later bash adds
SHELL_OWN = frozenset("_ BASHOPTS BASHPID BASH_ARGC BASH_ARGV BASH_ARGV0 BASH_COMMAND BASH_LINENO BASH_SOURCE "
                      "BASH_SUBSHELL BASH_VERSINFO DIRSTACK EPOCHREALTIME EPOCHSECONDS EUID FUNCNAME GROUPS HISTCMD "
                      "LINENO OPTIND PIPESTATUS PPID RANDOM SECONDS SHELLOPTS SRANDOM UID".split())
# Variables the shell sets itself as it starts, whatever the environment holds (measured on bash 3.2 as sh with
# env -i, 2026-09-27: PWD, SHLVL, HOSTNAME, HOSTTYPE, MACHTYPE, OSTYPE, IFS — OLDPWD likewise belongs to the
# shell's own state). They are never in the constructed environment and the file has not set them when this is
# asked, so what a reference gives is not derivable from the approved inputs (D4 rule 5): refused. A file that
# sets one first decides it until a cd, and this reader never follows a cd (STATEFUL).
STARTUP = frozenset("PWD SHLVL OLDPWD HOSTNAME HOSTTYPE MACHTYPE OSTYPE IFS".split())
READ_ONLY = "\0read-only"   # among the shell's variables: the names the file made read-only (never a name itself)
PARAMETER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|[0-9#?@*]")   # after $: a name (ASCII, as bash reads one), or a
# positional or special parameter
# ~ and the prefix after it, where a shell expands them: in a word (to /, ':', the word's end) and at the start of a
# ${…}'s word (to / or ':'); a quote, a backslash or a $ in the prefix leaves the ~ as written
TILDE = re.compile(r"~([^ \t\n/:;&|<>()'\"\\$`\0]*)(?=[ \t\n/:;&|<>()]|\Z)")
TILDE_WORD = re.compile(r"~([^/:$\0]*)(?=[/:]|\Z)")
# In a ${…} pattern: a range in [...], which bash 3.2 matches in the locale's collating order ([a-z] holds B in
# en_US.UTF-8), and an extended pattern (@(…) and the like), which later bash reads when its environment sets extglob
LOCALE_PATTERN = re.compile(r"\[[^\]]*-[^\]]*\]|[?*+@!]\(")
OUTSIDE = ("a value that depends on a variable the file does not set before this line, or that a command on an "
           "earlier line may have changed — the shell takes it from wherever the file is sourced")
# A part only the shell can read, inside a ${…}'s word the shell may never use: kept as ${ MARK code } and refused
# (LATER[code]) only where the shell reads it — what is in a part it skips it never runs (the owner's rule, round 8)
MARK = "\x01"
LATER = {"c": "a command's output, which only the shell knows", "a": "arithmetic this reader does not work out",
         "u": "a ${ … } this reader does not read", "p": "a special parameter only the running shell knows",
         "n": "an assignment inside another ${ … }, which a shell makes only when that part is used",
         "w": "a ~+, ~- or ~N, the working folders only the running shell knows",
         "h": "a ~name, the home folder the user database decides, not the file",
         "q": "a quote or a backslash inside ${ … }, which this reader does not read"}
# How bash 3.2 (this Mac's sh) reads a construct inside a word, from its own source (parse.y's parse_matched_pair): a
# ${ … } ends at its first } (FIRST), $'…' keeps an escaped character (ESCAPES), and inside "…" (DQUOTE) a $'…' is left
# as decoded
FIRST, ESCAPES, DQUOTE = 1, 2, 4
NEVER = "a ${ … } or a quote whose end this reader cannot find as the shell does"
# Before the text bash rewrote a $'…' into, inside a ${ … } in "…": still a quote there to this reader, and nothing
# where the rewritten text ends up outside the ${ … }. No secret file this tool reads can hold it (a lone surrogate)
REWRITTEN = "\udfff"
PLAIN = re.compile(r"[^ \t\n;&|<>()'\"`\\$\x01\x7f]*")   # characters bash reads on a word with, as they are written
CONTROL = re.compile("\\\\[\x01\x7f" + REWRITTEN + "]")   # after a backslash: a byte bash escapes its own way,
# or the text bash rewrote a $'…' into, whose first character that backslash escapes as it reads the word
ESCAPED_QUOTE = re.compile(r"\$'(?:[^'\\]|\\[^'])*\\'")   # a $'…' holding \', which bash reads on to a later '
KEPT = "a \\x01 or \\x7f byte after a backslash in $'…', or a \\x7f one in \"…\": bash keeps its escape byte there too"


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
    """A shell's $'…' text with its C escapes decoded, as bash decodes them. ValueError for an escape shells decode
    differently: \\u and \\U (bash 3.2, this Mac's sh, keeps them as written; later bash decodes them in the locale's
    encoding), \\c before anything but a letter, a byte that is 0 (the shell's value ends there) or 0x80 or more
    (\\xE9, \\351: written out as a raw byte, not as the character this reading would make of it), and KEPT."""
    if any(pair in ("\\\x01", "\\\x7f") for pair in re.findall(r"\\[\s\S]", raw)):
        raise ValueError(KEPT)
    def one(escape):
        letter, octal, hex2, hex4, hex8, control = escape.groups()
        if letter:
            return ANSI_LETTERS.get(letter, letter)
        if hex4 or hex8:
            raise ValueError("a \\u or \\U escape in $'…', which shells decode differently")
        if control is not None:
            if not re.fullmatch(r"[A-Za-z]", control):
                raise ValueError("a \\c escape before anything but a letter in $'…', which shells decode differently")
            return chr(ord(control.upper()) ^ 0x40)
        number = int(octal, 8) & 0xFF if octal else int(hex2, 16)
        if not 0 < number < 0x80:
            raise ValueError("a byte escape in $'…' that is 0 or outside ASCII, which the shell writes as a raw byte")
        return chr(number)
    return ANSI_C.sub(one, raw)


def shell_line(text, at, variables, environ=None):
    """What a POSIX shell (bash, run as sh) sourcing a .env file does on the line that starts at text[at], as far as
    this reader follows it exactly: ([(name, value)] for each assignment made there, [value] for each other word
    expanded, the offset where the shell's line ends) — `variables`, the shell's own variables so far, as the file set
    them (each value with NUL for a literal $, None for an array's, under READ_ONLY the names made read-only),
    updated as the shell updates its own, and `environ`, the check's constructed environment when known (encoded the
    same way), where a reference the file has not decided falls back: what it holds is used, what it does not hold is
    empty — nothing else can reach the child (final-review R1, D4 rule 5; without it the reader alone refuses such a
    reference, as before). No inherited function can stand in for a command any more: the constructed environment
    admits no BASH_FUNC_*, SHELLOPTS, BASH_ENV or ENV (D3), so a command the constructed PATH resolves cannot change
    a variable this shell holds. Followed: commands separated
    by ; or & (a background job changes nothing here), each NAME=value and NAME+=value words (and redirections),
    assigned in order, each seeing the ones before; export or readonly, after --, with NAME=value and NAME words, all
    expanded before any is assigned; or another command, whose NAME=value words last only for it. Each word is read
    by shell_word and worked out by evaluate. ValueError for anything
    else, never showing the file's
    text: a part only the shell can read (expansion), && || | ( ), an option but --, NAME=value before export or
    readonly, a reference in another command, a command that sets variables its own way (STATEFUL), a reference to a
    value that is genuinely indeterminate (value_of: a positional or special parameter, one of the shell's own
    variables, one it sets itself at startup, an array's), an assignment to a name
    it made read-only (assign), and a quote the shell never finds closed — it stops reading the file there, so each
    name set from there on keeps what the environment gives it."""
    assignments, words, i = [], [], at

    def done(end):   # what was assigned and expanded, each literal $ (NUL) put back
        return ([(name, value.replace("\0", "$")) for name, value in assignments],
                [value.replace("\0", "$") for value in words], end)
    while True:
        items, command, i = [], None, CONTINUED.match(text, i).end()
        while i < len(text) and (text[i] not in "\n#;&|()" or text.startswith("&>", i)):
            redirection = REDIRECTION.match(text, i)   # the word after it names a file
            if redirection and re.match(r"<<(?!<)", redirection.group()):
                raise ValueError("a here-document, whose lines this reader does not follow")
            head = None if redirection or (command is not None and command not in DECLARING) else (
                ARRAY.match(text, i) or ASSIGNMENT.match(text, i))
            raw, i = shell_word(text, CONTINUED.match(text, redirection.end()).end() if redirection else
                                head.end() if head else i)
            if raw is None:   # the shell reads nothing more, and each name set from here on keeps the environment's
                raise ValueError("a quote the shell never finds closed, where it stops reading the file")
            if head:
                kind = "array" if ARRAY.match(head.group()) else "append" if head.group().endswith("+=") else "assign"
                items.append((kind, re.match(r"\w+", head.group()).group(), raw))
            elif command is None and not redirection:
                command = raw.replace("\0", "$")
                items.append(("command", None, raw))
            else:
                items.append(("word", None, raw))
            i = CONTINUED.match(text, i).end()
        if text.startswith(("&&", "||"), i) or text[i:i + 1] in ("|", "(", ")"):
            raise ValueError("&&, ||, | or ( ), which this reader does not follow")
        scratch = dict(variables)
        if command in DECLARING and items[0][0] != "command":
            raise ValueError("NAME=value before %s, which this reader does not follow" % command)
        if command is not None and command not in DECLARING:   # another command: its NAME=value words last for it
            if command in STATEFUL:
                raise ValueError("a command that sets variables in its own way (%s), which this reader does not "
                                 "follow" % command)
            if any("$" in raw for _, _, raw in items):
                raise ValueError("a reference in a command's words, which this reader does not follow")
            temporary = dict(scratch)
            for kind, name, raw in items:
                value = evaluate(raw, temporary, environ)
                if kind in ("assign", "append", "array"):
                    assign(temporary, kind, name, value, environ=environ)
                    assignments += [(name, value)] + ([(name, temporary[name])] if kind == "append" and temporary[
                        name] is not None else [])
                else:
                    words.append(value)
        else:   # assignments: in order, each seeing the ones before; after export or readonly, all expanded first
            options, made, names = command in DECLARING, [], []
            for kind, name, raw in items[1:] if command else items:
                value = evaluate(raw, scratch, environ)
                if kind == "word" and options and value == "--":
                    options = False
                elif kind == "word" and options and value.startswith("-"):
                    raise ValueError("an option to %s, which this reader does not follow" % command)
                elif kind == "word":
                    options = False
                    words += [value] if not command else []   # a name export or readonly is given: not a value
                    names += [value] if command else []
                else:
                    options = False
                    made.append((kind, name, value))
                    if not command:
                        assign(scratch, kind, name, value, environ=environ)
            for kind, name, value in made if command else ():
                assign(scratch, kind, name, value, command == "readonly", environ=environ)
            if command == "readonly":   # readonly NAME: its value, the file's or none, can no longer change
                scratch[READ_ONLY] = scratch.get(READ_ONLY, frozenset()) | frozenset(names)
            assignments += [(name, value) for _, name, value in made] + [
                (name, scratch[name]) for kind, name, _ in made if kind == "append" and scratch[name] is not None]
        if text[i:i + 1] != "&":   # a background job's assignments never reach this shell
            variables.clear()
            variables.update(scratch)
        if text[i:i + 1] not in (";", "&"):
            return done(i)
        i += 1


def assign(variables, kind, name, value, readonly=False, environ=None):
    """A shell's NAME=value (kind "assign"), NAME+=value ("append") or NAME[…]=value ("array", which this reader does
    not follow: None) in `variables` — and, for readonly, the name made read-only. NAME+=value on a name the file has
    not set adds to the constructed environment's value of it (known exactly, empty when absent) — only the reader
    exercised alone (no environ) cannot say what the shell adds to, and refuses. ValueError for what the shell does
    not assign as written: a name the file made read-only (the shell refuses, and keeps the value it had)."""
    if name in variables.get(READ_ONLY, ()):
        raise ValueError("an assignment to a variable the file made read-only, which the shell refuses")
    if kind == "append" and name not in variables:
        if environ is None:
            raise ValueError("NAME+=value on a variable the file does not set before this line — without the "
                             "constructed environment this reader cannot say what the shell adds to")
        variables[name] = environ.get(name, "")
    if kind == "array" or (kind == "append" and variables[name] is None):
        variables[name] = None
    else:
        variables[name] = variables[name] + value if kind == "append" else value
    if readonly:
        variables[READ_ONLY] = variables.get(READ_ONLY, frozenset()) | {name}


def evaluate(word, variables, environ=None):
    """The value a shell makes of a word shell_word read, as the shell makes it: from the left, each $NAME and ${…} in
    turn, and a ${…}'s word only when the shell uses it — ${NAME:-word} and := when NAME is empty; :+ when it is not;
    + always; - = ? never, NAME being set; a trimming pattern (# ## % %%) when there is a value to trim — so a
    reference, or a part only the shell can read (a mark, later), in a part the shell skips is never read, and
    ${NAME:=word} assigns as the shell assigns. A literal $ is NUL, here and in every value the variables hold, so no
    value is read again for references. `environ`, the check's constructed environment when known, is where a
    reference the file has not decided resolves (value_of). ValueError for a mark the shell reads (its reason), when
    a reading stays indeterminate even so
    (value_of: an array's value too), for ${NAME:=word} on a name the file made read-only,
    for ${NAME:?word} on an empty value (the shell stops there and prints the word, which no value here holds), and
    for a reading that depends on the locale the shell runs in: ${#NAME} of a value outside ASCII (characters or
    bytes), and trimming a value, or with a pattern, outside ASCII, or with a range in [...] or an extended pattern
    (LOCALE_PATTERN)."""
    out, i = [], 0
    while i < len(word):
        if word.startswith("${", i):
            end, depth = i + 2, 1
            while depth:   # the } that closes it: a ${ … } inside it is kept whole by expansion()
                depth += 1 if word.startswith("${", end) else -1 if word[end] == "}" else 0
                end += 2 if word.startswith("${", end) else 1
            out.append(braced(word[i + 2:end - 1], variables, environ))
            i = end
        elif word[i] == "$" and PARAMETER.match(word, i + 1):
            name = PARAMETER.match(word, i + 1).group()
            out.append(value_of(name, variables, environ))
            i += 1 + len(name)
        else:
            out.append(word[i])
            i += 1
    return "".join(out)


def braced(inside, variables, environ=None):
    """What a shell makes of ${inside} (evaluate)."""
    if inside[:1] == MARK:   # a part only the shell can read, where the shell reads it
        raise ValueError(LATER[inside[1:]])
    length = re.fullmatch(r"#(\w+|[#?@*])", inside)
    if length:
        value = value_of(length.group(1), variables, environ)
        if not value.isascii():
            raise ValueError("the length of a value outside ASCII, which depends on the locale the shell runs in")
        return str(len(value))
    head = re.match(r"(\w+|[#?@*])(:?[-=+?]|##?|%%?)?", inside)
    if not head:   # ${${B}} and the like: a name this reader cannot read
        raise ValueError(LATER["u"])
    name, operator, word = head.group(1), head.group(2) or "", inside[head.end():]
    if word and not operator:   # ${A${B}}, ${A$(cmd)}, ${A"x"}: to the shell a bad substitution, which assigns nothing
        raise ValueError(LATER["u"])
    value = value_of(name, variables, environ)
    if operator[:1] in ("#", "%"):
        if not value:   # nothing to trim: the shell does not read the pattern
            return value
        pattern = evaluate(word, variables, environ)
        if not (value + pattern).isascii() or LOCALE_PATTERN.search(pattern):
            raise ValueError("a trimming pattern whose match depends on the locale the shell runs in")
        return trimmed(value, operator, pattern)
    if "+" in operator:
        return evaluate(word, variables, environ) if operator == "+" or value else ""
    if operator[:1] == ":" and not value:   # :- := :? on an empty value; - = ? never apply: the name is set
        if operator == ":?":
            raise ValueError("a ${NAME:?word} on an empty value, where the shell stops and prints the word")
        word = evaluate(word, variables, environ)
        if operator == ":=":
            assign(variables, "assign", name, word, environ=environ)
        return word
    return value


def value_of(name, variables, environ=None):
    """The shell's value of $name. A name the file set is the file's. One it has not: under the constructed
    environment (`environ`, the whole known mapping — final-review R1, D4 rule 5) the reading is computed, never
    guessed — the environment's value when it holds the name, empty when it does not, for nothing else can reach
    the child. ValueError only for what stays indeterminate even so: a positional or special parameter ($1, $#,
    $?, $@, $*), which the running shell alone knows; one of the shell's own variables (SHELL_OWN), worked out
    again at each reference whatever the file or the environment says; one the shell sets itself as it starts
    (STARTUP); an array's value. Without `environ` — the reader exercised alone — a name the file has not set
    stays refused (OUTSIDE): nothing then says what the shell inherits. Never shows the name: a would-be name may
    be text of a secret (pa$sw0rd)."""
    if re.fullmatch(r"[0-9]+|[#?@*]", name):
        raise ValueError("a value that depends on $1, $#, $?, $@ or $*, which the shell takes from wherever the file "
                         "is sourced")
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):   # ${2FA}, ${Aé}: the shell stops there
        raise ValueError("a ${ … } this reader does not read")
    if name in SHELL_OWN:   # worked out again at each reference: a file's assignment to one (RANDOM=1 sets the
        raise ValueError("a value that depends on %s, a variable the shell works out itself" % name)   # seed, never
    if name in variables:                                                                   # the value) decides
        if variables[name] is None:                                                         # nothing here
            raise ValueError("a reference to a variable this reader cannot follow (an array's)")
        return variables[name]
    if name in STARTUP:   # the file has not set it: the shell sets it itself as it starts — never the environment
        raise ValueError("a value that depends on %s, which the shell sets itself as it starts" % name)
    if environ is not None:
        return environ.get(name, "")
    raise ValueError(OUTSIDE)


def home(prefix, nested=False):
    """What a shell makes of ~prefix: ~ alone is the home folder — ${HOME}, which evaluate() reads like any other
    reference: the file's HOME when it sets one, else the constructed environment's (known exactly). ValueError for
    ~name, which the user database decides, never the file (as
    written when it holds no such user), and for ~+, ~- and ~N, the working folders only the running shell knows —
    starting a ${…}'s word (nested), a mark evaluate() refuses only where the shell uses that word (later)."""
    if not prefix:
        return "${HOME}"
    code = "w" if re.fullmatch(r"[+-][0-9]*|[0-9]+", prefix) else "h"
    if nested:
        return later(code)
    raise ValueError(LATER[code])


def shell_word(text, at):
    """(the word a POSIX shell (bash) reads at text[at] when it sources a .env file, the offset after it): quoted and
    unquoted parts joined, '…' as written, "…" — ending where bash ends it (parsed, quoted_end) — as double_quoted()
    reads it, $'…' with its C escapes (ansi_c), and
    outside quotes a backslash dropped before the character it keeps (a line break after it dropped too, so the value
    goes on on the next line), each $ and ` read by expansion(), and a ~ at the word's start or after ':' read by
    home(). A $ that stands for itself — in '…' or $'…', after a backslash, or with no name after it — is NUL in the
    word, so that no reference is read into it (shell_line puts it back). The word is None when a quote is never
    closed: the shell reads nothing then. ValueError, naming it, for a part only the shell can read (expansion,
    ansi_c, home) and for bash's $"…", which the shell translates with a message catalogue the locale it runs in
    picks."""
    out, i = [], at
    while i < len(text) and text[i] not in " \t\n;&|<>()":
        char = text[i]
        if char == "\\":
            out.append(text[i + 1:i + 2].replace("\n", "").replace("$", "\0"))
            i += 2
        elif char == "'" or (char == "$" and text[i + 1:i + 2] == "'"):
            start = i + 1 + (char == "$")
            close = re.compile(r"(?:[^'\\]|\\.)*'" if char == "$" else r"[^']*'", re.S).match(text, start)
            if not close:
                return None, i
            raw = text[start:close.end() - 1]
            out.append((ansi_c(raw) if char == "$" else raw).replace("$", "\0"))
            i = close.end()
        elif char == "$" and text[i + 1:i + 2] == '"':
            raise ValueError('a $"…", which the shell translates in the locale it runs in')
        elif char == '"':
            end, kept = parsed(text, i + 1, '"', '"', '"')
            if end is None:
                return None, i
            if quoted_end(kept, 0, '"') != len(kept):   # bash expands it up to another " than it read it to
                raise ValueError(NEVER)
            out.append(double_quoted(kept[:-1]))   # what bash expands: the text it kept as it read the word
            i = end
        elif char in "$`":
            piece, i = expansion(text, i)
            out.append(piece)
        elif char == "~" and (i == at or text[i - 1] == ":") and TILDE.match(text, i):   # a word's start, after ':'
            out.append(home(TILDE.match(text, i).group(1)))
            i = TILDE.match(text, i).end()
        else:
            out.append(char)
            i += 1
    return "".join(out), i


def double_quoted(raw):
    """What is inside a "…", as a shell reads it: \\\\ \\" \\$ \\` escaped, a line break after a backslash dropped,
    and each $ and ` read by expansion(), as inside "…". ValueError for KEPT."""
    out, i = [], 0
    while i < len(raw):
        if raw[i] == "\\" and raw[i + 1:i + 2] in ("\\", '"', "$", "`", "\n"):
            out.append(raw[i + 1].replace("\n", "").replace("$", "\0"))
            i += 2
        elif raw.startswith("\\\x7f", i):
            raise ValueError(KEPT)
        elif raw[i] in "$`":
            piece, i = expansion(raw, i, quoted=True)
            out.append(piece)
        else:
            out.append(raw[i].replace(REWRITTEN, ""))
            i += 1
    return "".join(out)


def later(code):
    """A part only the shell can read, kept for evaluate(), which refuses it (LATER[code]) where the shell reads it."""
    return "${" + MARK + code + "}"


def expansion(text, i, nested=False, quoted=False):
    """(what a shell makes of the $ or ` at text[i], outside '…', and the offset after it): arithmetic — $(( … )) and
    bash's $[ … ] — worked out; a ${…} whose shape evaluate() reads (BRACED) kept as written, with what it holds read
    the same way and a ~ starting its word read by home(); and $NAME, a positional parameter, $#, $?, $@, $* and a
    lone $ kept as written, for evaluate(). ValueError, naming it, for a reading only the shell can make: a command's
    output ($( … ), ` … `), arithmetic this reading does not work out, any other ${…} (${NAME:1:2}, ${!NAME}),
    ${NAME:=word} or ${NAME=word} inside another ${…} (an assignment the shell makes only when that part is used), and
    a special parameter only the running shell knows ($$, $!, $-, $0, $_) — but inside a ${…} (nested), where the
    shell may never use the part, each is kept as a mark (later) that evaluate() refuses only where it does. A ${…}
    ends where bash ends it (braced_end; `quoted`: inside "…"), or ValueError. Inside one, from a quote, a backslash, a
    command's output or arithmetic not worked out on, the rest of its word is one mark (its offset None to the ${…}
    that reads it): never read where the shell skips it, refused where the shell reads it."""
    if text[i] == "`" or (text.startswith("$(", i) and not text.startswith("$((", i)):
        if not nested:
            raise ValueError(LATER["c"])
        return later("c"), None
    if text.startswith(("$((", "$["), i):
        opener = 3 if text[i + 1] == "(" else 2
        end = arithmetic_end(text, i + opener, opener == 3)
        number = None if end is None else arithmetic(text[i + opener:end])
        if number is None:
            if not nested:
                raise ValueError(LATER["a"])
            return later("a"), None
        return str(number), end + opener - 1
    if text.startswith("${", i):
        try:
            end = braced_end(text, i, quoted, nested)
        except ValueError:
            if not nested:
                raise
            return later("u"), None
        kept, shape, j = [], [], i + 2
        while j < end - 1:
            piece, j = (later("q"), None) if text[j] in "\"'\\" + REWRITTEN or text.startswith(("$'", '$"'), j) else \
                expansion(text, j, True, quoted) if text[j] in "$`" else (text[j], j + 1)
            kept.append(piece)
            shape.append("x" if piece.startswith("${") else piece)   # one inside it is read already
            j = end - 1 if j is None else j   # the rest of the word goes with that mark
        if j != end - 1:
            raise ValueError(NEVER)
        shape = "".join(shape)
        if UNKNOWN_BRACED.match(shape) or not BRACED.fullmatch(shape):
            if not nested:
                raise ValueError(LATER["u"])
            return later("u"), end
        if nested and re.match(r"(?:\w+|[#?@*]):?=", shape):
            return later("n"), end
        inside = "".join(kept)
        word = re.match(r"(?:\w+|[#?@*])(?::?[-=+?]|##?|%%?)", inside)   # the name and operator before its word
        tilde = word and TILDE_WORD.match(inside, word.end())
        if tilde:   # ${NAME:-~/x}: the shell expands a ~ that starts the word — when it uses the word
            inside = inside[:word.end()] + home(tilde.group(1), True) + inside[tilde.end():]
        return "${" + inside + "}", end
    if UNKNOWN.match(text, i):
        if not nested:
            raise ValueError("a special parameter only the running shell knows ($%s)" % text[i + 1])
        return later("p"), UNKNOWN.match(text, i).end()
    return "$" if re.match(r"[\w#?@*]", text[i + 1:i + 2]) else "\0", i + 1   # a lone $ stands for itself


def parsed(text, i, qc, opener, close, flags=0):
    """(the offset just past the close of the construct whose opener stands just before text[i], the text bash keeps of
    it) as bash 3.2 reads a word — a port of its parse.y's parse_matched_pair; (None, …) when the text ends first. `qc`:
    the quote the construct is in ('' for none); `opener`, `close`: its brackets or its quote. A backslash keeps the
    next character — a line break after it dropped, but in '…' — and in '…' nothing else counts but its close, or with
    ESCAPES ($'…') a backslash; a ${ inside a ${ … }, and an opener inside $( … ) and $[ … ], opens another, never with
    FIRST. Inside brackets '…', "…" and `…` are read whole — a $'…' kept as quotes around nothing, or as ansi_c decodes
    it after REWRITTEN inside "…" (DQUOTE), and $"…" as "…"; inside "…", `…`, $( … ), ${ … } and $[ … ] are.
    ValueError where ansi_c refuses a $'…' it must decode."""
    out, count, dollar = [], 1, False
    rflags = DQUOTE if qc == '"' else flags & DQUOTE
    while count:
        if i >= len(text):
            return None, "".join(out)
        char, i = text[i], i + 1
        if char == close:
            count -= 1
        elif opener != close and dollar and opener == "{" and char == "{":
            count += 1
        elif not flags & FIRST and char == opener:
            count += 1
        out.append(char)
        if char == "\\" and (opener != "'" or flags & ESCAPES):   # the next character is kept as it is
            if i >= len(text):
                return None, "".join(out)
            if text[i] == "\n" and qc != "'":
                out.pop()
            else:
                out.append(text[i])
            i, dollar = i + 1, False
            continue
        if opener == "'":
            continue
        if opener != close and char in "'\"`" or opener == '"' and (char == "`" or dollar and char in "({["):
            closer = {"(": ")", "{": "}", "[": "]"}.get(char, char)
            end, inner = parsed(text, i, char if opener != close else "", char, closer, (
                (ESCAPES if dollar and char == "'" else 0) | rflags if opener != close else rflags & ~DQUOTE
                if char == "(" else FIRST | rflags if char == "{" else rflags))
            if end is None:
                return None, "".join(out) + inner
            if opener != close and dollar and char in "'\"":   # bash rewrites $'…' and $"…" as it reads them
                inner = '"' + inner if char == '"' else REWRITTEN + ansi_c(inner[:-1]) if rflags & DQUOTE else "''"
                del out[-2:]
            out.append(inner)
            i = end
        dollar = char == "$"
    return i, "".join(out)


def braced_end(text, i, quoted=False, nested=False):
    """The offset just past the } that ends the ${ at text[i] where bash 3.2 ends it as it expands the word
    (expanded_end). A ${ … } that starts a part of a word is read first (parsed): its expansion must end where the
    reading does, or further on only over plain characters of the same word. Inside "…" (`quoted`: the text bash kept
    of it) and inside another ${ … } (`nested`) bash reads it with what is around it: its expansion alone ends it — but
    over a $'…' holding \\', which bash reads on to a later ' as it reads the word, it is read first as if it started
    a part. ValueError when it never ends, where it ends otherwise, and for a \\x01 or \\x7f byte, or a $'…' bash
    rewrote, after a backslash — which bash escapes its own way as it reads the word, so that its expansion may read
    on past the } that ends it here."""
    if quoted or nested:
        end = expanded_end(text, i + 2, "}")
        if quoted or not ESCAPED_QUOTE.search(text, i, len(text) if end is None else end):
            if end is None or CONTROL.search(text, i, end):
                raise ValueError(NEVER)
            return end
    end, kept = parsed(text, i + 2, "", "{", "}", FIRST)
    if end is None:
        raise ValueError(NEVER)
    plain = PLAIN.match(text, end).group()   # the word bash reads on after it
    stop = expanded_end(kept + plain, 0, "}")
    if stop is None or stop < len(kept) or CONTROL.search(kept):
        raise ValueError(NEVER)
    return end + stop - len(kept)


def expanded_end(s, i, close):
    """The offset just past the } or ) (`close`) that ends the ${ … } or $( … ) whose inside starts at s[i], as bash 3.2
    finds it when it expands a word (subst.c's extract_dollar_brace_string, extract_delimited_string): a backslash keeps
    the next character; a ${ inside a ${ … }, and a ( inside a $( … ), opens another; '…' and "…" (quoted_end), `…` (a
    backslash in it keeping the next character) and a $( … ) inside ${ … } are passed whole; in a $( … ), a # starting a
    word makes the rest of its line a comment. None when nothing ends it."""
    depth, comment = 1, False
    while i is not None and i < len(s):
        char = s[i]
        if comment:
            comment, i = char != "\n", i + 1
        elif close == ")" and char == "#" and (not i or s[i - 1] in " \t\n"):
            comment, i = True, i + 1
        elif char == "\\":
            i += 2
        elif close == "}" and s.startswith("${", i):
            depth, i = depth + 1, i + 2
        elif char == close:
            depth -= 1
            if not depth:
                return i + 1
            i += 1
        elif close == ")" and char == "(" or close == "}" and s.startswith("$(", i):
            i = expanded_end(s, i + 1 + (char == "$"), ")")
        elif char == "`":
            i += 1
            while i < len(s) and s[i] != "`":
                i += 2 if s[i] == "\\" else 1
            i = i + 1 if i < len(s) else None
        elif char in "'\"":
            i = quoted_end(s, i + 1, char)
        else:
            i += 1
    return None


def quoted_end(s, i, quote):
    """The offset just past the quote that closes the '…' or "…" whose inside starts at s[i], as bash 3.2 passes it when
    it expands a word (subst.c's skip_single_quoted, skip_double_quoted): '…' at the next '; in "…" a backslash keeps
    the next character, `…` is passed whole, and so are $( … ) and ${ … } (expanded_end). The text's end when nothing
    closes it; None when a $( … ) or ${ … } inside never ends."""
    if quote == "'":
        return len(s) if s.find("'", i) < 0 else s.find("'", i) + 1
    backquote = False
    while i is not None and i < len(s):
        char = s[i]
        if char == "\\":
            i += 2
        elif backquote or char == "`":
            backquote, i = backquote != (char == "`"), i + 1
        elif s.startswith(("$(", "${"), i):
            i = expanded_end(s, i + 2, ")" if s[i + 1] == "(" else "}")
        elif char == '"':
            return i + 1
        else:
            i += 1
    return None if i is None else len(s)


def arithmetic_end(text, at, double):
    """Where the arithmetic that starts at text[at] ends: at the first ')' of its closing '))' (double) or at its ']';
    None when it is never closed."""
    if not double:
        end = text.find("]", at)
        return end if end >= 0 else None
    depth = 0
    for j in range(at, len(text)):
        if text[j] == "(":
            depth += 1
        elif text[j] == ")":
            if not depth:
                return j if text.startswith("))", j) else None
            depth -= 1
    return None


def arithmetic(expression):
    """A shell's $(( … )) over whole numbers — written in decimal, octal (017) or hexadecimal (0x1F) — with + - * / %
    and brackets, as the shell works it out, or None for anything else (a name, a comparison, 08) and for a number or
    a result outside the shell's signed 64-bit numbers, which it wraps around without a word — never evaluated as
    Python."""
    try:
        expression = re.sub(r"0[xX][0-9a-fA-F]+|[0-9]+", lambda one: str(int(one.group(), 16 if one.group()[1:2] in (
            "x", "X") else 8 if one.group()[:1] == "0" else 10)), expression)
    except ValueError:   # 08 and 09 are no octal numbers: the shell refuses them too
        return None
    if not re.fullmatch(r"[0-9+\-*/%() \t]+", expression):
        return None
    try:
        tree = ast.parse(expression.strip(), mode="eval")
    except SyntaxError:
        return None

    def quotient(a, b):   # whole numbers, cut toward zero as the shell cuts them
        return abs(a) // abs(b) * (1 if (a < 0) == (b < 0) else -1)
    operations = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b,
                  ast.Div: quotient, ast.Mod: lambda a, b: a - b * quotient(a, b)}

    def number(node):
        if isinstance(node, ast.Expression):
            return number(node.body)
        if isinstance(node, ast.BinOp) and type(node.op) in operations:
            return fits(operations[type(node.op)](number(node.left), number(node.right)))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            return fits(-number(node.operand) if isinstance(node.op, ast.USub) else number(node.operand))
        if isinstance(node, ast.Constant if hasattr(ast, "Constant") else ast.Num) and type(getattr(
                node, "value", getattr(node, "n", None))) is int:
            return fits(getattr(node, "value", getattr(node, "n", None)))
        raise ValueError("not a whole-number sum")

    def fits(value):   # the shell would wrap it around: refused
        if not -LIMIT <= value < LIMIT:
            raise ValueError("outside the shell's 64-bit numbers")
        return value
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
