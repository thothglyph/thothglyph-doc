import os
import re
import subprocess

from thothglyph.util.svg import svg2pdf, svg2png
from thothglyph.error import ThothglyphError
from thothglyph.node import logging

logger = logging.getLogger(__file__)


def customblock_write_html(self, node):
    indata = node.text
    if isinstance(indata, str):
        indata = indata.encode()
    umlname = os.path.join(self.tmpdirname, node.treeid() + '.uml')
    svgname = os.path.join(self.tmpdirname, node.treeid() + '.svg')
    with open(umlname, 'wb') as f:
        f.write(indata)
    cmd = ['plantuml', '-tsvg', umlname]
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    p.communicate()
    if p.returncode != 0:
        msg = '{} command exit with code {}.'.format(cmd[0], p.returncode)
        raise ThothglyphError(msg)
    with open(svgname) as f:
        svgstr = f.read()
        self.data += '<div>\n'
        # self.data += '<!--\n{}\n-->\n'.format(node.text)
        svgstr = re.sub(r';\n *', r'; ', svgstr, flags=re.MULTILINE | re.DOTALL)
        self.data += svgstr
        self.data += '</div>\n'


def customblock_write_latex(self, node):
    indata = node.text
    if isinstance(indata, str):
        indata = indata.encode()
    umlname = os.path.join(self.tmpdirname, node.treeid() + '.uml')
    svgname = os.path.join(self.tmpdirname, node.treeid() + '.svg')
    pdfname = os.path.join(self.tmpdirname, node.treeid() + '.pdf')
    with open(umlname, 'wb') as f:
        f.write(indata)
    cmd = ['plantuml', '-tsvg', umlname]
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    p.communicate()
    if p.returncode != 0:
        msg = '{} command exit with code {}.'.format(cmd[0], p.returncode)
        raise ThothglyphError(msg)
    svg2pdf(url=svgname, write_to=pdfname)
    w = 800
    with open(svgname) as f:
        svgdata = f.read()
        if m := re.search(r'viewBox="\S+ \S+ (\S+) \S+"', svgdata, flags=re.MULTILINE | re.DOTALL):
            w = int(float(m.group(1)))
    w = '{}bp'.format(int(w * self.bp_scale))
    self.data += '\\tgincludegraphics[{}]{{{}}}\n\n'.format(w, pdfname)


def customblock_write_pdf(self, node):
    customblock_write_latex(self, node)

def customblock_write_docx(self, node):
    indata = node.text
    if isinstance(indata, str):
        indata = indata.encode()
    umlname = os.path.join(self.tmpdirname, node.treeid() + '.uml')
    svgname = os.path.join(self.tmpdirname, node.treeid() + '.svg')
    pngname = os.path.join(self.tmpdirname, node.treeid() + '.png')
    with open(umlname, 'wb') as f:
        f.write(indata)
    cmd = ['plantuml', '-tsvg', umlname]
    p = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    p.communicate()
    if p.returncode != 0:
        msg = '{} command exit with code {}.'.format(cmd[0], p.returncode)
        raise ThothglyphError(msg)
    svg2png(url=svgname, write_to=pngname, scale=0.625)
    p = self._add_paragraph()
    if p:
        r = p.add_run()
        r.add_picture(pngname)
