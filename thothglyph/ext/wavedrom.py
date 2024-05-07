import os
import re
import wavedrom

from thothglyph.util.svg import svg2pdf, svg2png
from thothglyph.node import logging

logger = logging.getLogger(__file__)


def customblock_write_html(self, node):
    text = node.text
    svg = wavedrom.render(text)  # type: ignore
    self.data += '<div>\n'
    self.data += '<!--\n{}\n-->\n'.format(text)
    svgstr = str(svg._repr_svg_())
    svgstr = re.sub(r';\n *', r'; ', svgstr, flags=re.MULTILINE | re.DOTALL)
    self.data += svgstr
    self.data += '</div>\n'


def customblock_write_latex(self, node):
    text = node.text
    svg = wavedrom.render(text)  # type: ignore
    w = svg.attribs['width']
    fname = os.path.join(self.tmpdirname, node.treeid() + '.pdf')
    svg2pdf(bytestring=svg._repr_svg_(), write_to=fname)
    w = '{}bp'.format(int(w * self.bp_scale))
    self.data += '\\tgincludegraphics[{}]{{{}}}\n\n'.format(w, fname)


def customblock_write_pdf(self, node):
    customblock_write_latex(self, node)


# def customblock_write_pdf(self, node):
#     customblock_write_latex(self, node)
#     text = node.text
#     svg = wavedrom.render(text)
#     svg_io = io.StringIO(svg._repr_svg_())
#     drawing = svg2rlg(svg_io)
#     fname = os.path.join(self.tmpdirname, node.treeid() + '.pdf')
#     renderPDF.drawToFile(drawing, fname)

def customblock_write_docx(self, node):
    text = node.text
    svg = wavedrom.render(text)  # type: ignore
    fname = os.path.join(self.tmpdirname, node.treeid() + '.pdf')
    svg2png(bytestring=svg._repr_svg_(), write_to=fname, scale=0.625)
    p = self._add_paragraph()
    if p:
        r = p.add_run()
        r.add_picture(fname)
