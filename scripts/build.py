#!/usr/bin/env python3

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import jinja2  # type: ignore


def formatdate(x: str) -> str:
    """Convert 2024/06/08 to June 8, 2024"""
    dt = datetime.strptime(x, "%Y-%m-%d")
    return dt.strftime("%B %-d, %Y")


je = jinja2.Environment()
je.filters["formatdate"] = formatdate


def empty_dist() -> None:
    # Removing and recreating the directory messes with the `make watch+serve` workflow. So we
    # instead empty the directory each time..
    for f in Path("dist/").iterdir():
        if f.is_file():
            f.unlink()
        elif f.is_dir():
            shutil.rmtree(f)
        else:
            raise Exception(f"{f} is not a file or directory.")
    Path("dist/").mkdir(exist_ok=True)


def compile_posts():
    Path("dist/posts").mkdir()
    with Path("src/posts/template.jinja").open("r") as fp:
        tpl = je.from_string(fp.read())
    with Path("src/posts/index.json").open("r") as fp:
        meta = json.load(fp)
    for f in Path("src/posts").iterdir():
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

        # Wrap the post with a Jinja template.
        postmeta = meta[f.stem]
        post = tpl.render(meta=postmeta, body=post)

        # Write the compiled post.
        with Path("dist", *f.parts[1:]).with_suffix(".html").open("w") as fp:
            fp.write(post)


def main():
    os.chdir(os.environ["PROJECT_ROOT"])

    empty_dist()
    shutil.copytree("src/assets", "dist/assets")
    shutil.copyfile("src/index.html", "dist/index.html")
    compile_posts()


if __name__ == "__main__":
    main()
