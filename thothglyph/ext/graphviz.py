import os
import re
import cairosvg
import graphviz
from thothglyph.node import logging

logger = logging.getLogger(__file__)


def customblock_write_html(self, node):
    text = node.text
    graph = graphviz.Source(text)  # type: ignore
    svgstr = graph.pipe(format='svg').decode('utf-8')
    svgstr = re.sub(r'.+<svg', r'<svg', svgstr, flags=re.MULTILINE | re.DOTALL)
    self.data += '<div>\n'
    self.data += '<!--\n{}\n-->\n'.format(text)
    self.data += svgstr
    self.data += '</div>\n'


def customblock_write_latex(self, node):
    text = node.text
    graph = graphviz.Source(text)  # type: ignore
    svgstr = graph.pipe(format='svg')
    fname = os.path.join(self.tmpdirname, node.treeid() + '.pdf')
    cairosvg.svg2pdf(bytestring=svgstr, write_to=fname)
    m = re.match(
        r'.+<svg width="(.+)pt" height="(.+)pt"', svgstr.decode(),
        flags=re.MULTILINE | re.DOTALL
    )
    assert m
    w, _ = int(m.group(1)), int(m.group(2))
    wstr = '{}bp'.format(int(w * self.bp_scale))
    self.data += '\\tgincludegraphics[{}]{{{}}}\n\n'.format(wstr, fname)


def customblock_write_pdf(self, node):
    customblock_write_latex(self, node)
