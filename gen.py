#!/usr/bin/env python3
"""Draw the theme's images and write theme.txt.

OUT must already hold regular.pf2 and semibold.pf2, and may hold mono.pf2
and background.png; build.sh makes them.
"""

import argparse
import struct
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FRAME = (74, 73, 74)
FRAME_EDGE = (7, 7, 7)
FRAME_RIM = [(60, 51, 49), (71, 65, 64), (73, 71, 71)]
CAPTION = (255, 230, 192)
RIDGE_DARK = (67, 67, 67)
RIDGE_LIGHT = (83, 82, 83)
LIST = (59, 57, 59)
SCROLL_TRACK = (76, 73, 73)
SCROLL_THUMB = ((217, 217, 217), (181, 181, 181))
BUTTON_TEXT = (28, 28, 28)

# top edge, face, bottom edge, as in the game's dialog buttons
GREY = (
    [(208, 208, 208), (180, 180, 180), (160, 160, 160)],
    (164, 164, 164),
    [(160, 160, 160), (106, 106, 106), (33, 33, 33)],
)
GREEN = (
    [(156, 219, 160), (127, 193, 132), (112, 186, 117)],
    (121, 198, 125),
    [(112, 186, 117), (68, 122, 73), (19, 52, 22)],
)

# rows: light line, fade, flat, fade, dark line
ROW_TOP = [(81, 78, 81), (47, 46, 47), (55, 54, 55), (57, 56, 57)]
ROW_BOTTOM = [(57, 56, 57), (55, 54, 55), (47, 46, 47), (27, 26, 27)]
SELECTED = (244, 204, 126)
SELECTED_TOP = [(69, 47, 13), (115, 89, 46), (191, 155, 88), (238, 200, 123)]
SELECTED_BOTTOM = [(239, 200, 123), (221, 191, 134), (196, 180, 150), (121, 111, 96)]

# the longest entries nixos writes: a specialisation default of a 4 digit
# generation, and a typical os-prober name
LONGEST = [
    "NixOS - Configuration 9999 - Default (2026-12-31 - 26.05.20261231.abcdef0)",
    "Windows Boot Manager (on /dev/nvme0n1p1)",
]


def pf2(path):
    """name and advance widths of a grub font"""
    data = path.read_bytes()
    name, index, i = None, [], 0
    while i < len(data):
        tag, size = data[i : i + 4], struct.unpack(">I", data[i + 4 : i + 8])[0]
        body = data[i + 8 : i + 8 + size]
        if tag == b"NAME":
            name = body.rstrip(b"\0").decode()
        elif tag == b"CHIX":
            index = [struct.unpack(">IBI", body[j : j + 9]) for j in range(0, size, 9)]
        elif tag == b"DATA":
            break
        i += 8 + size
    widths = {}
    for code, _, at in index:
        # codes past unicode are glyph variants grub picks itself
        if code < 0x110000:
            widths[chr(code)] = struct.unpack(">h", data[at + 8 : at + 10])[0]
    return name, widths


def text_width(widths, text):
    missing = set(text) - widths.keys()
    if missing:
        raise ValueError(f"font has no glyph for {''.join(sorted(missing))!r}")
    return sum(widths[c] for c in text)


def offset(base, px):
    """grub position: a percentage plus or minus pixels"""
    return f"{base}%-{px}" if px >= 0 else f"{base}%+{-px}"


