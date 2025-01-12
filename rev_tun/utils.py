import os
import re
from typing import Literal

type NamingStyle = Literal["snake", "kebab", "camel", "pascal", "constant"]


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
        case "snake":
            return "_".join(words)
        case "kebab":
            return "-".join(words)
        case "camel":
            return words[0] + "".join(word.capitalize() for word in words[1:])
        case "pascal":
            return "".join(word.capitalize() for word in words)
        case "constant":
            return "_".join(word.upper() for word in words)
        case _:
            raise ValueError(f"Unsupported naming style: {style}")


def check_root():
    if os.geteuid() != 0:
        raise PermissionError("Root privileges are required")
