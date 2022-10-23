# sudo apt install texlive-luatex texlive-fonts-recommended texlive-fonts-extra texlive-lang-cjk
from thothglyph.writer.writer import Writer
from thothglyph.node import nd
import importlib
import os
import re
import tempfile
from PIL import Image

from thothglyph.node import logging

logger = logging.getLogger(__file__)


class LatexWriter(Writer):
    target = 'latex'
    ext = 'tex'

    sectlevel_cmds = {
        'article': ('section', 'subsection', 'paragraph', 'subparagraph'),
        'report': ('chapter', 'section', 'subsection', 'paragraph', 'subparagraph'),
        'book': ('chapter', 'section', 'subsection', 'paragraph', 'subparagraph'),
    }
    decoration_table = {
        'EMPHASIS': ('\\textit{', '}'),
        'STRONG': ('\\textbf{', '}'),
        'MARKED': ('\\uline{', '}'),
        'STRIKE': ('\\sout{', '}'),
        'VAR': ('\\varbox{', '}'),
        'CODE': ('\\codebox{', '}'),
        'SUP': ('\\textsuperscript{', '}'),
        'SUB': ('\\textsubscript{', '}'),
    }
    bp_scale = 72.0 / 150.0

    def __init__(self):
        super().__init__()
        self.tmpdirname = None

    def parse(self, node):
        super().parse(node)
        template_dir = self.template_dir(target=LatexWriter.target)
        template_path = os.path.join(template_dir, LatexWriter.target, 'document-ja.tex')
        if not os.path.exists(template_path):
            raise Exception('template not found: {}'.format(template_path))
        with open(template_path, 'r') as f:
            template = f.read()
        t = template.replace('{', '{{').replace('}', '}}')
        t = re.sub(r'\$\{\{([^}]+)\}\}', r'{\1}', t)
        self.data = t.format(doc=self.template_docdata)

    def write(self, fpath, node):
        self.rootnode = node
        with tempfile.TemporaryDirectory() as tmpdirname:
            self.tmpdirname = tmpdirname
            self.parse(node)
            with open(fpath, 'w') as f:
                f.write(self.data)
        self.tmpdirname = None

    def visit_section(self, node):
        level_offset = 0
        _id = node.id or node.title.replace(' ', '_')
        title = tex_escape(node.title)
        doctype = 'report'
        level = min(node.level - 1, len(self.sectlevel_cmds[doctype]) - 1) + level_offset
        cmd = self.sectlevel_cmds[doctype][level]
        if node.opts['nonum']:
            cmd += '*'
        self.data += '\\{}{{{}}}'.format(cmd, title)
        self.data += '\\label{{{}}}\n'.format(_id)

    def leave_section(self, node):
        pass

    def visit_tocblock(self, node):
        self.data += '\\tableofcontents\n'

    def leave_tocblock(self, node):
        pass

    def visit_bulletlistblock(self, node):
        self.data += '\\begin{itemize}\n'

    def leave_bulletlistblock(self, node):
        self.data += '\\end{itemize}\n'

    def visit_orderedlistblock(self, node):
        self.data += '\\begin{enumerate}\n'

    def leave_orderedlistblock(self, node):
        self.data += '\\end{enumerate}\n'

    def visit_descriptionlistblock(self, node):
        self.data += '\\begin{description}\n'

    def leave_descriptionlistblock(self, node):
        self.data += '\\end{description}\n'

    def visit_checklistblock(self, node):
        self.data += '\\begin{tgchecklist}\n'

    def leave_checklistblock(self, node):
        self.data += '\\end{tgchecklist}\n'

    def visit_footnotelistblock(self, node):
        self._continue()

    def leave_footnotelistblock(self, node):
        pass

    def visit_referencelistblock(self, node):
        self.data += '\\begin{thebibliography}{{99}}\n'

    def leave_referencelistblock(self, node):
        self.data += '\\end{thebibliography}\n'

    def visit_listitem(self, node):
        if isinstance(node.parent, nd.DescriptionListBlockNode):
            text = tex_escape(node.term)
            self.data += '\\item[{}] '.format(text)
        elif isinstance(node.parent, nd.CheckListBlockNode):
            if node.term == 'x':
                self.data += '\\item[{\\tgcheck[en]}] '
            elif node.term == '-':
                self.data += '\\item[{\\tgcheck[im]}] '
            else:
                self.data += '\\item[{\\tgcheck[dis]}] '
        elif isinstance(node.parent, nd.ReferenceListBlockNode):
            url = 'ref.{}'.format(node.ref_num)
            self.data += '\\bibitem{{{}}} '.format(url)
        else:
            self.data += '\\item '

    def leave_listitem(self, node):
        if isinstance(node.parent, nd.FootnoteListBlockNode):
            self.data += '\n'
        elif isinstance(node.parent, nd.ReferenceListBlockNode):
            self.data += '\n'

    def visit_quoteblock(self, node):
        self.data += '\\begin{quote}\n'

    def leave_quoteblock(self, node):
        self.data += '\\end{quote}\n'

    def visit_codeblock(self, node):
        self.data += '\\begin{lstlisting}\n'
        self.data += node.text + '\n'
        self.data += '\\end{lstlisting}\n'

    def leave_codeblock(self, node):
        pass

    def visit_figureblock(self, node):
        align = node.align
        table_align_cmd = {
            'l': 'raggedright',
            'c': 'centering',
            'r': 'raggedleft',
        }
        if not isinstance(node.children[0], nd.TableBlockNode):
            self.data += '\\begin{figure}[H]\n'
            self.data += '\\{}\n'.format(table_align_cmd[align])
            opts = 'singlelinecheck=false,justification={}'
            opts = opts.format(table_align_cmd[align])
            self.data += '\\captionsetup{{{}}}\n'.format(opts)
            self.data += '\\caption{{{}}}\n'.format(node.caption)

    def leave_figureblock(self, node):
        if not isinstance(node.children[0], nd.TableBlockNode):
            self.data += '\\end{figure}\n'

    style_gridtable = True

    def visit_tableblock(self, node):
        align = node.align
        if isinstance(node.parent, nd.FigureBlockNode):
            align = node.parent.align
        table_align_cmd = {
            'l': 'raggedright',
            'c': 'centering',
            'r': 'raggedleft',
        }
        if self.style_gridtable:
            col_aligns = '|{}|'.format('|'.join(node.aligns))
        else:
            col_aligns = '{}'.format(' '.join(node.aligns))
        self.data += '\\begin{table}[H]\n'
        self.data += '\\{}\n'.format(table_align_cmd[align])
        self.data += '\\begin{threeparttable}\n'
        if isinstance(node.parent, nd.FigureBlockNode):
            opts = 'singlelinecheck=false,justification={}'
            opts = opts.format(table_align_cmd[align])
            self.data += '\\captionsetup{{{}}}\n'.format(opts)
            self.data += '\\caption{{{}}}\n'.format(node.parent.caption)
        self.data += '\\begin{tabular}'
        self.data += '{{{}}}\n'.format(col_aligns.upper())
        self.data += '\\hline\n'

    def leave_tableblock(self, node):
        self.data += '\\hline\n'
        self.data += '\\end{tabular}\n'
        self.data += '\\end{threeparttable}\n'
        self.data += '\\end{table}\n'

    def visit_tablerow(self, node):
        if node.idx > 0:
            row = node
            cline_cols = list()
            for i in range(len(row.children)):
                cell = row.children[i]
                if cell.mergeto and cell.mergeto.parent.idx < cell.parent.idx:
                    pass
                else:
                    cline_cols.append(i + 1)
            clines = ''.join(['\\cline{{{}-{}}}'.format(c, c) for c in cline_cols])
            self.data += ' \\\\\n'
            self.data += clines + '\n'
        if node.tp == 'header':
            self.data += '\\tgthrowcolor\n'
        else:
            self.data += '\\tgtdrowcolor\n'

    def leave_tablerow(self, node):
        if node.idx == len(node.parent.children) - 1:
            self.data += ' \\\\\n'

    def visit_tablecell(self, node):
        if self.style_gridtable:
            align = '{}|'.format(node.align)
        else:
            align = '{}'.format(node.align)
        if len(node.children) == 1 and isinstance(node.children[0], nd.TextNode):
            if node.idx != 0:
                if node.mergeto is None:
                    self.data += ' & '
                    s = node.size
                    if s.x > 1:
                        self.data += '\\multicolumn{{{}}}{{{}}}{{'.format(s.x, align)
                    if s.y > 1:
                        self.data += '\\multirow{{{}}}{{*}}{{'.format(s.y)
                elif node.mergeto.idx == node.idx and node.mergeto.parent.idx != node.parent.idx:
                    self.data += ' & '
                    s = node.mergeto.size
                    if s.x > 1:
                        self.data += '\\multicolumn{{{}}}{{{}}}{{'.format(s.x, align)
        else:
            if node.idx != 0:
                self.data += ' & '
            self.data += '\\measureremainder{\\whatsleft}'
            self.data += '\n\\begin{varwidth}{\\whatsleft}\n'

    def leave_tablecell(self, node):
        if len(node.children) == 1 and isinstance(node.children[0], nd.TextNode):
            if node.idx != 0:
                if node.mergeto is None:
                    s = node.size
                    if s.x > 1:
                        self.data += '}'
                    if s.y > 1:
                        self.data += '}'
                elif node.mergeto.idx == node.idx and node.mergeto.parent.idx != node.parent.idx:
                    s = node.mergeto.size
                    if s.x > 1:
                        self.data += '}'
        else:
            self.data += '\n\\end{varwidth}\n'

    def visit_customblock(self, node):
        if node.ext == '':
            self.data += '\\begin{lstlisting}\n'
            self.data += node.text + '\n'
            self.data += '\\end{lstlisting}\n'
        else:
            try:
                extpath = 'thothglyph.ext.{}'.format(node.ext)
                extmodule = importlib.import_module(extpath)
                extmodule.customblock_write_latex(self, node)
            except Exception:
                self.data += '\\begin{lstlisting}\n'
                self.data += node.text + '\n'
                self.data += '\\end{lstlisting}\n'

    def leave_customblock(self, node):
        pass

    def visit_paragraph(self, node):
        pass

    def leave_paragraph(self, node):
        self.data += '\n\n'

    def visit_decorationrole(self, node):
        self.data += self.decoration_table[node.role][0]

    def leave_decorationrole(self, node):
        self.data += self.decoration_table[node.role][1]

    def visit_role(self, node):
        if node.role == '':
            self.data += '\\fbox{\\lstinline{'
            self.data += node.value
            self.data += '}}\n'
        else:
            try:
                extpath = 'thothglyph.ext.{}'.format(node.role)
                extmodule = importlib.import_module(extpath)
                extmodule.role_write_latex(self, node)
            except Exception:
                self.data += '\\fbox{\\lstinline{'
                self.data += node.value
                self.data += '}}\n'

    def leave_role(self, node):
        pass

    def visit_imagerole(self, node):
        fname, ext = os.path.splitext(node.value)
        if ext == '.svg':
            imgpath = os.path.join(self.tmpdirname, node.value)
            inc_imgpath = '{}.pdf'.format(imgpath)
        else:
            imgpath = node.value
            inc_imgpath = imgpath
        if 'w' in node.opts:
            w = node.opts['w']
            if w.endswith('px'):
                w = '{}bp'.format(int(float(w[0:-2]) * self.bp_scale))
            elif w.endswith('%'):
                w = '{}\\linewidth'.format(float(w[0:-1]) * 0.01)
        else:
            try:
                with Image.open(node.value) as img:
                    w = '{}bp'.format(img.width)
            except Exception:
                w = '\\linewidth'
        self.data += '\\tgincludegraphics[{}]{{{}}}'.format(w, inc_imgpath)

    def leave_imagerole(self, node):
        pass

    def visit_kbdrole(self, node):
        value = ['\\kbdbox{{{}}}'.format(v) for v in node.value]
        value = ' {\\scriptsize+} '.join(value)
        self.data += value

    def leave_kbdrole(self, node):
        pass

    def visit_btnrole(self, node):
        value = '\\btnbox{{{}}}'.format(node.value)
        self.data += value

    def leave_btnrole(self, node):
        pass

    def visit_menurole(self, node):
        value = ['\\menubox{{{}}}'.format(v) for v in node.value]
        value = ' {\\tiny>} '.join(value)
        self.data += value

    def leave_menurole(self, node):
        pass

    def visit_link(self, node):
        if '://' in node.value:
            url = node.value
            text = node.opts[0] if node.opts[0] else node.value
            text = tex_escape(text)
            self.data += '\\href{{{}}}{{{}}}'.format(url, text)
        else:
            url = node.target_id or node.value.replace(' ', '_')
            text = node.opts[0] if node.opts[0] else node.target_title
            text = tex_escape(text)
            self.data += '\\nameref{{{}}}'.format(url)

    def leave_link(self, node):
        pass

    def visit_footnote(self, node):
        url = node.fn_num
        self.data += '\\footnote[{}]{{'.format(url)
        for n in node.description.children:
            Writer.parse(self, n)
        self.data += '}'

    def leave_footnote(self, node):
        pass

    def visit_reference(self, node):
        url = 'ref.{}'.format(node.ref_num)
        self.data += '\\cite{{{}}}'.format(url)

    def leave_reference(self, node):
        pass

    def visit_text(self, node):
        text = node.text
        # if not(isinstance(node.parent, nd.RoleNode) and node.parent.role == 'CODE'):
        #     text = tex_escape(text)
        text = tex_escape(text)
        self.data += text

    def leave_text(self, node):
        pass

    def visit_other(self, node):
        pass

    def leave_other(self, node):
        pass


def tex_escape(text):
    text = text.replace('\\', '\\textbackslash ')
    text = re.sub(r'([#%&{}$_])', r'\\\1', text)
    text = text.translate(str.maketrans({
        '~': '{\\textasciitilde}',
        '^': '{\\textasciicircum}',
        '|': '{\\textbar}',
        '<': '{\\textless}',
        '>': '{\\textgreater}',
    }))
    return text
