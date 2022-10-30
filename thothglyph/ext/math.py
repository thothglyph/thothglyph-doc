import os
import re
import subprocess

from thothglyph.node import logging

logger = logging.getLogger(__file__)


latextemplate = r'''
\documentclass[12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage{amsmath}
\usepackage{amsthm}
\usepackage{amssymb}
\usepackage{amsfonts}
\usepackage{anyfontsize}
\usepackage{bm}
\pagestyle{empty}
\begin{document}
\fontsize{16}{20}\selectfont
\begin{%s}
%s
\end{%s}
\end{document}
'''

def _get_svgstr(tmpdirname, text, mathmode):
    if tmpdirname:
        with open(os.path.join(tmpdirname, 'math.tex'), 'w', encoding='utf-8') as f:
            t = latextemplate
            latextext = t % (mathmode, text, mathmode)
            f.write(latextext)
        p = subprocess.run([
            'platex',
            '-output-directory={}'.format(tmpdirname),
            '-halt-on-error',
            '-interaction=nonstopmode',
            'math.tex',
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p = subprocess.run([
            'dvisvgm',
            '--stdout',
            '--no-fonts',
            os.path.join(tmpdirname, 'math.dvi'),
        ], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        svgstr = p.stdout.decode('utf-8', 'replace')
        svgstr = re.sub(r'.+<svg', r'<svg', svgstr, flags=re.MULTILINE | re.DOTALL)
    return svgstr


def customblock_write_html(self, node):
    text = node.text
    svgstr = _get_svgstr(self.tmpdirname, text, 'displaymath')
    self.data += '<p>{}</p>'.format(svgstr)
    # self.data += '<p>\\[{}\\]</p>'.format(svgstr)

def role_write_html(self, node):
    text = node.value
    svgstr = _get_svgstr(self.tmpdirname, text, 'math')
    self.data += '<span>{}</span>'.format(svgstr)
    # self.data += '<span>\\({}\\)</span>'.format(svgstr)


def customblock_write_latex(self, node):
    text = node.text
    self.data += '\\begin{displaymath}\n'
    self.data += text + '\n'
    self.data += '\\end{displaymath}\n'

def role_write_latex(self, node):
    text = node.value
    self.data += '\\begin{math}\n'
    self.data += text + '\n'
    self.data += '\\end{math}\n'


def customblock_write_pdf(self, node):
    customblock_write_latex(self, node)

def role_write_pdf(self, node):
    role_write_latex(self, node)
