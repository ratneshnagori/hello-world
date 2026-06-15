#!/usr/bin/env python3
"""Reusable PDF framework for systems-design interview-prep guides.

Provides a styled FPDF subclass, content-block renderers, and small
diagram primitives (boxes, arrows) used to draw architecture diagrams.
"""

from fpdf import FPDF

NAVY = (15, 32, 64)
BLUE = (33, 102, 172)
LIGHT = (236, 242, 250)
GREY = (90, 90, 90)
GREEN = (34, 120, 70)
RED = (170, 45, 45)
ORANGE = (200, 120, 20)
PURPLE = (108, 64, 150)
TEAL = (20, 120, 130)

PUBLIC_FILL = (210, 232, 214)
PRIVATE_FILL = (213, 226, 245)
ISOLATED_FILL = (245, 222, 222)


def clean(text: str) -> str:
    """Replace non-latin-1 chars so core fonts render correctly."""
    repl = {
        "\u2192": "->", "\u2190": "<-", "\u2194": "<->",
        "\u2022": "-", "\u2013": "-", "\u2014": "-",
        "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u00d7": "x", "\u2265": ">=", "\u2264": "<=",
        "\u2248": "~", "\u00b7": "-", "\u2705": "", "\u274c": "",
    }
    for k, v in repl.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


