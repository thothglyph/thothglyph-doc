from __future__ import annotations
from typing import Optional
import copy
import html
import os
import re
import shutil
import tempfile

from thothglyph.error import ThothglyphError
from thothglyph.writer.html import HtmlWriter
from thothglyph.writer.writer import TocData, Writer
from thothglyph.node import nd
from thothglyph.node import logging

logger = logging.getLogger(__file__)


class HtmlsWriter(HtmlWriter):
    target = 'htmls'
    ext = 'htmls'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tmpdirname: Optional[str] = None
        self.imgdirname: str = 'img'
        self.doc_sections = []
        self.datas = []

    def collect_toc_sections(self):
        for n, gofoward in self.rootnode.walk_depth():
            if not gofoward:
                continue
            if isinstance(n, nd.SectionNode) and n.level == 1:
                copy_section = copy.copy(n)
                self.doc_sections.append(copy_section)

    def modify_section_lv1_to_link(self):
        for n, gofoward in self.rootnode.walk_depth():
            if not gofoward:
                continue
            if isinstance(n, nd.SectionNode) and n.level == 1:
                parent = n.parent
                parent.children.remove(n)
                # paragraph = nd.ParagraphNode()
                # text = nd.TextNode()
                # if n.opts.get('nonum'):
                #     title = n.title
                # else:
                #     title = '{}. {}'.format(n.sectnum, n.title)
                # text.text = title
                # paragraph.add(text)
                # if not n.opts.get('notoc'):
                #     parent.add(paragraph)

    def create_toc(self, node):
        toc = []
        for n, gofoward in node.walk_depth():
            if gofoward:
                if not isinstance(n, nd.SectionNode):
                    continue
                new_toc = TocData()
                new_toc.level = n.level
                new_toc.text = n.title
                new_toc.node = n
                toc.append(new_toc)
        prev_level = -1
        toc_html = '<div>\n'
        for d in toc:
            if d.node.level < prev_level:
                for lv in range(prev_level - d.node.level):
                    toc_html += '</ul>\n'
            if d.node.level > prev_level:
                # toc_html += '<ul class="{}">\n'.format(f'toc-lv{d.node.level}')
                toc_html += '<ul>\n'
            sect = d.node
            sect_lv1 = d.node
            while sect_lv1.parent:
                if sect_lv1.level == 1:
                    break
                sect_lv1 = sect_lv1.parent
            fname = str(sect_lv1.src_id) + '_' + sect_lv1.sectnum
            url = fname + '.html'
            url = url + "#" + str(sect.src_id) + '_' + (sect.id or sect.auto_id)
            toc_html += '<a href="{}">'.format(url)
            if d.node.opts.get('nonum'):
                title = d.node.title
            else:
                title = '{}. {}'.format(d.node.sectnum, d.node.title)
            li_class = []
            li_class.append(f'toc-lv{d.node.level}')
            if d.node.opts.get('notoc'):
                li_class.append('toc-notoc')
            if len(li_class) > 0:
                toc_html += '<li class="{}">'.format(','.join(li_class))
            else:
                toc_html += '<li>'
            toc_html += '{}</li>'.format(title)
            toc_html += '</a>\n'
            prev_level = d.node.level
        if 0 < prev_level:
            for lv in range(prev_level - 0):
                toc_html += '</ul>\n'
        toc_html += '</div>'
        return toc_html

    def parse(self, node: nd.ASTNode) -> None:
        self.toc = self.create_toc(self.rootnode)
        self.collect_toc_sections()
        template_dir = self.template_dir()
        target = self.target
        # target = HtmlWriter.target
        # target = 'html'
        theme = self.theme()
        template_path = os.path.join(template_dir, target, theme, 'index.html')
        if not os.path.exists(template_path):
            raise ThothglyphError('template not found: {}'.format(template_path))
        with open(template_path, 'r', encoding=self.encoding) as f:
            template = f.read()

        for n in self.doc_sections:
            Writer.parse(self, n)
            t = template.replace('{', '{{').replace('}', '}}')
            t = re.sub(r'\$\{\{([^}]+)\}\}', r'{\1}', t)
            self.datas.append([n, t.format(doc=self.template_docdata)])
            self.data = ''

        self.modify_section_lv1_to_link()
        Writer.parse(self, self.rootnode)
        t = template.replace('{', '{{').replace('}', '}}')
        t = re.sub(r'\$\{\{([^}]+)\}\}', r'{\1}', t)
        self.datas.append([self.rootnode, t.format(doc=self.template_docdata)])
        self.data = ''

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
            node0, data0 = self.datas.pop()  # index.html
            for node, data in self.datas:
                fname = str(node.src_id) + '_' + node.sectnum
                section_doc_path = os.path.join(self.tmpdirname, f'{fname}.html')
                with open(section_doc_path, 'w', encoding=self.encoding) as f:
                    f.write(data)
            section_doc_path = os.path.join(self.tmpdirname, 'index.html')
            with open(section_doc_path, 'w', encoding=self.encoding) as f:
                f.write(data0)
            os.makedirs(fdir, exist_ok=True)
            shutil.copytree(self.tmpdirname, fdir, dirs_exist_ok=True)
        self.tmpdirname = None

    def visit_section(self, node: nd.ASTNode) -> None:
        if node.level == 1:
            self.data = ''
        super().visit_section(node)

    def leave_section(self, node: nd.ASTNode) -> None:
        super().leave_section(node)

    def visit_link(self, node: nd.ASTNode) -> None:
        if '://' in node.value:
            blank = 'target=”_blank”'
            url = node.value
            text = node.opts[0] if node.opts[0] else node.value
        else:
            blank = ''
            sect = node.target_section
            if not sect:
                raise ThothglyphError('target not found: {} from {}'.format(
                    node.value, '?'))
            sect_lv1 = sect
            while sect_lv1.parent:
                if sect_lv1.level == 1:
                    break
                sect_lv1 = sect_lv1.parent
            fname = str(sect_lv1.src_id) + '_' + sect_lv1.sectnum
            url = fname + '.html'
            url = url + "#" + str(sect.src_id) + '_' + (sect.id or sect.auto_id)
            text = node.opts[0] if node.opts[0] else sect.title
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
