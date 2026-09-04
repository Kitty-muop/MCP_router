"""File transformation pipeline: Markdown to HTML."""
import pathlib
from typing import Iterator

import cocoindex as coco
from cocoindex.connectors import localfs
from cocoindex.resources.file import FileLike, PatternFilePathMatcher


@coco.lifespan
def coco_lifespan(builder: coco.EnvironmentBuilder) -> Iterator[None]:
    builder.settings.db_path = pathlib.Path("./cocoindex.db")
    yield


@coco.fn(memo=True)
async def transform_markdown(file: FileLike, outdir: pathlib.Path) -> None:
    content = await file.read_text()
    html = convert_md_to_html(content)
    outname = file.file_path.path.stem + ".html"
    localfs.declare_file(outdir / outname, html, create_parent_dirs=True)


def convert_md_to_html(md: str) -> str:
    import markdown
    return markdown.markdown(md, extensions=["fenced_code", "tables", "toc"])


@coco.fn
async def app_main(sourcedir: pathlib.Path, outdir: pathlib.Path) -> None:
    files = localfs.walk_dir(
        sourcedir,
        recursive=True,
        path_matcher=PatternFilePathMatcher(included_patterns=["**/*.md"]),
    )
    await coco.mount_each(transform_markdown, files.items(), outdir)


app = coco.App(
    coco.AppConfig(name="file_transform"),
    app_main,
    sourcedir=pathlib.Path("./data"),
    outdir=pathlib.Path("./out"),
)