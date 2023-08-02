from __future__ import annotations
from typing import Dict, List, Optional
import html
import importlib
import os
import re
import shutil
import tempfile
from thothglyph.error import ThothglyphError
from thothglyph.writer.writer import Writer
from thothglyph.node import nd
from thothglyph.node import logging

logger = logging.getLogger(__file__)


class HtmlWriter(Writer):
    target = 'html'
    ext = 'html'

    decoration_table: Dict[str, str] = {
        'EMPHASIS': 'em',
        'STRONG': 'strong',
        'MARKED': 'u',
        'STRIKE': 's',
        'VAR': 'var',
        'CODE': 'code',
        'SUP': 'sup',
        'SUB': 'sub',
    }

    def __init__(self):
        super().__init__()
        self.tmpdirname: Optional[str] = None
        self.imgdirname: str = 'img'

    def parse(self, node: nd.ASTNode) -> None:
        super().parse(node)
        template_dir = self.template_dir()
        target = self.target
        theme = self.theme()
        template_path = os.path.join(template_dir, target, theme, 'index.html')
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
            self._copy_template(fpath)
            self._copy_resources(fpath)
            fdir = os.path.abspath(fpath + '.dir')
            indexpath = os.path.join(self.tmpdirname, 'index.html')
            with open(indexpath, 'w', encoding=self.encoding) as f:
                f.write(self.data)
            os.makedirs(fdir, exist_ok=True)
            shutil.copytree(self.tmpdirname, fdir, dirs_exist_ok=True)
        self.tmpdirname = None

    def _copy_template(self, fpath: str) -> None:
        commondir = os.path.join(self.template_dir(), 'common')
        newcommondir = os.path.join(self.tmpdirname, 'template', 'common')
        shutil.copytree(commondir, newcommondir, dirs_exist_ok=True)

    def _copy_resources(self, fpath: str) -> None:
        rscs: Dict[str, List[str]] = dict()
        typetable: Dict[str, Dict[str, str]] = {
            'img': {
                'dir': os.path.join(self.tmpdirname, self.imgdirname),
            },
        }
        for n, gofoward in self.rootnode.walk_depth():
            if not gofoward:
                continue
            if isinstance(n, nd.ImageRoleNode):
                tp = 'img'
                path = os.path.abspath(n.value)
            else:
                continue
            rscs.setdefault(tp, list())
            if path not in rscs[tp]:
                rscs[tp].append(path)
        for tp, paths in rscs.items():
            newrscdir = typetable[tp]['dir']
            os.makedirs(newrscdir, exist_ok=True)
            for rscpath in paths:
                _, rscfname = os.path.split(rscpath)
                shutil.copy2(rscpath, os.path.join(newrscdir, rscfname))

    def visit_section(self, node: nd.ASTNode) -> None:
        self.data += '<section>'
        _id = node.id or node.title.replace(' ', '_')
        if node.opts.get('nonum'):
            title = node.title
        else:
            title = '{}. {}'.format(node.sectnum, node.title)
        if node.opts.get('notoc'):
            toc = 'class="notoc"'
        else:
            toc = ''
        if node.level < 7:
            tag = '<h{0} {3} id="{2}">{1}</h{0}>\n'
            self.data += tag.format(node.level, title, _id, toc)
        else:
            tag = '<div class="section h{0}" id="{2}">{1}</div>\n'
            self.data += tag.format(node.level, title, _id)

    def leave_section(self, node: nd.ASTNode) -> None:
        self.data += '</section>\n'

    def visit_tocblock(self, node: nd.ASTNode) -> None:
        self.data += '<div>\n'
        maxlevel = int(node.opts.get('level', '100'))
        for n, gofoward in node.walk_sections():
            if n.opts.get('notoc'):
                continue
            if gofoward and n.level <= maxlevel:
                bros = [s for s in n.parent.children if isinstance(n, nd.SectionNode)]
                if bros.index(n) == 0:
                    self.data += '<ul>\n'
                if n.opts.get('nonum'):
                    title = '{}'.format(n.title)
                else:
                    title = '{}. {}'.format(n.sectnum, n.title)
                _id = n.id or n.title.replace(' ', '_')
                self.data += '<li><a href="#{}">{}</a></li>\n'.format(_id, title)
                if bros.index(n) == len(bros) - 1:
                    self.data += '</ul>\n'
        self.data += '</div>\n'

    def leave_tocblock(self, node: nd.ASTNode) -> None:
        pass

    def visit_bulletlistblock(self, node: nd.ASTNode) -> None:
        self.data += '<ul>\n'

    def leave_bulletlistblock(self, node: nd.ASTNode) -> None:
        self.data += '</ul>\n'

    def visit_orderedlistblock(self, node: nd.ASTNode) -> None:
        self.data += '<ol>\n'

    def leave_orderedlistblock(self, node: nd.ASTNode) -> None:
        self.data += '</ol>\n'

    def visit_descriptionlistblock(self, node: nd.ASTNode) -> None:
        if not node.titlebreak:
            self.data += '<dl class="compactdl">\n'
        else:
            self.data += '<dl>\n'

    def leave_descriptionlistblock(self, node: nd.ASTNode) -> None:
        self.data += '</dl>\n'

    def visit_checklistblock(self, node: nd.ASTNode) -> None:
        self.data += '<ul class="checklist">\n'

    def leave_checklistblock(self, node: nd.ASTNode) -> None:
        self.data += '</ul>\n'

    def visit_footnotelistblock(self, node: nd.ASTNode) -> None:
        self.data += '<ul class="footnotelist">'

    def leave_footnotelistblock(self, node: nd.ASTNode) -> None:
        self.data += '</ul>'

    def visit_referencelistblock(self, node: nd.ASTNode) -> None:
        self.data += '<ul class="referencelist">'

    def leave_referencelistblock(self, node: nd.ASTNode) -> None:
        self.data += '</ul>'

    def visit_listitem(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent, nd.DescriptionListBlockNode):
            pass
        elif isinstance(node.parent, nd.CheckListBlockNode):
            if node.marker == 'x':
                liclass = 'check_en'
            elif node.marker == '-':
                liclass = 'check_im'
            else:
                liclass = 'check_dis'
            self.data += '<li class="checklist {}">'.format(liclass)
        elif isinstance(node.parent, nd.FootnoteListBlockNode):
            url = 'fn.{}-{}'.format(node.treeindex()[1], node.fn_num)
            text = node.fn_num  # node.title
            self.data += '<li> '
            self.data += '<span id="{}">{}</span>. '.format(url, text)
        elif isinstance(node.parent, nd.ReferenceListBlockNode):
            url = 'ref.{}'.format(node.ref_num)
            text = node.ref_num  # node.title
            self.data += '<li> '
            self.data += '[<span id="{}">{}</span>] '.format(url, text)
            # self.data += '<li id="{}">[{}] '.format(url, text)
        else:
            self.data += '<li>'

    def leave_listitem(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent, nd.DescriptionListBlockNode):
            self.data += '</dd>\n'
            if not node.parent.titlebreak:
                self.data += '</div>'
        else:
            self.data += '</li>\n'

    def visit_quoteblock(self, node: nd.ASTNode) -> None:
        self.data += '<blockquote>'

    def leave_quoteblock(self, node: nd.ASTNode) -> None:
        self.data += '</blockquote>'

    def visit_codeblock(self, node: nd.ASTNode) -> None:
        self.data += '<pre><code>'

    def leave_codeblock(self, node: nd.ASTNode) -> None:
        self.data += '</code></pre>\n'

    def visit_figureblock(self, node: nd.ASTNode) -> None:
        if node.align == 'l':
            style = 'style="text-align:left;"'
        elif node.align == 'c':
            style = 'style="text-align:center;"'
        elif node.align == 'r':
            style = 'style="text-align:right;"'
        if isinstance(node.children[0], nd.TableBlockNode):
            self.data += '<figure {}>\n'.format(style)
            self.data += '<figcaption>'
            self.data += '{} {}'.format(node.fignum, node.caption)
            self.data += '</figcaption>\n'
        else:
            self.data += '<figure {}>\n'.format(style)

    def leave_figureblock(self, node: nd.ASTNode) -> None:
        if isinstance(node.children[0], nd.TableBlockNode):
            self.data += '</figure>\n'
        else:
            self.data += '<figcaption>'
            self.data += '{} {}'.format(node.fignum, node.caption)
            self.data += '</figcaption>\n'
            self.data += '</figure>\n'

    def visit_tableblock(self, node: nd.ASTNode) -> None:
        align = node.align
        if isinstance(node.parent, nd.FigureBlockNode):
            align = node.parent.align
        if align == 'l':
            style = 'style="margin-right:auto;"'
        elif align == 'c':
            style = 'style="margin-left:auto;margin-right:auto;"'
        elif align == 'r':
            style = 'style="margin-left:auto;"'
        self.data += '<table {}>\n'.format(style)

    def leave_tableblock(self, node: nd.ASTNode) -> None:
        self.data += '</table>\n'

    def visit_tablerow(self, node: nd.ASTNode) -> None:
        self.data += '<tr>\n'

    def leave_tablerow(self, node: nd.ASTNode) -> None:
        self.data += '</tr>\n'

    def visit_tablecell(self, node: nd.ASTNode) -> None:
        tagname = 'td'
        if node.parent.tp == 'header':
            tagname = 'th'
        if node.mergeto is None:
            s = node.size
            align = {'l': 'left', 'c': 'center', 'r': 'right', 'x': 'left'}
            attrs = ['style="text-align:{}"'.format(align[node.align])]
            attrs += ['colspan="{}"'.format(s.x), 'rowspan="{}"'.format(s.y)]
            self.data += '<{} {}>'.format(tagname, ' '.join(attrs))
        else:
            self._continue()

    def leave_tablecell(self, node: nd.ASTNode) -> None:
        tagname = 'td'
        if node.parent.tp == 'header':
            tagname = 'th'
        if node.mergeto is None:
            self.data += '</{}>'.format(tagname)
        else:
            pass

    def visit_customblock(self, node: nd.ASTNode) -> None:
        if node.ext == '':
            self.data += '<pre><code>'
            self.data += html.escape(node.text) + '\n'
            self.data += '</code></pre>\n'
        else:
            try:
                extpath = 'thothglyph.ext.{}'.format(node.ext)
                extmodule = importlib.import_module(extpath)
                extmodule.customblock_write_html(self, node)
            except Exception:
                self.data += '<pre><code>'
                self.data += html.escape(node.text) + '\n'
                self.data += '</code></pre>\n'

    def leave_customblock(self, node: nd.ASTNode) -> None:
        pass

    def visit_horizonblock(self, node: nd.ASTNode) -> None:
        self.data += '<hr />'

    def leave_horizonblock(self, node: nd.ASTNode) -> None:
        pass

    def visit_paragraph(self, node: nd.ASTNode) -> None:
        if not all([
            isinstance(node.parent, nd.ListItemNode),
            len(node.parent.children) == 1
        ]):
            self.data += '<p>'

    def leave_paragraph(self, node: nd.ASTNode) -> None:
        if not all([
            isinstance(node.parent, nd.ListItemNode),
            len(node.parent.children) == 1
        ]):
            self.data += '</p>\n'

    def visit_title(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent, nd.ListItemNode):
            if not node.parent.parent.titlebreak:
                self.data += '<div>'
            self.data += '<dt>'

    def leave_title(self, node: nd.ASTNode) -> None:
        if isinstance(node.parent, nd.ListItemNode):
            self.data += '</dt><dd>'

    def visit_decorationrole(self, node: nd.ASTNode) -> None:
        self.data += '<{}>'.format(self.decoration_table[node.role])

    def leave_decorationrole(self, node: nd.ASTNode) -> None:
        self.data += '</{}>'.format(self.decoration_table[node.role])

    def visit_role(self, node: nd.ASTNode) -> None:
        if node.role == '':
            self.data += '<code>'
            self.data += html.escape(node.value)
            self.data += '</code>\n'
        else:
            try:
                extpath = 'thothglyph.ext.{}'.format(node.role)
                extmodule = importlib.import_module(extpath)
                extmodule.role_write_html(self, node)
            except Exception:
                self.data += '<code>'
                self.data += html.escape(node.value)
                self.data += '</code>\n'

    def leave_role(self, node: nd.ASTNode) -> None:
        pass

    def visit_imagerole(self, node: nd.ASTNode) -> None:
        options = dict()
        if 'w' in node.opts:
            options['width'] = node.opts['w']
        optstr = ' '.join(['{}="{}"'.format(k, v) for k, v in options.items()])
        fname = os.path.basename(node.value)
        _, ext = os.path.splitext(fname)
        imgpath = os.path.join(self.imgdirname, fname)
        if ext.lower() == '.svg':
            src = 'type="image/svg+xml" data="{}"'.format(imgpath)
            self.data += '<object {} {}></object>'.format(src, optstr)
        else:
            src = 'src="{}"'.format(imgpath)
            self.data += '<image {} {} />'.format(src, optstr)

    def leave_imagerole(self, node: nd.ASTNode) -> None:
        pass

    def visit_kbdrole(self, node: nd.ASTNode) -> None:
        texts = [html.escape(t) for t in node.value]
        value = ' + '.join(['<kbd>{}</kbd>'.format(v) for v in texts])
        self.data += value

    def leave_kbdrole(self, node: nd.ASTNode) -> None:
        pass

    def visit_btnrole(self, node: nd.ASTNode) -> None:
        value = '<kbd>{}</kbd>'.format(html.escape(node.value))
        self.data += value

    def leave_btnrole(self, node: nd.ASTNode) -> None:
        pass

    def visit_menurole(self, node: nd.ASTNode) -> None:
        texts = [html.escape(t) for t in node.value]
        value = ' > '.join(['<span class="menu">{}</span>'.format(v) for v in texts])
        self.data += value

    def leave_menurole(self, node: nd.ASTNode) -> None:
        pass

    def visit_link(self, node: nd.ASTNode) -> None:
        if '://' in node.value:
            blank = 'target=”_blank”'
            url = node.value
            text = node.opts[0] if node.opts[0] else node.value
        else:
            blank = ''
            url = '#' + node.target_id
            text = node.opts[0] if node.opts[0] else node.target_title
        text = html.escape(text)
        self.data += '<a href="{}" {}>{}</a>'.format(url, blank, text)

    def leave_link(self, node: nd.ASTNode) -> None:
        pass

    def visit_footnote(self, node: nd.ASTNode) -> None:
        url = '#fn.{}-{}'.format(node.treeindex()[1], node.fn_num)
        text = node.fn_num  # node.value
        self.data += '<sup><a href="{}">{}</a></sup>'.format(url, text)

    def leave_footnote(self, node: nd.ASTNode) -> None:
        pass

    def visit_reference(self, node: nd.ASTNode) -> None:
        url = '#ref.{}'.format(node.ref_num)
        text = node.ref_num  # node.value
        self.data += '[<a href="{}">{}</a>]'.format(url, text)

    def leave_reference(self, node: nd.ASTNode) -> None:
        pass

    def visit_text(self, node: nd.ASTNode) -> None:
        self.data += node.text

    def leave_text(self, node: nd.ASTNode) -> None:
        pass

    def visit_other(self, node: nd.ASTNode) -> None:
        pass

    def leave_other(self, node: nd.ASTNode) -> None:
        pass
