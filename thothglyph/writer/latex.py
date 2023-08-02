# sudo apt install texlive-luatex texlive-fonts-recommended texlive-fonts-extra texlive-lang-cjk
from __future__ import annotations
from typing import Dict, Optional, Tuple, Union
import importlib
import os
import re
import tempfile
from PIL import Image
from thothglyph.error import ThothglyphError
from thothglyph.writer.writer import Writer
from thothglyph.node import nd
from thothglyph.node import logging

logger = logging.getLogger(__file__)


class LatexWriter(Writer):
    target = 'latex'
    ext = 'tex'

    sectlevel_cmds: Dict[str, Tuple[str, ...]] = {
        'article': ('section', 'subsection', 'paragraph', 'subparagraph'),
        'report': ('chapter', 'section', 'subsection', 'paragraph', 'subparagraph'),
        'book': ('chapter', 'section', 'subsection', 'paragraph', 'subparagraph'),
    }
    decoration_table: Dict[str, Tuple[str, str]] = {
        'EMPHASIS': ('\\textit{', '}'),
        'STRONG': ('\\textbf{', '}'),
        'MARKED': ('\\uline{', '}'),
        'STRIKE': ('\\sout{', '}'),
        'VAR': ('\\varbox{', '}'),
        'CODE': ('\\codebox{', '}'),
        'SUP': ('\\textsuperscript{', '}'),
        'SUB': ('\\textsubscript{', '}'),
    }
    code_decoration_table: Dict[str, Tuple[str, str]] = {
        'EMPHASIS': '<?tg:I?>',
        'STRONG': '<?tg:S?>',
        'MARKED': '<?tg:U?>',
        'STRIKE': '<?tg:SO?>',
        'VAR': '<?tg:VAR?>',
        'CODE': '',
        'SUP': '',
        'SUB': '',
    }
    bp_scale: float = 72.0 / 150.0

    def __init__(self):
        super().__init__()
        self.tmpdirname: Optional[str] = None
        self.contentphase: str = 'before'  # before, main, after

    def parse(self, node) -> None:
        super().parse(node)
        template_dir = self.template_dir()
        target = LatexWriter.target
        theme = self.theme()
        template_path = os.path.join(template_dir, target, theme, 'document-ja.tex')
        if not os.path.exists(template_path):
            raise ThothglyphError('template not found: {}'.format(template_path))
        with open(template_path, 'r', encoding=self.encoding) as f:
            template = f.read()
        t = template.replace('{', '{{').replace('}', '}}')
        t = re.sub(r'\$\{\{([^}]+)\}\}', r'{\1}', t)
        self.data = t.format(doc=self.template_docdata)

    def write(self, fpath: str, node: nd.ASTNode) -> None:
        clsname = self.__class__.__name__
        logger.info('{}: write document'.format(clsname))
        self.rootnode = node
        with tempfile.TemporaryDirectory() as tmpdirname:
            self.tmpdirname = tmpdirname
            self.parse(node)
            with open(fpath, 'w', encoding=self.encoding) as f:
                f.write(self.data)
        self.tmpdirname = None

    def visit_document(self, node: nd.ASTNode) -> None:
        self.data += '\\setcounter{page}{0}\n'
        self.data += '\\pagenumbering{arabic}\\pagestyle{beforecontents}\n'

    def visit_section(self, node: nd.ASTNode) -> None:
        level_offset = 0
        _id = node.id or node.title.replace(' ', '_')
        title = tex_escape(node.title)
        doctype = 'report'
        level = min(node.level - 1, len(self.sectlevel_cmds[doctype]) - 1) + level_offset
        cmd = self.sectlevel_cmds[doctype][level]
        asterisk = ''
        if node.opts.get('notoc') or node.opts.get('nonum'):
            asterisk = '*'
        if not node.opts.get('notoc') and node.level == 1 and self.contentphase == 'before':
            self.data += '\\pagenumbering{arabic}\\pagestyle{fancy}\n'
            self.contentphase = 'main'
        self.data += '\\{}{}{{{}}}'.format(cmd, asterisk, title)
        if not node.opts.get('notoc') and node.opts.get('nonum'):
            self.data += '\\addcontentsline{{toc}}{{{}}}{{{}}}'.format(cmd, title)
        self.data += '\\label{{{}}}\n'.format(_id)

    def leave_section(self, node: nd.ASTNode) -> None:
        pass

    def visit_tocblock(self, node: nd.ASTNode) -> None:
        self.data += '\\tableofcontents\n'

    def leave_tocblock(self, node: nd.ASTNode) -> None:
        self.data += '\\clearpage\\setcounter{page}{0}\n'

    def visit_bulletlistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\begin{itemize}\n'

    def leave_bulletlistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\end{itemize}\n'

    def visit_orderedlistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\begin{enumerate}\n'

    def leave_orderedlistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\end{enumerate}\n'

    def visit_descriptionlistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\begin{description}\n'

    def leave_descriptionlistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\end{description}\n'

    def visit_checklistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\begin{tgchecklist}\n'

    def leave_checklistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\end{tgchecklist}\n'

    def visit_footnotelistblock(self, node: nd.ASTNode) -> None:
        self._continue()

    def leave_footnotelistblock(self, node: nd.ASTNode) -> None:
        pass

    def visit_referencelistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\begin{thebibliography}{{99}}\n'

    def leave_referencelistblock(self, node: nd.ASTNode) -> None:
        self.data += '\\end{thebibliography}\n'

    def visit_listitem(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent, nd.DescriptionListBlockNode):
            pass
        elif isinstance(node.parent, nd.CheckListBlockNode):
            if node.marker == 'x':
                self.data += '\\item[{\\tgcheck[en]}] '
            elif node.marker == '-':
                self.data += '\\item[{\\tgcheck[im]}] '
            else:
                self.data += '\\item[{\\tgcheck[dis]}] '
        elif isinstance(node.parent, nd.FootnoteListBlockNode):
            pass  # unreach
        elif isinstance(node.parent, nd.ReferenceListBlockNode):
            url = 'ref.{}'.format(node.ref_num)
            self.data += '\\bibitem{{{}}} '.format(url)
        else:
            self.data += '\\item '

    def leave_listitem(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent, nd.FootnoteListBlockNode):
            pass  # unreach
        elif isinstance(node.parent, nd.ReferenceListBlockNode):
            self.data += '\n'

    def visit_quoteblock(self, node: nd.ASTNode) -> None:
        self.data += '\\begin{quote}\n'

    def leave_quoteblock(self, node: nd.ASTNode) -> None:
        self.data += '\\end{quote}\n'

    def visit_codeblock(self, node: nd.ASTNode) -> None:
        self.data += '\\begin{lstlisting}'
        if node.lang:
            self.data += '[style={}]'.format(node.lang)
        self.data += '\n'

    def leave_codeblock(self, node: nd.ASTNode) -> None:
        self.data += '\\end{lstlisting}\n'

    def visit_figureblock(self, node: nd.ASTNode) -> None:
        align = node.align
        table_align_cmd = {
            'l': 'raggedright',
            'c': 'centering',
            'r': 'raggedleft',
        }
        self.data += '\\begin{figure}[H]\n'
        self.data += '\\{}\n'.format(table_align_cmd[align])
        opts = 'singlelinecheck=false,justification={}'
        opts = opts.format(table_align_cmd[align])
        self.data += '\\captionsetup{{{}}}\n'.format(opts)
        if isinstance(node.children[0], nd.TableBlockNode):
            self.data += '\\captionof{{table}}{{{}}}\n'.format(node.caption)
        else:
            self.data += '\\captionof{{figure}}{{{}}}\n'.format(node.caption)

    def leave_figureblock(self, node: nd.ASTNode) -> None:
        self.data += '\\end{figure}\n'

    style_gridtable = True

    def visit_tableblock(self, node: nd.ASTNode) -> None:
        align = node.align
        if isinstance(node.parent, nd.FigureBlockNode):
            align = node.parent.align
        table_align_cmd = {
            'l': 'raggedright',
            'c': 'centering',
            'r': 'raggedleft',
        }
        aligns = node.aligns[:]
        for i, a in enumerate(aligns):
            if a == 'x':
                aligns[i] = 'X[l]'
            else:
                aligns[i] = a
        if self.style_gridtable:
            col_aligns = '|{}|'.format('|'.join(aligns))
        else:
            col_aligns = '{}'.format(' '.join(aligns))
        if not node._parent_table():
            self.data += '\\{}'.format(table_align_cmd[align])
            if node.type == 'long':
                self.data += '\\begin{longtblr}\n'
            # elif isinstance(node.parent, nd.FigureBlockNode):
            #     self.data += '\\begin{talltblr}\n'
            else:
                self.data += '\\begin{tblr}\n'
            self.data += '['
            self.data += 'entry=none, label=none,'
            self.data += ']\n'
        else:
            self.data += '\\begin{tblr}\n'
        self.data += '{'
        self.data += 'colspec = {{{}}}, '.format(col_aligns)
        self.data += 'hlines, vlines, '
        self.data += 'measure = vbox, '
        self.data += '}\n'

    def leave_tableblock(self, node: nd.ASTNode) -> None:
        if not node._parent_table():
            if node.type == 'long':
                self.data += '\\end{longtblr}\n\n'
            # elif isinstance(node.parent, nd.FigureBlockNode):
            #     self.data += '\\end{talltblr}\n\n'
            else:
                self.data += '\\end{tblr}\n\n'
        else:
            self.data += '\\end{tblr}\n\n'

        fns = list()
        for n, gofoward in node.walk_depth():
            if not gofoward:
                continue
            if isinstance(n, nd.FootnoteNode):
                fns.append(n)
        for i, fn in enumerate(fns):
            self.data += '\\footnotetext[{}]{{\n'.format(fn.fn_num)
            for n in fn.description.children:
                Writer.parse(self, n)
            self.data += '}\n'

    def visit_tablerow(self, node: nd.ASTNode) -> None:
        if node.idx > 0:
            self.data += ' \\\\\n'
        # if node.tp == 'header':
        #     self.data += '\\tgthrowcolor\n'
        # else:
        #     self.data += '\\tgtdrowcolor\n'

    def leave_tablerow(self, node: nd.ASTNode) -> None:
        if node.idx == len(node.parent.children) - 1:
            self.data += ' \\\\\n'

    def visit_tablecell(self, node: nd.ASTNode) -> None:
        if self.style_gridtable:
            align = '{}|'.format(node.align)
        else:
            align = '{}'.format(node.align)
        if node.mergeto is None:
            if node.idx != 0:
                self.data += ' & '
            s = node.size
            if s.x > 1:
                self.data += '\\multicolumn{{{}}}{{{}}}{{'.format(s.x, align)
            if s.y > 1:
                self.data += '\\multirow{{{}}}{{*}}{{'.format(s.y)
            self.data += '\n{\\begin{varwidth}{\\linewidth}\n'
        elif node.mergeto.idx == node.idx and node.mergeto.parent.idx != node.parent.idx:
            # horizontal cell merging
            if node.idx != 0:
                self.data += ' & '
            s = node.mergeto.size
            if s.x > 1:
                self.data += '\\multicolumn{{{}}}{{{}}}{{'.format(s.x, align)
        else:
            # vertical cell merging
            pass

    def leave_tablecell(self, node: nd.ASTNode) -> None:
        if node.mergeto is None:
            self.data += '\n\\end{varwidth}}\n'
            s = node.size
            if s.x > 1:
                self.data += '}'
            if s.y > 1:
                self.data += '}'
        elif node.mergeto.idx == node.idx and node.mergeto.parent.idx != node.parent.idx:
            s = node.mergeto.size
            if s.x > 1:
                self.data += '}'

    def visit_customblock(self, node: nd.ASTNode) -> None:
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

    def leave_customblock(self, node: nd.ASTNode) -> None:
        pass

    def visit_paragraph(self, node: nd.ASTNode) -> None:
        pass

    def leave_paragraph(self, node: nd.ASTNode) -> None:
        self.data += '\n\n'

    def visit_title(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent, nd.ListItemNode):
            self.data += '\\item[\\desctitle{'

    def leave_title(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent, nd.ListItemNode):
            self.data += '}] '
            if node.parent.titlebreak:
                self.data += '\\mbox{}\\\\ '

    def visit_decorationrole(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent_block, nd.CodeBlockNode):
            self.data += self.code_decoration_table[node.role]
        else:
            self.data += self.decoration_table[node.role][0]

    def leave_decorationrole(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent_block, nd.CodeBlockNode):
            self.data += self.code_decoration_table[node.role]
        else:
            self.data += self.decoration_table[node.role][1]

    def visit_role(self, node: nd.ASTNode) -> None:
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

    def leave_role(self, node: nd.ASTNode) -> None:
        pass

    def visit_imagerole(self, node: nd.ASTNode) -> None:
        fname, ext = os.path.splitext(node.value)
        if ext == '.svg':
            assert self.tmpdirname
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

    def leave_imagerole(self, node: nd.ASTNode) -> None:
        pass

    def visit_kbdrole(self, node: nd.ASTNode) -> None:
        value = ['\\kbdbox{{{}}}'.format(v) for v in node.value]
        valuestr = ' {\\scriptsize+} '.join(value)
        self.data += valuestr

    def leave_kbdrole(self, node: nd.ASTNode) -> None:
        pass

    def visit_btnrole(self, node: nd.ASTNode) -> None:
        value = '\\btnbox{{{}}}'.format(node.value)
        self.data += value

    def leave_btnrole(self, node: nd.ASTNode) -> None:
        pass

    def visit_menurole(self, node: nd.ASTNode) -> None:
        value = ['\\menubox{{{}}}'.format(v) for v in node.value]
        valuestr = ' {\\tiny>} '.join(value)
        self.data += valuestr

    def leave_menurole(self, node: nd.ASTNode) -> None:
        pass

    def visit_link(self, node: nd.ASTNode) -> None:
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

    def leave_link(self, node: nd.ASTNode) -> None:
        pass

    def visit_footnote(self, node: nd.ASTNode) -> None:
        table = node._parent_table()
        if table:
            self.data += ' \\footnotemark[{}] '.format(node.fn_num)
        else:
            url = node.fn_num
            self.data += '\\footnote[{}]{{'.format(url)
            for n in node.description.children:
                Writer.parse(self, n)
            self.data += '}'

    def leave_footnote(self, node: nd.ASTNode) -> None:
        pass

    def visit_reference(self, node: nd.ASTNode) -> None:
        url = 'ref.{}'.format(node.ref_num)
        self.data += '\\cite{{{}}}'.format(url)

    def leave_reference(self, node: nd.ASTNode) -> None:
        pass

    def visit_text(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent_block, nd.CodeBlockNode):
            text = node.text
            for key, delim in self.code_decoration_table.items():
                text = text.replace(key, delim)
            self.data += text
        else:
            text = tex_escape(node.text)
            self.data += text

    def leave_text(self, node: nd.ASTNode) -> None:
        pass

    def visit_other(self, node: nd.ASTNode) -> None:
        pass

    def leave_other(self, node: nd.ASTNode) -> None:
        pass


def tex_escape(text: str) -> str:
    text = text.replace('\\', '\\textbackslash ')
    text = re.sub(r'([#%&{}$_])', r'\\\1', text)
    trans: Dict[str, Union[int, str, None]] = {
        '~': '{\\textasciitilde}',
        '^': '{\\textasciicircum}',
        '|': '{\\textbar}',
        '<': '{\\textless}',
        '>': '{\\textgreater}',
        '-': '{\\phantom{}}-',
    }
    text = text.translate(str.maketrans(trans))
    return text
