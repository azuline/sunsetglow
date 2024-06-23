#!/usr/bin/env python3

from __future__ import annotations
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
import dataclasses
from typing import Any

import jinja2  # type: ignore


def formatdate(x: str) -> str:
    """Convert 2024/06/08 to June 8, 2024"""
    dt = datetime.strptime(x, "%Y-%m-%d")
    return dt.strftime("%B %-d, %Y")


je = jinja2.Environment()
je.filters["formatdate"] = formatdate


@dataclasses.dataclass
class PostMeta:
    title: str
    date: str
    public: bool

    @classmethod
    def parse(cls, d: dict[str, Any]) -> PostMeta:
        return cls(
            title=d["title"],
            date=d["date"],
            public=d["public"],
        )


PostIndex = dict[str, PostMeta]


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


def compile_index(posts: PostIndex):
    with Path("src/index.jinja").open("r") as fp:
        tpl = je.from_string(fp.read())

    # Write the main index.html
    publicposts = {k: v for k, v in posts.items() if v.public}
    index = tpl.render(posts=publicposts)
    with Path("dist/index.html").open("w") as fp:
        fp.write(index)

    # Write a staging index.html
    staging = tpl.render(posts=posts)
    with Path("dist/staging.html").open("w") as fp:
        fp.write(staging)


def compile_posts(posts: PostIndex):
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
        post = tpl.render(slug=slug, meta=meta, body=post)

        # Write the compiled post.
        with Path("dist/posts", f.parts[-1]).with_suffix(".html").open("w") as fp:
            fp.write(post)


def main():
    os.chdir(os.environ["PROJECT_ROOT"])

    with Path("src/posts/index.json").open("r") as fp:
        posts = {k: PostMeta.parse(v) for k, v in json.load(fp).items()}

    empty_dist()
    shutil.copytree("src/assets", "dist/assets")
    compile_index(posts)
    compile_posts(posts)


if __name__ == "__main__":
    main()
