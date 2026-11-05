#!/usr/bin/env python3
"""Build landtalks.org into _site/. Standard library only.

    python3 build.py           build
    python3 build.py --serve   build, then preview at http://localhost:8000/

Talks are _talks/<evening>/<name>.md, slides are slides/<evening>/<name>.pdf,
and evenings are in _data/evenings.yml. See README.md.

The templates are written in Liquid, the same language Jekyll uses. This
understands only the parts of it they use, and stops on anything else.
"""

import functools
import html
import http.server
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
NOT_PUBLISHED = {"README.md", "build.py", "tmp", "__pycache__"}
TALK_FIELDS = ("title", "speaker", "emoji", "hook")


def fail(message):
    sys.exit(f"Build failed: {message}")


# ---------- content files ----------

def value(text):
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        return text[1:-1].replace('\\"', '"') if text[0] == '"' else text[1:-1]
    return int(text) if text.isdigit() else text


def front_matter(path):
    """(fields, body), or (None, text) for a file with no front matter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None, text
    head, separator, body = text[4:].partition("\n---\n")
    if not separator:
        fail(f"{path}: the --- section is never closed")
    fields = {}
    for line in head.splitlines():
        if line.strip() and not line.startswith("#"):
            key, colon, rest = line.partition(":")
            if not colon:
                fail(f"{path}: can't read this line: {line}")
            fields[key.strip()] = value(rest)
    return fields, body.lstrip("\n")


def evenings():
    found = []
    for line in (ROOT / "_data/evenings.yml").read_text(encoding="utf-8").splitlines():
        match = re.match(r"(- )?\s*(\w+):\s*(.+)", line)
        if match:
            if match.group(1):
                found.append({})
            found[-1][match.group(2)] = value(match.group(3))
    return found


def markdown(text):
    """Paragraphs and [links](https://...), which is all talk copy needs."""
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", text.strip()):
        if paragraph.strip():
            escaped = html.escape(" ".join(paragraph.split()), quote=False)
            paragraphs.append("<p>" + re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', escaped) + "</p>\n")
    return "".join(paragraphs)


def talks(known):
    found = []
    for path in sorted((ROOT / "_talks").glob("*/*.md")):
        fields, body = front_matter(path)
        name = path.relative_to(ROOT)
        if fields is None:
            fail(f"{name}: it needs a --- section at the top, see README.md")
        missing = [field for field in TALK_FIELDS if field not in fields]
        if missing:
            fail(f"{name}: missing {', '.join(missing)}")
        folder = path.parent.name
        if str(fields.get("evening")) != folder:
            fail(f"{name}: it says evening {fields.get('evening')} but is in folder {folder}")
        if fields["evening"] not in known:
            fail(f"{name}: add evening {folder} to _data/evenings.yml")
        found.append({**fields, "slug": path.stem, "url": f"/talks/{folder}/{path.stem}/", "content": markdown(body)})
    return found


# ---------- Liquid, the parts these templates use ----------

TOKEN = re.compile(r"(\{\{.*?\}\}|\{%.*?%\})", re.S)
ARGUMENT = re.compile(r'"[^"]*"|[\w.]+')


def lookup(expression, context):
    expression = expression.strip()
    if expression.startswith('"'):
        return expression[1:-1]
    if expression.isdigit():
        return int(expression)
    current = context
    for part in expression.split("."):
        current = current.get(part) if isinstance(current, dict) else None
    return current


def evaluate(expression, context):
    first, *filters = re.findall(r'(?:[^|"]|"[^"]*")+', expression)
    result = lookup(first, context)
    for item in filters:
        name, _, rest = item.strip().partition(":")
        arguments = [lookup(argument, context) for argument in ARGUMENT.findall(rest)]
        name = name.strip()
        if name == "where":
            result = [entry for entry in result or [] if str(entry.get(arguments[0])) == str(arguments[1])]
        elif name == "first":
            result = result[0] if result else None
        elif name == "append":
            result = f"{result}{arguments[0]}"
        elif name == "size":
            result = len(result)
        elif name == "escape":
            result = "" if result is None else html.escape(str(result))
        elif name == "strip_html":
            result = re.sub(r"<[^>]+>", "", str(result))
        elif name == "strip":
            result = str(result).strip()
        elif name == "default":
            result = result or arguments[0]
        else:
            fail(f"unknown template filter: {name}")
    return result


def condition(text, context):
    for option in text.split(" or "):
        left, equals, right = option.partition("==")
        if (lookup(left, context) == lookup(right, context)) if equals else lookup(left, context):
            return True
    return False


def parse(tokens, position=0, until=None):
    nodes = []
    while position < len(tokens):
        token = tokens[position]
        if token.startswith("{%"):
            tag = token[2:-2].strip()
            word = tag.split()[0]
            if word == until:
                return nodes, position
            if word in ("if", "for"):
                children, position = parse(tokens, position + 1, "end" + word)
                nodes.append((word, tag[len(word) + 1:], children))
            elif word in ("assign", "include"):
                nodes.append((word, tag[len(word) + 1:], None))
            else:
                fail(f"unknown template tag: {tag}")
        elif token.startswith("{{"):
            nodes.append(("output", token[2:-2], None))
        else:
            nodes.append(("text", token, None))
        position += 1
    if until:
        fail(f"a template is missing {{% {until} %}}")
    return nodes, position


def run(nodes, context):
    result = []
    for kind, text, children in nodes:
        if kind == "text":
            result.append(text)
        elif kind == "output":
            output = evaluate(text, context)
            result.append("" if output is None else str(output))
        elif kind == "if":
            if condition(text, context):
                result.append(run(children, context))
        elif kind == "for":
            name, _, items = text.partition(" in ")
            for item in evaluate(items, context) or []:
                result.append(run(children, {**context, name.strip(): item}))
        elif kind == "assign":
            name, _, expression = text.partition("=")
            context[name.strip()] = evaluate(expression, context)
        elif kind == "include":
            filename, name, source = re.match(r"(\S+)\s+(\w+)=(\S+)", text).groups()
            included = (ROOT / "_includes" / filename).read_text(encoding="utf-8")
            result.append(render(included, {**context, "include": {name: lookup(source, context)}}))
    return "".join(result)


def render(template, context):
    return run(parse(TOKEN.split(template))[0], context)


def with_layout(name, content, context):
    fields, template = front_matter(ROOT / "_layouts" / f"{name}.html")
    result = render(template, {**context, "content": content})
    return with_layout(fields["layout"], result, context) if fields and fields.get("layout") else result


# ---------- the build ----------

def published(path):
    parts = path.relative_to(ROOT).parts
    return path.is_file() and parts[0] not in NOT_PUBLISHED and not any(part.startswith(("_", ".")) for part in parts)


def write(url, text):
    target = OUT / url.strip("/") / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


def build():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    pages, static = [], []
    for path in sorted(ROOT.rglob("*")):
        if published(path):
            is_page = path.suffix == ".html" and front_matter(path)[0] is not None
            (pages if is_page else static).append(path)
    for path in static:
        target = OUT / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)

    data = {"evenings": evenings()}
    all_talks = talks({evening["number"] for evening in data["evenings"]})
    site = {
        "url": "https://landtalks.org",
        "talks": all_talks,
        "data": data,
        "static_files": [{"path": "/" + path.relative_to(ROOT).as_posix()} for path in static],
    }
    for talk in all_talks:
        write(talk["url"], with_layout("talk", talk["content"], {"site": site, "page": talk}))
    for path in pages:
        fields, template = front_matter(path)
        folder = path.relative_to(ROOT).parent.as_posix()
        url = "/" if folder == "." else f"/{folder}/"
        context = {"site": site, "page": {**fields, "url": url}}
        write(url, with_layout(fields["layout"], render(template, context), context))

    paths = {entry["path"] for entry in site["static_files"]}
    waiting = [talk["slug"] for talk in all_talks if f"/slides/{talk['evening']}/{talk['slug']}.pdf" not in paths]
    print(f"Built {len(all_talks)} talks into _site/")
    if waiting:
        print("No PDF yet for: " + ", ".join(waiting))


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(OUT))
        print("Preview at http://localhost:8000/ (Ctrl-C to stop). Run this again after editing.")
        try:
            http.server.ThreadingHTTPServer(("127.0.0.1", 8000), handler).serve_forever()
        except KeyboardInterrupt:
            pass
