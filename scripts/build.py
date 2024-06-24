#!/usr/bin/env python3

from __future__ import annotations

import functools
import json
import os
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
class PostMeta:
    slug: str
    title: str
    timestamp: datetime
    public: bool

    @classmethod
    def parse(cls, slug: str, d: dict[str, Any]) -> PostMeta:
        return cls(
            slug=slug,
            title=d["title"],
            timestamp=datetime.fromisoformat(d["timestamp"]),
            public=d["public"],
        )

    @functools.cached_property
    def lastupdated(self) -> datetime | None:
        p = f"src/posts/tex/{self.slug}.tex"
        r = subprocess.run(
            ["git", "log", "-1", "--format=%cI", p],
            check=True,
            capture_output=True,
            text=True,
        )
        text = r.stdout.strip()
        if not text:
            return None
        lastupdated = datetime.fromisoformat(text).astimezone(pytz.utc)
        if lastupdated.date() == self.timestamp.date():
            return None
        return lastupdated


PostIndex = dict[str, PostMeta]


# UTILS


def site_updated_at() -> datetime:
    r = subprocess.run(
        ["git", "log", "-1", "--format=%cI"],
        check=True,
        capture_output=True,
        text=True,
    )
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


def compile_index(posts: PostIndex, commit: str):
    with Path("src/index.jinja").open("r") as fp:
        tpl = je.from_string(fp.read())

    # Write the main index.html
    publicposts = {k: v for k, v in reversed(posts.items()) if v.public}
    index = tpl.render(posts=publicposts, commit=commit)
    with Path("dist/index.html").open("w") as fp:
        fp.write(index)

    # Write a staging index.html
    stagingposts = dict(reversed(posts.items()))
    staging = tpl.render(posts=stagingposts, commit=commit)
    with Path("dist/staging.html").open("w") as fp:
        fp.write(staging)


def compile_posts(posts: PostIndex, commit: str):
    Path("dist/posts").mkdir()
    with Path("src/posts/template.jinja").open("r") as fp:
        tpl = je.from_string(fp.read())
    for f in Path("src/posts/tex").iterdir():
        if not f.suffix == ".tex":
            continue

        # Compile the post from LaTeX to HTML.
        with tempfile.NamedTemporaryFile(suffix=".html") as tmp:
            subprocess.run(
                [
                    "pandoc",
                    "--standalone",  # Puts TOC into the .html, but we have to trim the rest.
                    "--table-of-contents",
                    "--number-sections",
                    str(f),
                    "-o",
                    tmp.name,
                ],
                check=True,
            )
            tmp.seek(0)
            post = tmp.read().decode()

        # Trim the unnecessary parts of the pandoc output, leaving only the TOC and the post.
        trim_start = post.find("</header>") + len("</header>")
        trim_end = post.find("</body")
        post = post[trim_start:trim_end]
        # Wrap the main article inside a div.
        nav_end = post.find("</nav>") + len("</nav>")
        post = post[:nav_end] + '<div id="POST">' + post[nav_end:] + "</div>"

        # Wrap the post with a Jinja template.
        slug = f.stem
        meta = posts[slug]
        post = tpl.render(slug=slug, meta=meta, body=post, commit=commit)

        # Write the compiled post.
        with Path("dist/posts", f.parts[-1]).with_suffix(".html").open("w") as fp:
            fp.write(post)


def compile_feed(posts: PostIndex):
    # fmt: off
    feed = Element("feed", xmlns="http://www.w3.org/2005/Atom")
    SubElement(feed, "title").text = "sunsetglow"
    SubElement(feed, "link", href="https://sunsetglow.net/atom.xml", rel="self", type="application/atom+xml")
    SubElement(feed, "link", href="https://sunsetglow.net/", rel="alternate", type="text/html")
    SubElement(feed, "updated").text = site_updated_at().isoformat()
    SubElement(feed, "id").text = "tag:sunsetglow.net,2024:site"

    for slug, meta in posts.items():
        post = SubElement(feed, "entry")
        SubElement(post, "id").text = f"tag:sunsetglow.net,{meta.timestamp.strftime('%Y-%m-%d')}:{slug}"
        SubElement(post, "link", href=f"https://sunsetglow.net/posts/{slug}.html", type="text/html")
        SubElement(post, "title").text = meta.title
        SubElement(post, "published").text = meta.timestamp.isoformat()
        SubElement(post, "updated").text = (meta.lastupdated or meta.timestamp).isoformat()

        author = SubElement(post, "author")
        SubElement(author, "name").text = "blissful"
        SubElement(author, "email").text = "blissful@sunsetglow.net"
    # fmt: on

    tree = ElementTree(feed)
    with open("dist/atom.xml", "wb") as fh:
        tree.write(fh, encoding="utf-8", xml_declaration=True)


def main():
    os.chdir(PROJECT_DIR)

    with Path("src/posts/index.json").open("r") as fp:
        posts = {k: PostMeta.parse(k, v) for k, v in json.load(fp).items()}

    r = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    commit = r.stdout.strip()

    empty_dist()
    shutil.copytree("src/assets", "dist/assets")
    compile_index(posts, commit)
    compile_posts(posts, commit)
    compile_feed(posts)


if __name__ == "__main__":
    main()