class PDF(FPDF):
    def __init__(self, running_title="Systems Design Interview Prep"):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.running_title = running_title
        self.set_auto_page_break(auto=True, margin=18)
        self.set_margins(18, 18, 18)

    # ---- page furniture ----
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, clean(self.running_title), align="L",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BLUE)
        self.set_line_width(0.3)
        self.line(18, 26, 192, 26)
        self.ln(6)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

    # ---- headings & text ----
    def h1(self, num, title):
        if self.get_y() > 230:
            self.add_page()
        self.start_section(f"{num}. {title}")
        self.ln(2)
        self.set_fill_color(*NAVY)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, clean(f"  {num}.  {title}"), new_x="LMARGIN",
                  new_y="NEXT", fill=True)
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def page_title(self, title):
        self.set_font("Helvetica", "B", 18)
        self.set_text_color(*NAVY)
        self.cell(0, 12, clean(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*BLUE)
        self.line(18, self.get_y(), 192, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def h2(self, title):
        if self.get_y() > 245:
            self.add_page()
        self.set_font("Helvetica", "B", 11.5)
        self.set_text_color(*BLUE)
        self.cell(0, 8, clean(title), new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def body(self, text):
        self.set_font("Helvetica", "", 10.5)
        self.set_text_color(20, 20, 20)
        self.multi_cell(0, 5.6, clean(text))
        self.ln(1.5)

    def bullets(self, items, color=None):
        self.set_font("Helvetica", "", 10.5)
        for it in items:
            x = self.get_x()
            self.set_text_color(*(color or BLUE))
            self.cell(5, 5.6, clean("-"))
            self.set_text_color(20, 20, 20)
            self.multi_cell(0, 5.6, clean(it))
            self.set_x(x)
        self.ln(1.5)

    def kv_bullets(self, pairs):
        self.set_font("Helvetica", "", 10.5)
        for key, val in pairs:
            x = self.get_x()
            self.set_text_color(*BLUE)
            self.cell(5, 5.6, clean("-"))
            self.set_font("Helvetica", "B", 10.5)
            self.set_text_color(*NAVY)
            kw = self.get_string_width(clean(key + ": "))
            self.cell(kw, 5.6, clean(key + ": "))
            self.set_font("Helvetica", "", 10.5)
            self.set_text_color(20, 20, 20)
            self.multi_cell(0, 5.6, clean(val))
            self.set_x(x)
        self.ln(1.5)

    def callout(self, title, text, color=BLUE):
        if self.get_y() > 235:
            self.add_page()
        y0 = self.get_y()
        x = self.get_x()
        w = 174
        self.set_xy(x + 4, y0 + 3)
        self.set_font("Helvetica", "B", 10.5)
        self.set_text_color(*color)
        self.multi_cell(w - 8, 5.4, clean(title))
        self.set_x(x + 4)
        self.set_font("Helvetica", "", 10)
        self.set_text_color(30, 30, 30)
        self.multi_cell(w - 8, 5.2, clean(text))
        y1 = self.get_y() + 3
        self.set_draw_color(*color)
        self.set_line_width(0.4)
        self.rect(x, y0, w, y1 - y0, style="D")
        self.set_fill_color(*color)
        self.rect(x, y0, 1.5, y1 - y0, style="F")
        self.set_xy(x, y1 + 2)
        self.set_text_color(0, 0, 0)

    def simple_table(self, header, rows, widths):
        self.set_font("Helvetica", "B", 9.5)
        self.set_fill_color(*NAVY)
        self.set_text_color(255, 255, 255)
        self.set_draw_color(*BLUE)
        for h, w in zip(header, widths):
            self.cell(w, 8, clean(h), border=1, align="C", fill=True)
        self.ln()
        self.set_font("Helvetica", "", 9)
        self.set_text_color(20, 20, 20)
        fill = False
        for row in rows:
            line_h = 5
            n_lines = 1
            for txt, w in zip(row, widths):
                nl = self.multi_cell(w, line_h, clean(txt), dry_run=True,
                                     output="LINES")
                n_lines = max(n_lines, len(nl))
            rh = line_h * n_lines
            if self.get_y() + rh > 270:
                self.add_page()
                self.set_font("Helvetica", "B", 9.5)
                self.set_fill_color(*NAVY)
                self.set_text_color(255, 255, 255)
                for h, w in zip(header, widths):
                    self.cell(w, 8, clean(h), border=1, align="C", fill=True)
                self.ln()
                self.set_font("Helvetica", "", 9)
                self.set_text_color(20, 20, 20)
            self.set_fill_color(*(LIGHT if fill else (255, 255, 255)))
            x0, y0 = self.get_x(), self.get_y()
            for txt, w in zip(row, widths):
                x, y = self.get_x(), self.get_y()
                self.multi_cell(w, line_h, clean(txt), border=0, fill=True,
                                max_line_height=line_h)
                self.set_xy(x + w, y)
            self.set_xy(x0, y0)
            for w in widths:
                self.cell(w, rh, "", border=1)
            self.ln(rh)
            fill = not fill
        self.ln(2)

    # ---- diagram primitives ----
    def diag_box(self, x, y, w, h, fill, edge, title=None, lines=None,
                 title_color=None, title_size=8, line_size=7):
        self.set_fill_color(*fill)
        self.set_draw_color(*edge)
        self.set_line_width(0.4)
        self.rect(x, y, w, h, style="DF")
        if title:
            self.set_font("Helvetica", "B", title_size)
            self.set_text_color(*(title_color or NAVY))
            self.set_xy(x + 2, y + 1.5)
            self.cell(w - 4, 4, clean(title))
        if lines:
            self.set_font("Helvetica", "", line_size)
            self.set_text_color(40, 40, 40)
            ly = y + 1.5 + (5 if title else 0)
            for ln in lines:
                self.set_xy(x + 2, ly)
                self.cell(w - 4, 4, clean(ln))
                ly += 4.2
        self.set_text_color(0, 0, 0)

    def diag_label(self, x, y, text, color=NAVY, size=7, bold=False, w=40,
                   align="L"):
        self.set_font("Helvetica", "B" if bold else "", size)
        self.set_text_color(*color)
        self.set_xy(x, y)
        self.cell(w, 4, clean(text), align=align)
        self.set_text_color(0, 0, 0)

    def diag_arrow(self, x1, y1, x2, y2, color=GREY, width=0.4, head=2.0):
        import math
        self.set_draw_color(*color)
        self.set_line_width(width)
        self.line(x1, y1, x2, y2)
        ang = math.atan2(y2 - y1, x2 - x1)
        for da in (math.radians(150), math.radians(-150)):
            hx = x2 + head * math.cos(ang + da)
            hy = y2 + head * math.sin(ang + da)
            self.line(x2, y2, hx, hy)

    def diag_caption(self, x, y, w, text):
        self.set_xy(x, y)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.multi_cell(w, 4.4, clean(text))
        self.set_text_color(0, 0, 0)


def cover(pdf: PDF, title, subtitle, blurb):
    pdf.add_page()
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 297, style="F")
    pdf.set_fill_color(*BLUE)
    pdf.rect(0, 86, 210, 60, style="F")
    pdf.set_xy(0, 96)
    pdf.set_font("Helvetica", "B", 32)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(210, 18, clean(title), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 14)
    pdf.cell(210, 12, clean(subtitle), align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_xy(0, 168)
    pdf.set_font("Helvetica", "I", 12)
    pdf.set_text_color(200, 215, 235)
    pdf.cell(210, 8, "Interview Preparation Guide", align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10.5)
    pdf.set_text_color(215, 225, 240)
    pdf.set_xy(25, 184)
    pdf.multi_cell(160, 6, clean(blurb), align="C")


def render_toc(pdf: PDF, outline):
    pdf.set_xy(pdf.l_margin, pdf.get_y())
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*NAVY)
    pdf.cell(174, 12, "Table of Contents", align="L", new_x="LMARGIN",
             new_y="NEXT")
    pdf.set_draw_color(*BLUE)
    pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 11)
    for section in outline:
        pdf.set_text_color(20, 20, 20)
        pdf.cell(160, 8, clean(section.name))
        pdf.set_text_color(*GREY)
        pdf.cell(0, 8, clean(str(section.page_number)), align="R",
                 new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(220, 226, 235)
        pdf.line(18, pdf.get_y(), 192, pdf.get_y())
    pdf.set_text_color(0, 0, 0)


def render_block(pdf: PDF, block):
    kind = block[0]
    if kind == "h2":
        pdf.h2(block[1])
    elif kind == "body":
        pdf.body(block[1])
    elif kind == "bullets":
        pdf.bullets(block[1])
    elif kind == "kv":
        pdf.kv_bullets(block[1])
    elif kind == "callout":
        pdf.callout(*block[1])
    elif kind == "table":
        pdf.simple_table(*block[1])
    elif kind == "diagram":
        block[1](pdf)
    else:
        raise ValueError(f"unknown block kind: {kind}")


def build_pdf(topic, out_path):
    """topic: dict with title, subtitle, summary_title, summary, blurb,
    sections=[(title, [blocks])]."""
    pdf = PDF(running_title=f"{topic['title']} - Systems Design Interview Prep")
    cover(pdf, topic["title"], topic["subtitle"], topic["blurb"])
    pdf.add_page()
    pdf.insert_toc_placeholder(render_toc, pages=1)

    pdf.page_title(topic.get("summary_title", "Executive Summary"))
    pdf.body(topic["summary"])
    pdf.ln(1)

    for i, (sec_title, blocks) in enumerate(topic["sections"], start=1):
        pdf.h1(i, sec_title)
        for block in blocks:
            render_block(pdf, block)

    pdf.output(out_path)
    return pdf.page_no()
