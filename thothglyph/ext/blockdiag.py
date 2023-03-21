import os
import re
import cairosvg
import blockdiag.parser
import blockdiag.builder
import blockdiag.drawer
import actdiag.parser
import actdiag.builder
import actdiag.drawer
import seqdiag.parser
import seqdiag.builder
import seqdiag.drawer
import nwdiag.parser
import nwdiag.builder
import nwdiag.drawer
import rackdiag.parser
import rackdiag.builder
import rackdiag.drawer
import packetdiag.parser
import packetdiag.builder
import packetdiag.drawer
from thothglyph.node import logging

logger = logging.getLogger(__file__)


def _get_svgstr(text):
    if text.startswith('blockdiag'):
        parser = blockdiag.parser
        Builder = blockdiag.builder.ScreenNodeBuilder
        Drawer = blockdiag.drawer.DiagramDraw
    elif text.startswith('actdiag'):
        parser = actdiag.parser
        Builder = actdiag.builder.ScreenNodeBuilder
        Drawer = actdiag.drawer.DiagramDraw
    elif text.startswith('seqdiag'):
        parser = seqdiag.parser
        Builder = seqdiag.builder.ScreenNodeBuilder
        Drawer = seqdiag.drawer.DiagramDraw
    elif text.startswith('nwdiag'):
        parser = nwdiag.parser
        Builder = nwdiag.builder.ScreenNodeBuilder
        Drawer = nwdiag.drawer.DiagramDraw
    elif text.startswith('rackdiag'):
        parser = rackdiag.parser
        Builder = rackdiag.builder.ScreenNodeBuilder
        Drawer = rackdiag.drawer.DiagramDraw
    elif text.startswith('packetdiag'):
        parser = packetdiag.parser
        Builder = packetdiag.builder.ScreenNodeBuilder
        Drawer = packetdiag.drawer.DiagramDraw
    tree = parser.parse_string(text)
    diagram = Builder.build(tree)
    draw = Drawer('svg', diagram)
    draw.draw()
    draw.save()
    svg = draw.drawer.target.svg
    x, y, w, h = svg.attributes['viewBox'].split(' ')
    svg.attributes['width'] = w
    svg.attributes['height'] = h
    svgstr = draw.drawer.target.svg.to_xml()
    return svgstr, w, h

def customblock_write_html(self, node):
    text = node.text
    svgstr, w, h = _get_svgstr(text)
    svgstr = re.sub(r'.+<svg', r'<svg', svgstr, flags=re.MULTILINE | re.DOTALL)
    lines = list(svgstr.splitlines())
    for i, line in enumerate(lines[:]):
        m = re.match(r'( *<text )([^>]+)( x=.+ y=.+>)', line)
        if m:
            oldstyle = m.group(2)
            newstyle = oldstyle.replace('="', ':').replace('"', ';')
            newstyle = 'style="' + newstyle + '"'
            lines[i] = m.group(1) + newstyle + m.group(3)
    svgstr = '\n'.join(lines)
    self.data += '<div>\n'
    self.data += '<!--\n{}\n-->\n'.format(text)
    self.data += svgstr
    self.data += '</div>\n'


def customblock_write_latex(self, node):
    text = node.text
    svgstr, w, h = _get_svgstr(text)
    w, h = int(w), int(h)
    fname = os.path.join(self.tmpdirname, node.treeid() + '.pdf')
    cairosvg.svg2pdf(bytestring=svgstr, write_to=fname)
    w = '{}bp'.format(int(w * self.bp_scale))
    self.data += '\\tgincludegraphics[{}]{{{}}}\n\n'.format(w, fname)

def customblock_write_pdf(self, node):
    customblock_write_latex(self, node)
