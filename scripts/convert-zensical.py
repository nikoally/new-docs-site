#!/usr/bin/env python3
"""Convert a section of the Zensical (MkDocs) itac-docs site into Fumadocs MDX.

Usage:
    python3 scripts/convert-zensical.py <itac-docs repo> <nav section> [--out content/docs]

Example:
    python3 scripts/convert-zensical.py ../itac-docs Training

The nav tree in zensical.toml decides which pages are converted, their order,
and the folder titles (written to meta.json). Pages not in the nav are skipped.

Translations performed:
  * `# H1`                    -> frontmatter `title`
  * `hide: [toc]`             -> frontmatter `hideToc: true`
  * `!!! note|tip|warning`    -> <Callout type=...>
  * `!!! example`             -> <Example>
  * `??? type "title"`        -> <Accordions><Accordion>
  * `\\[ ... \\]`, `$$x$$`     -> fenced `$$` math blocks (KaTeX)
  * `align` environments      -> `aligned` (so KaTeX doesn't number equations)
  * currency `$` in prose     -> `\\$` (inline math follows arithmatex rules)
  * `{`, `}`, bare `<`        -> escaped for MDX
  * YouTube <iframe> embeds   -> <YouTube id=... />
  * `![alt](img){width=..}`   -> <FloatImage ... />  (images copied to public/)
  * links to `.md` pages      -> relative `.mdx` links, or the live site for
                                 pages outside the converted section
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tomllib
from pathlib import Path, PurePosixPath
from urllib.parse import quote

LIVE_SITE = "https://industrialassessment.com"

CALLOUT_TYPES = {
    "note": "info",
    "info": "info",
    "abstract": "info",
    "tip": "idea",
    "hint": "idea",
    "success": "success",
    "check": "success",
    "warning": "warning",
    "caution": "warning",
    "attention": "warning",
    "danger": "error",
    "error": "error",
    "failure": "error",
    "bug": "error",
}

ADMONITION_RE = re.compile(r'^(?P<indent>[ \t]*)(?P<kind>!!!|\?\?\?\+?)\s+(?P<type>[\w-]+)(?:\s+"(?P<title>[^"]*)")?\s*$')
# arithmatex "generic" inline-math rules: no space just inside the $, no digit after the closing $
INLINE_MATH_RE = re.compile(r"(?<![\\$])\$(?![\s$])(?:\\.|[^\\$\n])+?(?<!\s)\$(?![\d$])")
INLINE_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
PROTECT_RE = re.compile(f"{INLINE_CODE_RE.pattern}|{INLINE_MATH_RE.pattern}")
LINK_RE = re.compile(r"(\]\()([^)\s]+)(\))")
IFRAME_RE = re.compile(
    r'(?:<div[^>]*>\s*)?<iframe[^>]*?src="(?P<src>[^"]+)"[^>]*?>\s*</iframe>(?:\s*</div>)?',
    re.S,
)
IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)\)(?:\{(?P<attrs>[^}]*)\})?")


def slug(part: str) -> str:
    stem = re.sub(r"^\d+-", "", part)
    return re.sub(r"[\s_]+", "-", stem).lower()


def dest_rel(src_rel: PurePosixPath) -> PurePosixPath:
    parts = [slug(p) for p in src_rel.parent.parts]
    return PurePosixPath(*parts, slug(src_rel.stem) + ".mdx")


def jsx_attr(value: str) -> str:
    return '"' + value.replace("&", "&amp;").replace('"', "&quot;") + '"'


class Converter:
    def __init__(self, docs_dir: Path, out_dir: Path, public_dir: Path, page_map: dict[PurePosixPath, PurePosixPath]):
        self.docs_dir = docs_dir
        self.out_dir = out_dir
        self.public_dir = public_dir
        self.page_map = page_map  # source rel path -> dest rel path
        self.src_rel = PurePosixPath()
        self.warnings: list[str] = []

    # ---------- links / assets ----------
    def resolve(self, target: str) -> PurePosixPath:
        joined = os.path.normpath(os.path.join(str(self.src_rel.parent), target))
        return PurePosixPath(joined)

    def rewrite_link(self, url: str) -> str:
        if re.match(r"^[a-z]+:|^#|^/", url):
            return url
        path, _, anchor = url.partition("#")
        anchor = f"#{anchor}" if anchor else ""
        if not path.endswith(".md"):
            return url
        target = self.resolve(path)
        if target in self.page_map:
            here = self.page_map[self.src_rel].parent
            rel = os.path.relpath(str(self.page_map[target]), str(here))
            if not rel.startswith("."):
                rel = "./" + rel
            return rel + anchor
        # page outside this section: point at the live Zensical site
        web = str(target)[:-3]
        web = web[: -len("index")] if web.endswith("index") else web + "/"
        self.warnings.append(f"{self.src_rel}: external link -> {LIVE_SITE}/{web}")
        return f"{LIVE_SITE}/{quote(web)}{anchor}"

    def copy_asset(self, src: str) -> str:
        if re.match(r"^[a-z]+:", src):
            return src
        target = self.resolve(src)
        source_file = self.docs_dir / target
        if not source_file.exists():
            self.warnings.append(f"{self.src_rel}: missing image {src}")
            return src
        dest = self.public_dir / target
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, dest)
        return "/" + quote(str(target))

    # ---------- embeds ----------
    def convert_embeds(self, text: str) -> str:
        def iframe(m: re.Match) -> str:
            src = m.group("src")
            yt = re.search(r"youtube(?:-nocookie)?\.com/embed/([\w-]+)(?:\?(.*))?", src)
            if not yt:
                self.warnings.append(f"{self.src_rel}: non-YouTube iframe kept as <iframe>")
                return f'<iframe src={jsx_attr(src)} className="w-full aspect-video" />'
            attrs = [f"id={jsx_attr(yt.group(1))}"]
            start = re.search(r"(?:^|&)(?:start|t)=(\d+)", yt.group(2) or "")
            if start:
                attrs.append(f"start={{{start.group(1)}}}")
            title = re.search(r'title="([^"]*)"', m.group(0))
            if title and title.group(1) != "YouTube video player":
                attrs.append(f"title={jsx_attr(title.group(1))}")
            return f"<YouTube {' '.join(attrs)} />"

        def image(m: re.Match) -> str:
            src = self.copy_asset(m.group("src"))
            attrs = [f"src={jsx_attr(src)}", f"alt={jsx_attr(m.group('alt'))}"]
            raw = m.group("attrs") or ""
            width = re.search(r'width="?(\d+)', raw)
            align = re.search(r'align="?(left|right|center)', raw)
            if width:
                attrs.append(f"width={{{width.group(1)}}}")
            if align:
                attrs.append(f"align={jsx_attr(align.group(1))}")
            return f"<FloatImage {' '.join(attrs)} />"

        text = IFRAME_RE.sub(iframe, text)
        return IMAGE_RE.sub(image, text)

    # ---------- prose escaping ----------
    def escape_prose(self, line: str) -> str:
        if re.match(r"^\s*<(YouTube|FloatImage|iframe)\b", line):
            return line
        out, last = [], 0
        for m in PROTECT_RE.finditer(line):
            out.append(self.escape_plain(line[last : m.start()]))
            out.append(m.group(0))
            last = m.end()
        out.append(self.escape_plain(line[last:]))
        return "".join(out)

    def escape_plain(self, s: str) -> str:
        # protect link targets while escaping, then rewrite them
        links: list[str] = []

        def stash(m: re.Match) -> str:
            links.append(m.group(1) + self.rewrite_link(m.group(2)) + m.group(3))
            return f"\x00{len(links) - 1}\x00"

        s = LINK_RE.sub(stash, s)
        s = re.sub(r"(?<!\\)\$", r"\\$", s)
        s = re.sub(r"(?<!\\)([{}])", r"\\\1", s)
        s = re.sub(r"<(?![A-Za-z/!])", "&lt;", s)
        return re.sub(r"\x00(\d+)\x00", lambda m: links[int(m.group(1))], s)

    # ---------- line-level text (code, math, prose) ----------
    @staticmethod
    def fix_math(line: str) -> str:
        # KaTeX numbers rows of align/equation environments; MathJax (old site) did not.
        envs = {"align": "aligned", "gather": "gathered"}
        line = re.sub(r"\\(begin|end)\{(align|gather)\*?\}", lambda m: f"\\{m.group(1)}{{{envs[m.group(2)]}}}", line)
        return re.sub(r"\\(begin|end)\{equation\*?\}", "", line)

    def transform_text(self, lines: list[str]) -> list[str]:
        out: list[str] = []
        fence: str | None = None
        math: str | None = None  # "$$" or "\\["
        for line in lines:
            stripped = line.strip()
            indent = line[: len(line) - len(line.lstrip())]
            if fence:
                out.append(line)
                if stripped.startswith(fence):
                    fence = None
                continue
            fm = re.match(r"^(`{3,}|~{3,})", stripped)
            if fm and not math:
                fence = fm.group(1)
                out.append(line)
                continue
            if math:
                closer = "$$" if math == "$$" else "\\]"
                if stripped.endswith(closer):
                    body = stripped[: -len(closer)].rstrip()
                    if body:
                        out.append(indent + body)
                    out.append(indent + "$$")
                    math = None
                else:
                    out.append(line)
                continue
            for opener, closer in (("$$", "$$"), ("\\[", "\\]")):
                if stripped.startswith(opener):
                    rest = stripped[len(opener) :]
                    out.append(indent + "$$")
                    if rest.endswith(closer) and rest.strip() != "":
                        body = rest[: -len(closer)].strip()
                        if body:
                            out.append(indent + body)
                        out.append(indent + "$$")
                    else:
                        if rest.strip():
                            out.append(indent + rest.strip())
                        math = opener
                    break
            else:
                line = re.sub(r"\\\((.+?)\\\)", r"$\1$", line)
                out.append(self.escape_prose(line))
        if math:
            self.warnings.append(f"{self.src_rel}: unterminated math block")
        return [self.fix_math(l) for l in out]

    # ---------- admonitions ----------
    def convert_blocks(self, lines: list[str]) -> list[str]:
        out: list[str] = []
        buf: list[str] = []
        i = 0

        def flush():
            out.extend(self.transform_text(buf))
            buf.clear()

        while i < len(lines):
            m = ADMONITION_RE.match(lines[i])
            in_fence = False  # admonition markers are never inside code blocks in practice
            if not m or in_fence:
                buf.append(lines[i])
                i += 1
                continue
            flush()
            indent = m.group("indent")
            body_indent = indent + "    "
            i += 1
            body: list[str] = []
            while i < len(lines):
                line = lines[i]
                if line.strip() == "":
                    body.append("")
                elif line.startswith(body_indent) or line.startswith(indent + "\t"):
                    body.append(line[len(body_indent) :] if line.startswith(body_indent) else line[len(indent) + 1 :])
                else:
                    break
                i += 1
            while body and body[-1] == "":
                body.pop()
                i -= 1
            while body and body[0] == "":
                body.pop(0)
            inner = self.convert_blocks(body)
            kind, typ, title = m.group("kind"), m.group("type").lower(), m.group("title")
            if kind.startswith("???"):
                open_attr = ' defaultValue={["item"]}' if kind.endswith("+") else ""
                heading = title or typ.capitalize()
                out.append(f"{indent}<Accordions{open_attr}>")
                out.append(f'{indent}<Accordion title={jsx_attr(heading)} value="item">')
                close = [f"{indent}</Accordion>", f"{indent}</Accordions>"]
            elif typ == "example":
                attr = f" title={jsx_attr(title)}" if title else ""
                out.append(f"{indent}<Example{attr}>")
                close = [f"{indent}</Example>"]
            else:
                ctype = CALLOUT_TYPES.get(typ)
                if not ctype:
                    self.warnings.append(f"{self.src_rel}: unknown admonition type '{typ}', using info")
                    ctype = "info"
                attr = f" title={jsx_attr(title)}" if title else ""
                out.append(f'{indent}<Callout type="{ctype}"{attr}>')
                close = [f"{indent}</Callout>"]
            out.append("")
            out.extend(indent + l if l else "" for l in inner)
            out.append("")
            out.extend(close)
        flush()
        return out

    # ---------- page ----------
    def convert_page(self, src_rel: PurePosixPath) -> str:
        self.src_rel = src_rel
        text = (self.docs_dir / src_rel).read_text(encoding="utf-8").replace("\r\n", "\n")

        front: dict = {}
        fm = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        if fm:
            text = text[fm.end() :]
            if re.search(r"hide:\s*\n\s*-\s*toc", fm.group(1)):
                front["hideToc"] = True

        h1 = re.search(r"^# (.+)$", text, re.M)
        title = h1.group(1).strip() if h1 else slug(src_rel.stem).replace("-", " ").title()
        if h1:
            text = text[: h1.start()] + text[h1.end() :]

        text = self.convert_embeds(text)
        lines = self.convert_blocks(text.strip("\n").split("\n"))
        body = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"

        head = ["---", f"title: {json.dumps(title)}"]
        head += [f"{k}: {json.dumps(v)}" for k, v in front.items()]
        head.append("---")
        return "\n".join(head) + "\n\n" + body


def walk_nav(entries, title: str, metas: dict, pages: list):
    """Collect pages and build meta.json data for one nav group."""
    items: list[tuple[str, object]] = []  # ("page", path) | ("group", result)
    for entry in entries:
        pairs = [(None, entry)] if isinstance(entry, str) else list(entry.items())
        for sub_title, value in pairs:
            if isinstance(value, str):
                pages.append(PurePosixPath(value))
                items.append(("page", PurePosixPath(value)))
            else:
                items.append(("group", walk_nav(value, sub_title, metas, pages)))

    all_files = [v for k, v in items if k == "page"] + [f for k, g in items if k == "group" for f in g["files"]]
    group_dir = PurePosixPath(os.path.commonpath([str(f.parent) for f in all_files]))
    dest_dir = PurePosixPath(*[slug(p) for p in group_dir.parts])

    order = []
    for kind, value in items:
        target = dest_rel(value).with_suffix("") if kind == "page" else PurePosixPath(*[slug(p) for p in value["dir"].parts])
        order.append(str(target.relative_to(dest_dir)))
    # a folder's index.mdx is its landing page (clicking the folder opens it),
    # so it must not also be listed as a child
    order = [o for o in order if o != "index"]
    metas[group_dir] = {"title": title, "pages": order}
    return {"files": all_files, "dir": group_dir}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo", type=Path, help="path to the itac-docs (Zensical) repo")
    ap.add_argument("section", help="top-level nav section to convert, e.g. Training")
    ap.add_argument("--out", type=Path, default=Path("content/docs"))
    ap.add_argument("--public", type=Path, default=Path("public"))
    ap.add_argument("--no-root", action="store_true", help="don't mark the section as a sidebar root/tab")
    args = ap.parse_args()

    config = tomllib.loads((args.repo / "zensical.toml").read_text())
    nav = config["project"]["nav"]
    section = next((e[args.section] for e in nav if isinstance(e, dict) and args.section in e), None)
    if section is None:
        sys.exit(f"nav section '{args.section}' not found in zensical.toml")

    metas: dict[PurePosixPath, dict] = {}
    pages: list[PurePosixPath] = []
    root = walk_nav(section, args.section, metas, pages)
    if not args.no_root:
        metas[root["dir"]]["root"] = True

    docs_dir = args.repo / "docs"
    page_map = {p: dest_rel(p) for p in pages}
    conv = Converter(docs_dir, args.out, args.public, page_map)

    section_out = args.out / PurePosixPath(*[slug(p) for p in root["dir"].parts])
    if section_out.exists():
        shutil.rmtree(section_out)

    for src in pages:
        dest = args.out / page_map[src]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(conv.convert_page(src), encoding="utf-8")
        print(f"  {src}  ->  {dest}")

    for d, meta in metas.items():
        dest = args.out / PurePosixPath(*[slug(p) for p in d.parts]) / "meta.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    for w in conv.warnings:
        print(f"warning: {w}", file=sys.stderr)
    print(f"Converted {len(pages)} pages into {section_out}")


if __name__ == "__main__":
    main()
