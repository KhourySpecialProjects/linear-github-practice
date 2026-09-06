"""Command line entry point.

    python -m generator validate         # check every bio file (what CI runs)
    python -m generator build            # render the site into dist/
    python -m generator serve            # build, then serve dist/ on :8000
"""

from __future__ import annotations

import argparse
import functools
import http.server
import os
import socketserver
import sys
from pathlib import Path

from .bios import Problem, load_bios
from .config import ConfigError, SiteConfig
from .render import build


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--bios", type=Path, default=Path("bios"), help="directory of bio Markdown files")
    parser.add_argument("--config", type=Path, default=Path("site.yml"), help="site configuration file")


def _report(problems: tuple[Problem, ...]) -> None:
    """Print problems, as GitHub Actions annotations when running in CI."""
    annotate = os.environ.get("GITHUB_ACTIONS") == "true"
    for problem in problems:
        if annotate:
            print(f"::error file={problem.path}::{problem.message}")
        print(f"  {problem}", file=sys.stderr)


def _validate(args: argparse.Namespace, config: SiteConfig) -> int:
    bios, problems = load_bios(args.bios, config)
    if problems:
        print(f"{len(problems)} problem(s) found in {args.bios}/:", file=sys.stderr)
        _report(problems)
        print(
            "\nFix the files listed above, then re-run: python -m generator validate",
            file=sys.stderr,
        )
        return 1
    print(f"{len(bios)} bio file(s) valid.")
    return 0


def _build(args: argparse.Namespace, config: SiteConfig) -> int:
    bios, problems = load_bios(args.bios, config)
    if problems:
        print(f"{len(problems)} problem(s) found in {args.bios}/:", file=sys.stderr)
        _report(problems)
        return 1
    result = build(args.bios, config, args.out, strict=False)
    print(f"Built {result.pages} page(s) for {result.bios} bio(s) into {result.out_dir}/")
    return 0


def _serve(args: argparse.Namespace, config: SiteConfig) -> int:
    status = _build(args, config)
    if status:
        return status
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(args.out))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", args.port), handler) as httpd:
        print(f"Serving {args.out}/ at http://localhost:{args.port} (Ctrl-C to stop)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="generator", description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="check bio files without rendering")
    _add_common_args(validate)
    validate.set_defaults(handler=_validate)

    build_cmd = subparsers.add_parser("build", help="render the static site")
    _add_common_args(build_cmd)
    build_cmd.add_argument("--out", type=Path, default=Path("dist"), help="output directory")
    build_cmd.set_defaults(handler=_build)

    serve = subparsers.add_parser("serve", help="build, then serve the site locally")
    _add_common_args(serve)
    serve.add_argument("--out", type=Path, default=Path("dist"), help="output directory")
    serve.add_argument("--port", type=int, default=8000, help="port to serve on")
    serve.set_defaults(handler=_serve)

    args = parser.parse_args(argv)
    try:
        config = SiteConfig.load(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return int(args.handler(args, config))


if __name__ == "__main__":
    raise SystemExit(main())