class Theme:
    def __init__(self, out, scale, title, rows, corner, width, longest, font_dir):
        self.out = out
        self.s = scale
        self.title = title
        self.rows = rows
        self.corner = corner
        self.width = width
        self.longest = longest
        self.font_dir = font_dir

    def px(self, v):
        return max(1, round(v * self.s))

    def font(self, weight, size):
        path = self.font_dir / f"TitilliumWeb-{weight}.ttf"
        return ImageFont.truetype(str(path), self.px(size))

    def save(self, img, name):
        img.save(self.out / name)

    def lines(self, w, h, top, face, bottom):
        """a strip: top lines, flat face, bottom lines, each line one scaled px"""
        img = Image.new("RGBA", (w, h), face)
        draw = ImageDraw.Draw(img)
        line = self.px(1)
        for i, c in enumerate(top):
            draw.rectangle([0, i * line, w - 1, (i + 1) * line - 1], fill=c)
        for i, c in enumerate(reversed(bottom)):
            draw.rectangle([0, h - (i + 1) * line, w - 1, h - i * line - 1], fill=c)
        return img

    def ridges(self, draw, x0, y0, x1, y1):
        """the recessed drag handle: vertical ridges"""
        line = self.px(1)
        step = self.px(2)
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=RIDGE_DARK)
        for x in range(x0 + step, x1 - step, 2 * step):
            draw.rectangle(
                [x, y0 + line, x + step - 1, y1 - line - 1], fill=RIDGE_LIGHT
            )
        draw.rectangle([x0, y0, x1 - 1, y0 + line - 1], fill=(62, 60, 61))
        draw.rectangle([x0, y1 - line, x1 - 1, y1 - 1], fill=(77, 75, 76))

    def arrow_button(self, w, h, colors, point, label, font):
        """a dialog button with an arrow tip on the left or right"""
        tip = self.px(10)
        strip = self.lines(w, h, *colors)
        if point == "left":
            poly = [(tip, 0), (w - 1, 0), (w - 1, h - 1), (tip, h - 1), (0, h // 2)]
        else:
            poly = [
                (0, 0),
                (w - tip - 1, 0),
                (w - 1, h // 2),
                (w - tip - 1, h - 1),
                (0, h - 1),
            ]
        mask = Image.new("L", (w, h))
        ImageDraw.Draw(mask).polygon(poly, fill=255)
        img = Image.new("RGBA", (w, h))
        img.paste(strip, mask=mask)
        draw = ImageDraw.Draw(img)
        draw.line(poly + [poly[0]], fill=(33, 33, 33, 160), width=self.px(1))
        pad = tip + self.px(16)
        if point == "left":
            draw.text((pad, h // 2), label, font=font, fill=BUTTON_TEXT, anchor="lm")
        else:
            draw.text(
                (w - pad, h // 2), label, font=font, fill=BUTTON_TEXT, anchor="rm"
            )
        return img

    def inset(self, draw, x0, y0, x1, y1, fill):
        """a sunken area: dark top and left edges, light bottom and right"""
        line = self.px(1)
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], fill=fill)
        for i, c in enumerate([(0, 0, 0), (29, 27, 29), (42, 42, 42)]):
            draw.rectangle([x0, y0 + i * line, x1 - 1, y0 + (i + 1) * line - 1], fill=c)
            draw.rectangle([x0 + i * line, y0, x0 + (i + 1) * line - 1, y1 - 1], fill=c)
        draw.rectangle([x0, y1 - line, x1 - 1, y1 - 1], fill=(68, 65, 65))
        draw.rectangle([x1 - line, y0, x1 - 1, y1 - 1], fill=(68, 65, 65))

    def three_slice(self, img, name):
        w, h = img.size
        cap = self.px(4)
        self.save(img.crop((0, 0, cap, h)), f"{name}_w.png")
        self.save(img.crop((w // 2, 0, w // 2 + 1, h)), f"{name}_c.png")
        self.save(img.crop((w - cap, 0, w, h)), f"{name}_e.png")

    def nine_slice(self, img, name, corner=4):
        w, h = img.size
        c = self.px(corner)
        boxes = {
            "nw": (0, 0, c, c),
            "n": (c, 0, w - c, c),
            "ne": (w - c, 0, w, c),
            "w": (0, c, c, h - c),
            "c": (c, c, w - c, h - c),
            "e": (w - c, c, w, h - c),
            "sw": (0, h - c, c, h),
            "s": (c, h - c, w - c, h),
            "se": (w - c, h - c, w, h),
        }
        for part, box in boxes.items():
            self.save(img.crop(box), f"{name}_{part}.png")

    def write(self):
        s = self.px
        out = self.out
        regular, regular_widths = pf2(out / "regular.pf2")
        semibold, _ = pf2(out / "semibold.pf2")

        row_h = s(28)
        text_left = s(10)
        scroll_w = s(12)
        longest = max(text_width(regular_widths, t) for t in self.longest)
        # text, padding both sides, and room for the scrollbar
        menu_w = max(s(self.width), text_left + longest + s(16) + scroll_w + s(4))

        pad = s(12)
        caption_h = s(32)
        list_top = s(6) + caption_h + s(6)
        border = s(3)
        list_h = self.rows * row_h + 2 * border
        footer_h = s(32)
        footer_top = list_top + list_h + pad
        win_w = menu_w + 2 * border + 2 * pad
        win_h = footer_top + footer_h + pad
        half_w = win_w // 2
        lift = round(win_h * 0.5)

        img = Image.new("RGBA", (win_w, win_h))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, win_w - 1, win_h - 1], fill=FRAME_EDGE)
        for i, c in enumerate(FRAME_RIM + [FRAME]):
            d = s(2) + i * s(1)
            draw.rectangle([d, d, win_w - d - 1, win_h - d - 1], fill=c)

        caption_font = self.font("SemiBold", 18)
        cy = s(6) + caption_h // 2
        draw.text((pad, cy), self.title, font=caption_font, fill=CAPTION, anchor="lm")
        drag_x = pad + round(draw.textlength(self.title, font=caption_font)) + s(10)
        self.ridges(draw, drag_x, cy - s(11), win_w - pad, cy + s(11))

        self.inset(draw, pad, list_top, win_w - pad, list_top + list_h, LIST)

        button_font = self.font("SemiBold", 18)
        back_w = s(112)
        boot_w = max(s(200), win_w // 3)
        back = self.arrow_button(back_w, footer_h, GREY, "left", "Back", button_font)
        boot = self.arrow_button(boot_w, footer_h, GREEN, "right", "Boot", button_font)
        img.alpha_composite(back, (pad, footer_top))
        img.alpha_composite(boot, (win_w - pad - boot_w, footer_top))
        bar_x0 = pad + back_w + s(8)
        bar_x1 = win_w - pad - boot_w - s(8)
        self.ridges(
            draw, bar_x0, footer_top + s(4), bar_x1, footer_top + footer_h - s(4)
        )
        self.save(img, "window.png")

        self.three_slice(self.lines(s(40), row_h, ROW_TOP, LIST, ROW_BOTTOM), "item")
        self.three_slice(
            self.lines(s(40), row_h, SELECTED_TOP, SELECTED, SELECTED_BOTTOM),
            "selected",
        )
        track = Image.new("RGBA", (scroll_w, s(40)), SCROLL_TRACK)
        ImageDraw.Draw(track).rectangle(
            [0, 0, scroll_w - 1, s(40) - 1], outline=(33, 32, 32), width=s(1)
        )
        # grub only draws the scrollbar when the frame's and thumb's side
        # pieces together fit in its width
        self.nine_slice(track, "scroll_frame", corner=1)
        thumb = self.lines(
            scroll_w, s(40), [SCROLL_THUMB[0]], SCROLL_THUMB[1], [(120, 120, 120)]
        )
        self.nine_slice(thumb, "scroll_thumb", corner=1)
        # the countdown fills the footer's drag handle in orange
        self.three_slice(Image.new("RGBA", (s(20), s(24))), "bar")
        self.three_slice(Image.new("RGBA", (s(20), s(24)), (250, 168, 56, 150)), "fill")
        terminal = Image.new("RGBA", (s(40), s(40)))
        self.inset(ImageDraw.Draw(terminal), 0, 0, s(40), s(40), (0, 0, 0))
        self.nine_slice(terminal, "terminal")

        head = ['title-text: ""', 'desktop-color: "#000000"']
        if (out / "background.png").exists():
            head += [
                'desktop-image: "background.png"',
                'desktop-image-scale-method: "crop"',
            ]
        if (out / "mono.pf2").exists():
            head.append(f'terminal-font: "{pf2(out / "mono.pf2")[0]}"')

        corner = ""
        if self.corner:
            corner = f"""
+ label {{
  left = {s(2)}
  top = {s(1)}
  width = 100%
  height = {s(24)}
  color = "#ffffff"
  font = "{regular}"
  text = "{self.corner}"
}}
"""

        (out / "theme.txt").write_text("\n".join(head) + f"""
terminal-box: "terminal_*.png"
terminal-left: "10%"
terminal-top: "10%"
terminal-width: "80%"
terminal-height: "80%"
terminal-border: "0"

+ boot_menu {{
  left = 50%-{half_w - pad - border}
  top = {offset(50, lift - list_top - border)}
  width = {menu_w}
  height = {self.rows * row_h}
  item_font = "{regular}"
  item_color = "#fcfcfc"
  selected_item_color = "#040400"
  item_height = {row_h}
  item_padding = 0
  item_spacing = 0
  icon_width = 0
  icon_height = 0
  item_icon_space = {text_left}
  item_pixmap_style = "item_*.png"
  selected_item_pixmap_style = "selected_*.png"
  scrollbar = true
  scrollbar_slice = "center"
  scrollbar_left_pad = {s(4)}
  scrollbar_right_pad = 0
  scrollbar_width = {scroll_w}
  scrollbar_frame = "scroll_frame_*.png"
  scrollbar_thumb = "scroll_thumb_*.png"
}}

+ progress_bar {{
  id = "__timeout__"
  left = 50%-{half_w - bar_x0}
  top = {offset(50, lift - footer_top - s(4))}
  width = {bar_x1 - bar_x0}
  height = {footer_h - s(8)}
  bar_style = "bar_*.png"
  highlight_style = "fill_*.png"
  text = ""
}}

+ label {{
  id = "__timeout__"
  left = 50%-{half_w - bar_x0}
  top = {offset(50, lift - footer_top)}
  width = {bar_x1 - bar_x0}
  height = {footer_h}
  align = "center"
  color = "#ffffff"
  font = "{semibold}"
  text = "Booting in %d s"
}}
{corner}
# grub paints components last to first, so the window goes last to sit
# under the menu
+ image {{
  left = 50%-{half_w}
  top = {offset(50, lift)}
  width = {win_w}
  height = {win_h}
  file = "window.png"
}}
""")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("out", type=Path)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--title", default="Boot")
    p.add_argument("--rows", type=int, default=10)
    p.add_argument("--corner", default="", help="text in the top left corner")
    p.add_argument("--width", type=int, default=0, help="minimum list width at scale 1")
    p.add_argument(
        "--longest",
        action="append",
        help="an entry that must fit; repeat for more, replaces the defaults",
    )
    p.add_argument("--fonts", type=Path, default=Path(__file__).parent / "fonts")
    a = p.parse_args()
    # theme.txt strings have no escapes
    if '"' in a.corner:
        p.error("--corner can not hold a double quote")
    a.out.mkdir(parents=True, exist_ok=True)
    longest = a.longest or LONGEST
    Theme(a.out, a.scale, a.title, a.rows, a.corner, a.width, longest, a.fonts).write()


if __name__ == "__main__":
    main()
