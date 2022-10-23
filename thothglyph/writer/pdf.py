from thothglyph.writer.latex import LatexWriter
import cairosvg
import importlib
import os
import subprocess
import tempfile

from thothglyph.node import logging

logger = logging.getLogger(__file__)


class PdfWriter(LatexWriter):
    target = 'pdf'
    ext = 'pdf'

    def __init__(self):
        super().__init__()
        self.tmpdirname = None

    def write(self, fpath, node):
        self.rootnode = node
        with tempfile.TemporaryDirectory() as tmpdirname:
            self.tmpdirname = tmpdirname
            self.parse(node)
            dirname, fname = os.path.split(fpath)
            fbname, fext = os.path.splitext(fpath)
            if dirname == '':
                dirname = '.'
            tex_fpath = os.path.join(tmpdirname, '{}.tex'.format(fbname))
            with open(tex_fpath, 'w') as f:
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

    def visit_customblock(self, node):
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

    def leave_customblock(self, node):
        pass

    def visit_role(self, node):
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

    def leave_role(self, node):
        pass

    def visit_imagerole(self, node):
        super().visit_imagerole(node)
        fname, ext = os.path.splitext(node.value)
        if ext == '.svg':
            imgpath = os.path.join(self.tmpdirname, node.value)
            cairosvg.svg2pdf(url=node.value, write_to='{}.pdf'.format(imgpath))
        else:
            pass

    def leave_imagerole(self, node):
        pass
