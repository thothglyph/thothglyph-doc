from typing import Dict, List, Optional, Tuple
from thothglyph.error import ThothglyphError
from thothglyph.reader import ReaderClass
from thothglyph.reader.reader import Reader, Parser
from thothglyph.node import nd
from markdown_it import MarkdownIt
from markdown_it.token import Token
from markdown_it.tree import SyntaxTreeNode
from mdit_py_plugins.front_matter import front_matter_plugin
# from mdit_py_plugins.footnote import footnote_plugin
from mdit_py_plugins.deflist import deflist_plugin
from mdit_py_plugins.field_list import fieldlist_plugin
# from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.admon import admon_plugin
from mdit_py_plugins.attrs import attrs_plugin
from mdit_py_plugins.attrs import attrs_block_plugin
from mdit_py_plugins.myst_role import myst_role_plugin
from mdit_py_plugins.myst_blocks import myst_block_plugin
import urllib
import re
import os

from thothglyph.node import logging

logger = logging.getLogger(__file__)


mdit = (
    MarkdownIt('commonmark')
    .use(front_matter_plugin)
    # .use(footnote_plugin)
    .use(deflist_plugin)
    .use(fieldlist_plugin)
    # .use(tasklists_plugin)
    .use(admon_plugin)
    .use(attrs_plugin)
    .use(attrs_block_plugin)
    .use(myst_role_plugin)
    .use(myst_block_plugin)
    .enable('table')
)


