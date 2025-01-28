import os
import re
from copy import deepcopy
from typing import Literal, TypeVar

import jinja2
from deepmerge import always_merger

import rev_tun

NamingStyle = Literal[
    "snake_style",
    "kebab-style",
    "camelStyle",
    "PascalStyle",
    "CONSTANT_STYLE",
]


def convert_to(name: str, style: NamingStyle) -> str:
    words: list[str]

    if "-" in name:
        words = name.split("-")
    elif "_" in name:
        words = name.split("_")
    else:
        words = re.findall(r"[A-Z][^A-Z]*|[^A-Z]+", name)

    words = [word.lower() for word in words]

    match style:
        case "snake_style":
            return "_".join(words)
        case "kebab-style":
            return "-".join(words)
        case "camelStyle":
            return words[0] + "".join(word.capitalize() for word in words[1:])
        case "PascalStyle":
            return "".join(word.capitalize() for word in words)
        case "CONSTANT_STYLE":
            return "_".join(word.upper() for word in words)
        case _:
            raise ValueError(f"Unsupported naming style: {style}")


def check_root(raise_exception: bool = True) -> bool:
    if not (is_root := os.geteuid() == 0) and raise_exception:
        raise PermissionError("Root privileges are required")

    return is_root


def merge(base: dict, update: dict) -> dict:
    return always_merger.merge(deepcopy(base), update)


T = TypeVar("T")


def mutually_exclusive(*args: T) -> T | None:
    match [arg for arg in args if arg is not None]:
        case [arg]:
            return arg
        case _:
            return None


template_env = jinja2.Environment(loader=jinja2.PackageLoader(rev_tun.__name__))
