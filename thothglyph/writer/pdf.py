from __future__ import annotations
from typing import Optional
import importlib
import os
import shutil
import subprocess
import tempfile
from thothglyph.error import ThothglyphError
from thothglyph.util.svg import svg2pdf
from thothglyph.writer.latex import LatexWriter
from thothglyph.node import nd
from thothglyph.node import logging

logger = logging.getLogger(__file__)


class PdfWriter(LatexWriter):
    target = 'pdf'
    ext = 'pdf'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tmpdirname: Optional[str] = None

    def template_dir(self):
        if self.tmpdirname:
            return os.path.join(self.tmpdirname, 'template')
        return super().template_dir()

    def _copy_template(self, tmpdirname: str) -> None:
        commondir1 = os.path.join(self.pkg_template_dir(), 'common')
        commondir2 = os.path.join(self.template_dir(), 'common')
        newcommondir = os.path.join(tmpdirname, 'template', 'common')
        os.makedirs(newcommondir, exist_ok=True)
        shutil.copy(os.path.join(commondir1, 'check_en.pdf'), newcommondir)
        shutil.copy(os.path.join(commondir1, 'check_im.pdf'), newcommondir)
        shutil.copy(os.path.join(commondir1, 'check_dis.pdf'), newcommondir)
        if os.path.exists(commondir2):
            shutil.copytree(commondir2, newcommondir, dirs_exist_ok=True)

        latexdir1 = os.path.join(self.pkg_template_dir(), 'latex')
        latexdir2 = os.path.join(self.template_dir(), 'latex')
        newlatexdir = os.path.join(tmpdirname, 'template', 'latex')
        os.makedirs(newlatexdir, exist_ok=True)
        shutil.copytree(latexdir1, newlatexdir, dirs_exist_ok=True)
        if os.path.exists(latexdir2):
            shutil.copytree(latexdir2, newlatexdir, dirs_exist_ok=True)

    def write(self, fpath: str, node: nd.ASTNode):
        clsname = self.__class__.__name__
        logger.info('{}: write document'.format(clsname))
        self.rootnode = node
        with tempfile.TemporaryDirectory() as tmpdirname:
            self._copy_template(tmpdirname)
            self.tmpdirname = tmpdirname
            self.parse(node)
            dirname, fname = os.path.split(fpath)
            fbname, fext = os.path.splitext(fname)
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
            clsname = self.__class__.__name__
            steps = ('write main contents', 'insert toc pages', 'fix page numbers')
            try:
                for i, step in enumerate(steps, start=1):
                    logger.info('{}: {}. {}'.format(clsname, i, step))
                    p = subprocess.run(
                        latex_cmds, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                    )
                    if p.returncode != 0:
                        msg = 'lualatex command exit with code {}.'.format(p.returncode)
                        raise ThothglyphError(msg)
                mv_cmd = ['mv', '-f', '{}/{}.pdf'.format(tmpdirname, fbname), dirname]
                subprocess.run(mv_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as e:
                msg = '{} exit with code {}\n'.format(latex_cmds[0], e)
                msg += 'log: {}/{}.pdf.log'.format(dirname, fbname)
                logger.error(msg)
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
                if node.ext in self.exts:
                    extpath = 'thothglyph.ext.{}'.format(node.ext)
                    extmodule = importlib.import_module(extpath)
                    extmodule.customblock_write_pdf(self, node)
                else:
                    self.data += '\\begin{lstlisting}\n'
                    self.data += node.text + '\n'
                    self.data += '\\end{lstlisting}\n'
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
            imgpath = os.path.join(self.tmpdirname, '{}.pdf'.format(node.value))
            svg2pdf(url=node.value, write_to=imgpath)
        else:
            pass

    def leave_imagerole(self, node: nd.ASTNode) -> None:
        pass
