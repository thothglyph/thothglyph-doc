from __future__ import annotations
from typing import Optional
import importlib
import os
import subprocess
import tempfile
import cairosvg
from thothglyph.writer.latex import LatexWriter
from thothglyph.node import nd
from thothglyph.node import logging

logger = logging.getLogger(__file__)


class PdfWriter(LatexWriter):
    target = 'pdf'
    ext = 'pdf'

    def __init__(self):
        super().__init__()
        self.tmpdirname: Optional[str] = None

    def write(self, fpath: str, node: nd.ASTNode):
        self.rootnode = node
        with tempfile.TemporaryDirectory() as tmpdirname:
            self.tmpdirname = tmpdirname
            self.parse(node)
            dirname, fname = os.path.split(fpath)
            fbname, fext = os.path.splitext(fpath)
            if dirname == '':
                dirname = '.'
            tex_fpath = os.path.join(tmpdirname, '{}.tex'.format(fbname))
            with open(tex_fpath, 'w', encoding=self.encoding) as f:
                f.write(self.data)
            latex_cmds = [
                'lualatex',
                '-output-directory={}'.format(tmpdirname),
                '-halt-on-error',
                '-interaction=nonstopmode',
                '{}.tex'.format(fbname),
            ]
            rets = list()
            # lualatex fails to build hyperrefs at first. So the command is executed twice.
            p = subprocess.run(latex_cmds, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rets.append(p.returncode)
            p = subprocess.run(latex_cmds, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            rets.append(p.returncode)

            mv_cmd = ['mv', '-f', '{}/{}.pdf'.format(tmpdirname, fbname), dirname]
            subprocess.run(mv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if not all([r == 0 for r in rets]):
                mv_cmd = [
                    'mv', '-f',
                    '{}/{}.log'.format(tmpdirname, fbname),
                    '{}/{}.pdf.log'.format(dirname, fbname),
                ]
                subprocess.run(mv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.tmpdirname = None

    def visit_customblock(self, node: nd.ASTNode) -> None:
        if node.ext == '':
            self.data += '\\begin{lstlisting}\n'
            self.data += node.text + '\n'
            self.data += '\\end{lstlisting}\n'
        else:
            try:
                extpath = 'thothglyph.ext.{}'.format(node.ext)
                extmodule = importlib.import_module(extpath)
                extmodule.customblock_write_pdf(self, node)
            except Exception as e:
                logger.warning(e)
                self.data += '\\begin{lstlisting}\n'
                self.data += node.text + '\n'
                self.data += '\\end{lstlisting}\n'

    def leave_customblock(self, node: nd.ASTNode) -> None:
        pass

    def visit_role(self, node: nd.ASTNode) -> None:
        if node.role == '':
            self.data += '\\fbox{\\lstinline{'
            self.data += node.value
            self.data += '}}\n'
        else:
            try:
                extpath = 'thothglyph.ext.{}'.format(node.role)
                extmodule = importlib.import_module(extpath)
                extmodule.role_write_pdf(self, node)
            except Exception:
                self.data += '\\fbox{\\lstinline{'
                self.data += node.value
                self.data += '}}\n'

    def leave_role(self, node: nd.ASTNode) -> None:
        pass

    def visit_imagerole(self, node: nd.ASTNode) -> None:
        super().visit_imagerole(node)
        fname, ext = os.path.splitext(node.value)
        if ext == '.svg':
            assert self.tmpdirname
            imgpath = os.path.join(self.tmpdirname, node.value)
            cairosvg.svg2pdf(url=node.value, write_to='{}.pdf'.format(imgpath))
        else:
            pass

    def leave_imagerole(self, node: nd.ASTNode) -> None:
        pass
