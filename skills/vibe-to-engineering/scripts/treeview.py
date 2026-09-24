"""The tree view: every file of a checkpoint or of the project, ignored files and nested repositories marked
where they sit (RA-01).
"""

from gitrun import show

def plural(count, one, many):
    return "%d %s" % (count, one if count == 1 else many)


MARKS = {"ignored": "[ignored]", "nested": "[nested repository]", "state": "[the skill's own folder]"}


def print_tree(title, saved, depth, full=False, ignored=(), nested=(), state_dir=None):
    """The saved files as a tree, folders opened `depth` levels deep. With full=True, also every file git ignores and
    every nested repository, each marked where it sits — a folder holding nothing but ignored files as one line —
    and the skill's own folder (`state_dir`, its name in bytes, when it exists), then the count of each kind.
    ignored or nested None: the checkpoint did not record them."""
    root = {}
    repos = sorted(set(nested or ()) | {rel for rel in ignored or () if rel.endswith(b"/")})
    leaves = [(rel, "saved") for rel in saved]
    if full:
        leaves += [(rel, "ignored") for rel in ignored or () if not rel.endswith(b"/")]
        leaves += [(rel, "nested") for rel in repos] + ([(state_dir + b"/", "state")] if state_dir else [])
    for rel, kind in leaves:
        node, parts = root, show(rel).rstrip("/").split("/")
        for part in parts[:-1]:
            node = node.setdefault(part + "/", {})
        node[parts[-1] + ("/" if rel.endswith(b"/") else "")] = kind

    def count(node):
        found = {"saved": 0, "ignored": 0, "nested": 0, "state": 0}
        for child in node.values():
            for kind, number in (count(child).items() if isinstance(child, dict) else [(child, 1)]):
                found[kind] += number
        return found

    lines, folded = [], []

    def walk(node, prefix, level):
        names = sorted(node, key=lambda name: (not name.endswith("/"), name.lower()))
        for position, name in enumerate(names):
            last = position == len(names) - 1
            child = node[name]
            line = prefix + ("└── " if last else "├── ") + name
            if not isinstance(child, dict):
                lines.append((line, MARKS.get(child)))
                continue
            found = count(child)
            if found["ignored"] and not (found["saved"] or found["nested"]):
                folded.append(name)
                lines.append((line, "[ignored — %s]" % plural(found["ignored"], "file", "files")))
            elif level >= depth:
                counts = [plural(found["saved"], "file", "files")] + (
                    ["%d ignored" % found["ignored"]] if found["ignored"] else []) + (
                    [plural(found["nested"], "nested repository", "nested repositories")] if found["nested"] else [])
                lines.append(("%s (%s)" % (line, " · ".join(counts)), None))
            else:
                lines.append((line, None))
                walk(child, prefix + ("    " if last else "│   "), level + 1)

    walk(root, "", 1)
    print(title)
    column = min(max([len(line) for line, mark in lines if mark] or [0]), 40) + 2
    for line, mark in lines:
        print((line + "  ").ljust(column) + mark if mark else line)
    if not full:
        print("\n%d files" % len(saved))
    elif ignored is None or nested is None:
        print("\n%s saved — this checkpoint did not record which files git ignored or which nested repositories there "
              "were" % plural(len(saved), "file", "files"))
    else:
        others = [rel for rel in ignored if not rel.endswith(b"/")]
        print("\n%s saved · %d ignored%s · %s\n[ignored], [nested repository]: never touched, not in checkpoints" % (
            plural(len(saved), "file", "files"), len(others),
            " (%s)" % plural(len(folded), "folder", "folders") if folded else "",
            plural(len(repos), "nested repository", "nested repositories")))