class MdParser(Parser):
    preproc_keywords: Tuple[str] = (
        'if', 'elif', 'else',
        'end',
    )
    preproc_tokens: Dict[str, str] = {
        'CONFIG_LINE': r'---$',
        'COMMENT': r'%(.+)',
        'CONTROL_FLOW': r'%%(\w+)(.*)',
        'TEXT': r'[^⑇%*',
    }
    inline_tokens: Dict[str, str] = {
        'ATTR': r'{{%([A-Za-z0-9_\-]+)%}}',
    }
    deco_keymap: Dict[str, str] = {
        'em': 'EMPHASIS',
        'strong': 'STRONG',
    }
    listblock_keymap: Dict[str, nd.ASTNode] = {
        'bullet_list': nd.BulletListBlockNode,
        'ordered_list': nd.OrderedListBlockNode,
    }

    def __init__(self, reader: Reader):
        super().__init__(reader)
        self.pplines: List[str] = list()
        self.rootnode: Optional[nd.DocumentNode] = None
        self.nodes: List[nd.ASTNode] = list()

        self.rootnode = nd.DocumentNode()
        self.nodes.append(self.rootnode)

    def parse(self, data: str) -> Optional[nd.DocumentNode]:
        ppdata = self.preprocess(data)
        try:
            self.tokens = mdit.parse(ppdata)
        except ThothglyphError as e:
            lineno, line, rests = e.args
            lineno += 1
            msg = 'Unknown token.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        tokens = list() + self.tokens
        tokens = self.p_document(tokens)
        return self.rootnode

    def preprocess(self, data: str) -> str:
        self._init_config()
        tokens = mdit.parse(data)
        mdnodes = SyntaxTreeNode(tokens)
        if mdnodes.children[0].type == 'front_matter':
            self.p_configblock(mdnodes.children[0])
        ppdata = self.replace_text_attrs(data)
        return ppdata

    def _init_config(self) -> None:
        config = nd.ConfigNode()
        if self.reader.parent:
            pconfig = self.reader.parent.parser.rootnode.config
            pattrs = dict(pconfig.__dict__)
            for key in ('parent', 'children', 'id'):
                pattrs.pop(key)
            for key in pattrs:
                setattr(config, key, pattrs[key])
        self.rootnode.config = config

    def p_configblock(self, mdnode: List[SyntaxTreeNode]) -> None:
        assert mdnode.type == 'front_matter'
        config = self.rootnode.config
        text = mdnode.content
        try:
            config.parse(text)
        except Exception as e:
            lineno = mdnode.map[0]
            msg = 'Config block: ' + str(e)
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)

    def p_document(self, tokens: List[Token]) -> List[Token]:
        logger.debug(mdit.get_all_rules())
        mdnodes = SyntaxTreeNode(tokens)
        logger.debug(mdnodes.pretty(indent=2, show_text=True))
        self.p_blocks(mdnodes.children)
        return tokens

    def p_blocks(self, mdnodes: List[SyntaxTreeNode]) -> None:
        for mdnode in mdnodes:
            if mdnode.type == 'heading':
                self.p_section(mdnode)
            elif mdnode.type == 'table':
                self.p_basictable(mdnode)
            elif mdnode.type in self.listblock_keymap.keys():
                self.p_listblock(mdnode)
            elif mdnode.type == 'dl':
                self.p_descriptionlist(mdnode)
            elif mdnode.type == 'field_list':
                self.p_fieldlist(mdnode)
            elif mdnode.type == 'fence':
                self.p_fenceblock(mdnode)
            elif mdnode.type == 'myst_block_break':
                self.p_horizon(mdnode)
            elif mdnode.type == 'paragraph':
                self.p_paragraph(mdnode)
        pass

    @property
    def _lastsection(self) -> nd.SectionNode:
        idx = len(self.nodes) - 1
        types = (nd.DocumentNode, nd.SectionNode)
        while idx >= 0:
            if isinstance(self.nodes[idx], types):
                break
            idx -= 1
        else:
            msg = 'Nothing document or sections.'
            msg = f'{self.reader.path}: {msg}'
            raise ThothglyphError(msg)
        return self.nodes[idx]

    def p_section(self, mdnode: SyntaxTreeNode) -> None:
        m = re.match(r'h(\d+)', mdnode.tag)
        level = int(m.group(1))

        accepted = (nd.DocumentNode, nd.SectionNode)
        if not isinstance(self.nodes[-1], accepted):
            symbol = '#' * level
            title = mdnode.children[0].children[0].content
            text = f'{symbol} {title}'
            text = nd.TextNode(text)
            self.nodes[-1].add(text)
            return

        if level > self._lastsection.level + 1:
            msg = 'Section level {} appears suddenly.'.format(level)
            msg += ' Section level must not be skipped.'
            lineno = mdnode.map[0]
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        poplevel = max(self._lastsection.level - level + 1, 0)
        for i in range(poplevel):
            self.nodes.pop()
        section = nd.SectionNode()
        section.level = level
        nonum = bool(mdnode.attrs.get('nonum', ''))
        notoc = bool(mdnode.attrs.get('notoc', ''))
        section.opts['nonum'] = nonum or notoc
        section.opts['notoc'] = notoc
        section.title = mdnode.children[0].children[0].content
        prevnode = mdnode.previous_sibling
        if prevnode and prevnode.type == 'myst_target':
            section.id = prevnode.content
        self.nodes[-1].add(section)
        self.nodes.append(section)

    def _is_checklist(self, mdnode: SyntaxTreeNode) -> None:
        for listitem in mdnode.children:
            try:
                text = listitem.children[0].children[0].children[0]
            except Exception:
                break
            m = re.match(r'^\[[ x-]\] ', text.content)
            if m:
                listitem.attrs['marker'] = text.content[1]
                # text.content = text.content[4:]
            else:
                break
        else:
            return True
        return False

    def p_listblock(self, mdnode: SyntaxTreeNode) -> None:
        if self._is_checklist(mdnode):
            listblock = nd.CheckListBlockNode()
        else:
            listblock = self.listblock_keymap[mdnode.type]()
        # listblock.level = len(m.group(1))
        # listblock.indent = len(m.group(0))
        self.nodes[-1].add(listblock)
        self.nodes.append(listblock)
        for childnode in mdnode.children:
            self.p_listitem(childnode)
        self.nodes.pop()

    def p_descriptionlist(self, mdnode: SyntaxTreeNode) -> None:
        listblock = nd.DescriptionListBlockNode()
        # listblock.level = len(m.group(1))
        # listblock.indent = len(m.group(0))
        self.nodes[-1].add(listblock)
        self.nodes.append(listblock)
        item = None
        prev = SyntaxTreeNode()
        for child in mdnode.children:
            if child.type == 'dt' and prev.type != 'dt':
                item = nd.ListItemNode()
                item.title = ''
                self.nodes[-1].add(item)
            if child.type == 'dt':
                title = nd.TitleNode()
                item.add(title)
                self.nodes.append(title)
                self.p_inlinemarkup(child.children[0])
                self.nodes.pop()
            elif child.type == 'dd':
                self.nodes.append(item)
                self.p_blocks(child.children)
                self.nodes.pop()
        self.nodes.pop()

    def p_fieldlist(self, mdnode: SyntaxTreeNode) -> None:
        listblock = nd.DescriptionListBlockNode()
        # listblock.level = len(m.group(1))
        # listblock.indent = len(m.group(0))
        self.nodes[-1].add(listblock)
        self.nodes.append(listblock)
        item = None
        prev = SyntaxTreeNode()
        for child in mdnode.children:
            if child.type == 'fieldlist_name' and prev.type != 'fieldlist_body':
                item = nd.ListItemNode()
                item.title = ''
                self.nodes[-1].add(item)
            if child.type == 'fieldlist_name':
                title = nd.TitleNode()
                item.add(title)
                self.nodes.append(title)
                self.p_inlinemarkup(child.children[0])
                self.nodes.pop()
            elif child.type == 'fieldlist_body':
                self.nodes.append(item)
                self.p_blocks(child.children)
                self.nodes.pop()
        self.nodes.pop()

    def p_listitem(self, mdnode: SyntaxTreeNode) -> None:
        item = nd.ListItemNode()
        if isinstance(self.nodes[-1], nd.CheckListBlockNode):
            item.marker = mdnode.attrs['marker']
        self.nodes[-1].add(item)
        self.nodes.append(item)
        self.p_blocks(mdnode.children)
        self.nodes.pop()

    def p_fenceblock(self, mdnode: SyntaxTreeNode) -> None:
        m = re.match(r'{([a-zA-Z0-9_-]+)}(?: +(.+))?', mdnode.info.strip())
        if m:
            tp, args = m.group(1), m.group(2)
            self.p_directive(mdnode, tp, args)
            return
        self.p_codeblock(mdnode)

    def p_codeblock(self, mdnode: SyntaxTreeNode) -> None:
        code = nd.CodeBlockNode()
        self.nodes[-1].add(code)
        text = self.replace_text_attrs(mdnode.content)
        text = nd.TextNode(text)
        code.add(text)

    def p_directive(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        if tp == 'toc':
            self.p_tocblock(mdnode, tp, args)
        elif tp == 'footnote':
            self.p_footnotelist(mdnode, tp, args)
        elif tp == 'reference':
            self.p_referencelist(mdnode, tp, args)
        elif tp == 'figure':
            self.p_figureblock(mdnode, tp, args)
        elif tp == 'literalinclude':
            self.p_literalinclude(mdnode, tp, args)
        elif tp == 'include':
            self.p_include(mdnode, tp, args)
        elif tp == 'list-table':
            self.p_listtable(mdnode, tp, args)
        else:
            msg = '"{}" directive is not supported.'.format(tp)
            logger.warn(msg)

    def _parse_directive(self, text):
        opts = {}
        data = []
        is_opt = True
        for line in text.splitlines():
            if is_opt:
                m = re.match(r':([^:]+): *(.+)', line)
                if m:
                    k, v = m.group(1), m.group(2)
                    opts[k] = v
                elif line.strip() == '':
                    pass
                else:
                    is_opt = False
            if not is_opt:
                data.append(line)
        data = '\n'.join(data)
        return opts, data

    def p_tocblock(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        toc = nd.TocBlockNode()
        toc.opts = mdnode.attrs
        toc.value = mdnode.content
        self.nodes[-1].add(toc)

    def p_footnotelist(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        monolist = nd.FootnoteListBlockNode()
        self.nodes[-1].add(monolist)
        data = mdnode.content
        tokens = mdit.parse(data)
        child_mdnodes = SyntaxTreeNode(tokens)
        self.nodes.append(monolist)
        item = None
        prev = SyntaxTreeNode()
        for child in child_mdnodes.children[0].children:
            if child.type == 'fieldlist_name' and prev.type != 'fieldlist_body':
                item = nd.ListItemNode()
                item.title = ''
                self.nodes[-1].add(item)
            if child.type == 'fieldlist_name':
                title = child.children[0].children[0].content
                item.title = title
            elif child.type == 'fieldlist_body':
                self.nodes.append(item)
                self.p_blocks(child.children)
                self.nodes.pop()
        self.nodes.pop()

    def p_referencelist(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        monolist = nd.ReferenceListBlockNode()
        self.nodes[-1].add(monolist)
        data = mdnode.content
        tokens = mdit.parse(data)
        child_mdnodes = SyntaxTreeNode(tokens)
        self.nodes.append(monolist)
        item = None
        prev = SyntaxTreeNode()
        for child in child_mdnodes.children[0].children:
            if child.type == 'fieldlist_name' and prev.type != 'fieldlist_body':
                item = nd.ListItemNode()
                item.title = ''
                self.nodes[-1].add(item)
            if child.type == 'fieldlist_name':
                title = child.children[0].children[0].content
                item.title = title
            elif child.type == 'fieldlist_body':
                self.nodes.append(item)
                self.p_blocks(child.children)
                self.nodes.pop()
        self.nodes.pop()

    def p_figureblock(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        fig = nd.FigureBlockNode()
        fig.opts = ['']
        fig.caption = args or ''
        self.nodes[-1].add(fig)
        data = mdnode.content
        tokens = mdit.parse(data)
        child_mdnodes = SyntaxTreeNode(tokens)
        self.nodes.append(fig)
        self.p_blocks(child_mdnodes.children)
        self.nodes.pop()

    def p_literalinclude(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        text = self.replace_text_attrs(mdnode.content)
        opts, data = self._parse_directive(text)
        code = nd.CodeBlockNode()
        code.lang = opts.get('language', '')
        self.nodes[-1].add(code)
        text = nd.TextNode()
        path = args
        if os.path.exists(path):
            with open(path, 'r', encoding=self.reader.encoding) as f:
                text.text = f.read().rstrip()
        else:
            logger.warn('Include file cannot found: {}'.format(path))
            text = nd.TextNode(mdnode.content)
        code.add(text)

    def p_include(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        path = args
        if self._check_recursive_include(path):
            _, ext = os.path.splitext(path)
            reader: Reader = ReaderClass(ext[1:])(parent=self.reader)
            subdoc = reader.read(path)
            lastsection = self._lastsection
            for node, gofoward in subdoc.walk_depth():
                if not gofoward:
                    continue
                if isinstance(node, nd.SectionNode):
                    node.level += lastsection.level
            p = self.nodes[-1]
            for node in subdoc.children:
                p.add(node)

    def p_horizon(self, mdnode: SyntaxTreeNode) -> None:
        horizon = nd.HorizonBlockNode()
        self.nodes[-1].add(horizon)

    def _extract_tablecell_merge_hmarker(self, text: str):
        if text.startswith(':<'):
            return ':<'
        return ''

    def _extract_tablecell_merge_vmarker(self, text: str):
        if text.startswith(':^'):
            return ':^'
        return ''

    def p_basictable(self, mdnode: SyntaxTreeNode) -> None:
        table = nd.TableBlockNode()
        self.nodes[-1].add(table)
        aligns = list()
        header_splitter = -1
        if len(mdnode.children) > 1:
            header_splitter = len(mdnode.children[0].children)
        if header_splitter < 0:
            header_splitter = 0
        trows = mdnode.children[0].children
        if len(mdnode.children) > 1:
            trows += mdnode.children[1].children
        table.row = len(trows)
        table.col = len(trows[0].children)
        table.headers = header_splitter
        if len(aligns) == 0:
            aligns = ['c' for i in range(table.col)]
        table.aligns = aligns
        for r, row_mdnode in enumerate(trows):
            row = nd.TableRowNode()
            row.idx = r
            if r < table.headers:
                row.tp = 'header'
            table.add(row)
            for c, col_mdnode in enumerate(row_mdnode.children):
                cell = nd.TableCellNode()
                cell.idx = c
                cell.align = table.aligns[c]
                style = col_mdnode.attrs.get('style', '')
                m = re.search(r'text-align:(\w+)', style)
                if m:
                    alignkey = m.group(1)
                    align_table = {'left': 'l', 'center': 'c', 'right': 'r'}
                    if alignkey in align_table.keys():
                        cell.align = align_table[alignkey]
                row.add(cell)
                text_mdnode = col_mdnode.children[0].children[0]
                if text_mdnode.type == 'text':
                    self._tablecell_merge(table, cell, r, c, text_mdnode.content)
                self.nodes.append(cell)
                self.p_inlinemarkup(col_mdnode.children[0])
                self.nodes.pop()

    def p_listtable(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        text = self.replace_text_attrs(mdnode.content)
        opts, data = self._parse_directive(text)
        # title = args or ''
        tokens = mdit.parse(data)
        child_mdnodes = SyntaxTreeNode(tokens)
        table = nd.TableBlockNode()
        self.nodes[-1].add(table)
        aligns = list()
        if opts.get('align'):
            for c in opts.get('align'):
                aligns.append(c)
        table.row = len(child_mdnodes.children[0].children)
        table.col = len(child_mdnodes.children[0].children[0].children[0].children)
        try:
            table.headers = int(opts.get('header-rows', '0'))
        except Exception:
            table.headers = 0
        if len(aligns) == 0:
            aligns = ['c' for i in range(table.col)]
        table.aligns = aligns
        for r, row_mdnode in enumerate(child_mdnodes.children[0].children):
            row = nd.TableRowNode()
            row.idx = r
            if r < table.headers:
                row.tp = 'header'
            table.add(row)
            for c, col_mdnode in enumerate(row_mdnode.children[0].children):
                cell = nd.TableCellNode()
                row.add(cell)
                cell.idx = c
                cell.align = table.aligns[c]
                self.nodes.append(cell)
                self.p_blocks(col_mdnode.children)
                self.nodes.pop()
                try:
                    text_mdnode = col_mdnode.children[0].children[0].children[0]
                    if text_mdnode.type == 'text':
                        self._tablecell_merge(table, cell, r, c, text_mdnode.content)
                except Exception:
                    pass

    def p_paragraph(self, mdnode: SyntaxTreeNode) -> None:
        paragraph = nd.ParagraphNode()
        self.nodes[-1].add(paragraph)
        self.nodes.append(paragraph)
        self.p_inlinemarkup(mdnode.children[0])
        self.nodes.pop()

    def p_inlinemarkup(self, mdnode: SyntaxTreeNode) -> None:
        for childnode in mdnode.children:
            self.p_inline(childnode)

    def p_inline(self, mdnode: SyntaxTreeNode) -> None:
        if mdnode.type == 'image':
            self.p_image(mdnode)
        elif mdnode.type == 'link':
            self.p_link(mdnode)
        elif mdnode.type == 'myst_role':
            self.p_role(mdnode)
        elif mdnode.type in self.deco_keymap.keys():
            self.p_deco(mdnode)
        elif mdnode.type == 'code_inline':
            self.p_codeinline(mdnode)
        elif mdnode.type == 'html_inline':
            pass
        else:
            self.p_text(mdnode)

    def p_decotext(self, mdnodes: SyntaxTreeNode) -> None:
        for mdnode in mdnodes:
            if mdnode.type in self.deco_keymap.keys():
                self.p_deco(mdnode)
            elif mdnode.type == 'code_inline':
                self.p_codeinline(mdnode)
            else:
                self.p_text(mdnode)

    def p_deco(self, mdnode: SyntaxTreeNode) -> None:
        deco = nd.DecorationRoleNode()
        deco.role = self.deco_keymap[mdnode.type]
        self.nodes[-1].add(deco)
        self.nodes.append(deco)
        self.p_decotext(mdnode.children)
        self.nodes.pop()

    def p_codeinline(self, mdnode: SyntaxTreeNode) -> None:
        deco = nd.DecorationRoleNode()
        deco.role = 'CODE'
        self.nodes[-1].add(deco)
        text = nd.TextNode()
        text.text = self.replace_text_attrs(mdnode.content)
        deco.add(text)

    def p_image(self, mdnode: SyntaxTreeNode) -> None:
        image = nd.ImageRoleNode()
        image.role = 'image'
        image.opts = mdnode.attrs
        image.value = self.replace_text_attrs(mdnode.attrs['src'])
        self.nodes[-1].add(image)

    def p_link(self, mdnode: SyntaxTreeNode) -> None:
        link = nd.LinkNode()
        text = mdnode.children[0].content if len(mdnode.children) > 0 else ''
        link.opts = [text]
        link.value = mdnode.attrs['href']
        if '://' not in link.value:
            link.value = urllib.parse.unquote(link.value)
        self.nodes[-1].add(link)

    def p_role(self, mdnode: SyntaxTreeNode) -> None:
        role = nd.RoleNode()
        role.role = mdnode.meta['name']
        role.opts = ''
        role.value = mdnode.content
        if role.role == 'kbd':
            self.p_kbd(mdnode, role)
        elif role.role == 'btn':
            self.p_btn(mdnode, role)
        elif role.role == 'menu':
            self.p_menu(mdnode, role)
        elif role.role == 'footnote':
            self.p_footnote(mdnode, role)
        elif role.role == 'cite':
            self.p_reference(mdnode, role)
        else:
            self.nodes[-1].add(role)

    def p_kbd(self, mdnode: SyntaxTreeNode, role: nd.RoleNode) -> None:
        kbd = nd.KbdRoleNode()
        kbd.role = mdnode.meta['name']
        kbd.opts = role.opts
        text = self.replace_text_attrs(role.value)
        kbd.value = text.strip().split()
        self.nodes[-1].add(kbd)

    def p_btn(self, mdnode: SyntaxTreeNode, role: nd.RoleNode) -> None:
        btn = nd.BtnRoleNode()
        btn.role = role.role
        btn.opts = role.opts
        text = self.replace_text_attrs(role.value)
        btn.value = text
        self.nodes[-1].add(btn)

    def p_menu(self, mdnode: SyntaxTreeNode, role: nd.RoleNode) -> None:
        menu = nd.MenuRoleNode()
        menu.role = role.role
        menu.opts = role.opts
        text = self.replace_text_attrs(role.value)
        menu.value = re.split(r' +\> +', text.strip())
        self.nodes[-1].add(menu)

    def p_footnote(self, mdnode: SyntaxTreeNode, role: nd.RoleNode) -> None:
        link = nd.FootnoteNode()
        link.value = role.value
        self.nodes[-1].add(link)

    def p_reference(self, mdnode: SyntaxTreeNode, role: nd.RoleNode) -> None:
        link = nd.ReferenceNode()
        link.value = role.value
        self.nodes[-1].add(link)

    def replace_text_attrs(self, text: str) -> str:
        def attrvalue(m):
            attr = m.group(1)
            assert isinstance(self.rootnode, nd.DocumentNode)
            if hasattr(self.rootnode.config, 'attrs'):
                attrs = self.rootnode.config.attrs
                return str(attrs.get(attr, m.group(0)))
            else:
                return m.group(0)

        newtext = re.sub(
            self.inline_tokens['ATTR'], attrvalue, text,
            flags=re.MULTILINE | re.DOTALL
        )
        return newtext

    def p_text(self, mdnode: SyntaxTreeNode) -> None:
        text = nd.TextNode()
        content = mdnode.content
        try:
            if mdnode.parent.parent.parent.type == 'list_item':
                m = re.match(r'^\[[ x-]\] ', mdnode.content)
                if m:
                    content = mdnode.content[4:]
            elif any([
                isinstance(self.nodes[-1], nd.TableCellNode),
            ]) and mdnode.previous_sibling is None:
                hmarker = self._extract_tablecell_merge_hmarker(content)
                vmarker = self._extract_tablecell_merge_vmarker(content)
                if hmarker:
                    content = content[len(hmarker):]
                elif vmarker:
                    content = content[len(vmarker):]
        except Exception:
            pass
        text.text = self.replace_text_attrs(content)
        self.nodes[-1].add(text)


class MdReader(Reader):
    target = 'md'
    ext = 'md'

    def __init__(self, parent: Optional[Reader] = None):
        super().__init__(parent=parent)
        self.parser: MdParser = MdParser(self)

    def read(self, path: str, encoding: Optional[str] = None) -> nd.ASTNode:
        try:
            return super().read(path, encoding)
        except Exception as e:
            _, errormsg = e.args
            msg = 'File cannot found: {}'.format(e.filename)
            raise ThothglyphError(msg)
