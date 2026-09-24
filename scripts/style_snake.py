"""Give snk's animated SVGs a minimal, theme-aware snake design."""

import argparse
import os
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)

FILES = {
    "github-contribution-grid-snake.svg": {
        "head": ("#1a7f37", "#56d364"),
        "body": ("#278b3d", "#3faa50", "#56d364"),
        "shadow": "rgba(26, 127, 55, .35)",
    },
    "github-contribution-grid-snake-dark.svg": {
        "head": ("#3fb950", "#7ee787"),
        "body": ("#4ecb60", "#65d875", "#7ee787"),
        "shadow": "rgba(126, 231, 135, .65)",
    },
}


def tag(name: str) -> str:
    return f"{{{SVG_NS}}}{name}"


def style_svg(source: bytes, colors: dict) -> bytes:
    root = ET.fromstring(source)
    if root.tag != tag("svg"):
        raise ValueError("Input is not an SVG")

    style = root.find(tag("style"))
    if style is None or not style.text:
        raise ValueError("snk animation styles are missing")

    segments = []
    for element in root:
        if element.tag != tag("rect"):
            continue
        match = re.fullmatch(r"s s([0-3])", element.get("class", ""))
        if match:
            segments.append((int(match.group(1)), element))

    if sorted(index for index, _ in segments) != list(range(4)):
        raise ValueError("Expected four snk snake segments")
    for index in range(4):
        if f"@keyframes s{index}" not in style.text or f".s.s{index}" not in style.text:
            raise ValueError(f"snk animation for segment {index} is missing")
    if not any(element.get("class", "").startswith("c") for element in root):
        raise ValueError("Contribution grid is missing")

    defs = ET.Element(tag("defs"))
    gradient = ET.SubElement(
        defs,
        tag("linearGradient"),
        {"id": "snake-head-gradient", "x1": "0", "y1": "0", "x2": "1", "y2": "1"},
    )
    ET.SubElement(gradient, tag("stop"), {"offset": "0%", "stop-color": colors["head"][0]})
    ET.SubElement(gradient, tag("stop"), {"offset": "100%", "stop-color": colors["head"][1]})
    root.insert(1, defs)

    for index, segment in segments:
        position = list(root).index(segment)
        root.remove(segment)

        group = ET.Element(tag("g"), {"class": f"s s{index}"})
        segment.attrib.pop("class")
        segment.set("class", "snake-head" if index == 0 else "snake-body")
        segment.set("fill", "url(#snake-head-gradient)" if index == 0 else colors["body"][index - 1])
        radius = min(float(segment.get("width", "0")), float(segment.get("height", "0"))) / 2
        segment.set("rx", f"{radius:g}")
        segment.set("ry", f"{radius:g}")
        group.append(segment)

        if index == 0:
            x = float(segment.get("x", "0"))
            y = float(segment.get("y", "0"))
            width = float(segment.get("width", "0"))
            height = float(segment.get("height", "0"))
            ET.SubElement(
                group,
                tag("ellipse"),
                {
                    "class": "snake-highlight",
                    "cx": f"{x + width * 0.35:g}",
                    "cy": f"{y + height * 0.3:g}",
                    "rx": f"{width * 0.19:g}",
                    "ry": f"{height * 0.1:g}",
                    "fill": "#ffffff",
                },
            )

        root.insert(position, group)

    style.text += f"""
.s.s0 {{ filter: drop-shadow(0 0 2px {colors['shadow']}); }}
.snake-highlight {{ opacity: .3; animation: snake-pulse 2.4s ease-in-out infinite; }}
@keyframes snake-pulse {{ 50% {{ opacity: .65; }} }}
@media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; }} }}
"""
    return ET.tostring(root, encoding="utf-8") + b"\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="Directory containing both snk SVG outputs")
    args = parser.parse_args()

    styled = {
        args.directory / name: style_svg((args.directory / name).read_bytes(), colors)
        for name, colors in FILES.items()
    }
    for path, contents in styled.items():
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
            temporary.write(contents)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)


if __name__ == "__main__":
    main()
