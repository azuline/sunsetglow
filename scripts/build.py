#!/usr/bin/env python3

from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
import tempfile
import dataclasses

from datetime import datetime
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, SubElement, ElementTree

import jinja2  # type: ignore
import pytz  # type: ignore

PROJECT_DIR = os.environ["PROJECT_ROOT"]

je = jinja2.Environment(loader=jinja2.FileSystemLoader(f"{PROJECT_DIR}/src"))


# DATA


@dataclasses.dataclass
class Fascicle:
    index: int
    title: str


@dataclasses.dataclass
class PostMeta:
    slug: str
    title: str
    fascicle: Fascicle | None
    timestamp: datetime

    @classmethod
    def parse(cls, slug: str, d: dict[str, Any]) -> PostMeta:
        return cls(
            slug=slug,
            title=d["title"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            fascicle=Fascicle(**f) if (f := d.get("fascicle", None)) else None,
        )

    @functools.cached_property
    def lastupdated(self) -> datetime:
        p = f"src/posts/tex/{self.slug}.tex"
        r = subprocess.run(["git", "log", "-1", "--format=%cI", p], check=True, capture_output=True, text=True)
        if text := r.stdout.strip():
            return datetime.fromisoformat(text).astimezone(pytz.utc)
        return self.timestamp


@dataclasses.dataclass
class PostIndex:
    longform: dict[str, PostMeta]
    shortform: dict[str, PostMeta]


# UTILS


def site_updated_at() -> datetime:
    r = subprocess.run(["git", "log", "-1", "--format=%cI"], check=True, capture_output=True, text=True)
    text = r.stdout.strip()
    return datetime.fromisoformat(text).astimezone(pytz.utc)


# BUILD STEPS


def empty_dist() -> None:
    # Removing and recreating the directory messes with the `make watch+serve` workflow. So we
    # instead empty the directory each time if it already exists.
    p = Path("dist")
    if not p.is_dir():
        if p.is_file():
            p.unlink()
        p.mkdir()
    for f in p.iterdir():
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f)
        else:
            raise Exception(f"{f} is not a file or directory.")


def compile_favicons():
    for f in Path("src/favicons").iterdir():
        shutil.copyfile(f, Path("dist", f.name))


def compile_index(posts: PostIndex, commit: str):
    with Path("src/index.html.jinja").open("r") as fp:
        tpl = je.from_string(fp.read())
    with Path("dist/index.html").open("w") as fp:
        fp.write(tpl.render(posts=posts, commit=commit))


def compile_posts(posts: PostIndex, commit: str):
    with Path("src/posts/post.html.jinja").open("r") as fp:
        tpl = je.from_string(fp.read())
    for path, entries in [("posts", posts.longform), ("scribbles", posts.shortform)]:
        Path("dist", path).mkdir()
        for slug, meta in entries.items():
            f = Path(f"src/posts/tex/{slug}.tex")

            # Compile the post from LaTeX to HTML.
            with tempfile.NamedTemporaryFile(suffix=".html") as tmp:
                # --standalone: puts TOC into the .html, but we have to trim the rest.
                subprocess.run(["pandoc", "--standalone", "--table-of-contents", "--number-sections", str(f), "-o", tmp.name], check=True)
                tmp.seek(0)
                post = tmp.read().decode()

            # Trim the unnecessary parts of the pandoc output, leaving only the TOC and the post.
            trim_start = post.find("</header>") + len("</header>")
            trim_end = post.find("</body")
            post = post[trim_start:trim_end]
            # Wrap the main article inside a div.
            nav_end = post.find("</nav>") + len("</nav>")
            post = post[:nav_end] + '<div id="POST">' + post[nav_end:] + "</div>"
            # Add dots after ToC and header section numbers.
            post = re.sub(r'(-section-number">[^<]*)', r"\1.", post)
            # Add clickable links to headings.
            post = re.sub(
                r'(<h[1-6])(.*?)id="([^"]+)"([^>]*)>(.+?)</h',
                r'\1\2id="\3"\4><a href="#\3" class="heading">\5</a></h',
                post,
                flags=re.MULTILINE | re.DOTALL,
            )

            # Compile and write the compiled post.
            with Path("dist", path, f.parts[-1]).with_suffix(".html").open("w") as fp:
                fp.write(tpl.render(slug=slug, meta=meta, body=post, commit=commit))


def compile_feed(posts: PostIndex):
    table = [
        ("posts", "longform", posts.longform),
        ("scribbles", "shortform", posts.shortform),
    ]
    for path, title, entries in table:
        feed = Element("feed", xmlns="http://www.w3.org/2005/Atom")
        SubElement(feed, "title").text = f"sunsetglow :: {title}"
        SubElement(feed, "link", href="https://sunsetglow.net/atom.xml", rel="self", type="application/atom+xml")
        SubElement(feed, "link", href="https://sunsetglow.net/", rel="alternate", type="text/html")
        SubElement(feed, "updated").text = site_updated_at().isoformat()
        SubElement(feed, "id").text = "tag:sunsetglow.net,2024:site"

        for slug, meta in entries.items():
            post = SubElement(feed, "entry")
            SubElement(post, "id").text = f"tag:sunsetglow.net,{meta.timestamp.strftime('%Y-%m-%d')}:{slug}"
            SubElement(post, "link", href=f"https://sunsetglow.net/{path}/{slug}.html", type="text/html")
            SubElement(post, "title").text = meta.title
            SubElement(post, "published").text = meta.timestamp.isoformat()
            SubElement(post, "updated").text = meta.lastupdated.isoformat()

            author = SubElement(post, "author")
            SubElement(author, "name").text = "acid angel from asia"
            SubElement(author, "email").text = "contact@sunsetglow.net"

        tree = ElementTree(feed)
        with open(f"dist/{path}/atom.xml", "wb") as fh:
            tree.write(fh, encoding="utf-8", xml_declaration=True)


def main():
    os.chdir(PROJECT_DIR)

    with Path("src/posts/index.json").open("r") as fp:
        index = json.load(fp)
        posts = PostIndex(
            longform={k: PostMeta.parse(k, v) for k, v in index["longform"].items()},
            shortform={k: PostMeta.parse(k, v) for k, v in index["shortform"].items()},
        )

    r = subprocess.run(["git", "rev-parse", "--short", "HEAD"], check=True, capture_output=True, text=True)
    commit = r.stdout.strip()

    empty_dist()
    shutil.copytree("src/assets", "dist/assets")
    compile_favicons()
    compile_index(posts, commit)
    compile_posts(posts, commit)
    compile_feed(posts)


if __name__ == "__main__":
    main()
