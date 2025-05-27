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
import sys

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


class Lexer():
    class Token():
        def __init__(self, no: int, line: int, pos: int, key: str, value: str):
            self.no: int = no
            self.line: int = line
            self.pos: int = pos
            self.key: str = key
            self.value: str = value

        def __str__(self) -> str:
            s = f'Token({self.no}, {self.line}, {self.pos}, {self.key}, "{self.value}")'
            return s

    newline_token: str = '\n'
    preproc_keywords: Tuple[str] = (
        'if', 'elif', 'else',
        'end',
    )
    preproc_tokens: Dict[str, str] = {
        'CONFIG_BEGIN_LINE': r'^--- *(.+)$',
        'CONFIG_END_LINE': r'^---$',
        'COMMENT': r'%//(.+)',
        'CONTROL_FLOW': r'%# *(\w+)(.*)',
        'TEXT': r'^.*(?<!%//)|(?<!%#)$',
    }

    def __init__(self):
        self._preproc_tokens: Dict[str, re.Pattern] = {
            k: re.compile(v) for k, v in self.preproc_tokens.items()
        }

    def lex_preproc(self, data: str) -> List["Lexer.Token"]:
        return self.lex_pattern(self._preproc_tokens, data)

    def lex_pattern(self, patterns, data: str, begin=0) -> List["Lexer.Token"]:
        lines = data.split(self.newline_token)
        tokens: List[Lexer.Token] = list()
        for lineno, line in enumerate(lines):
            rest = line
            rests: List[Tuple[int, str]] = [(0, line)]
            linetokens: List[Lexer.Token] = list()
            while rests:
                for key, pattern in patterns.items():
                    newrests: List[Tuple[int, str]] = list()
                    matched = False
                    for rest in rests:
                        bpos, text = rest
                        m = pattern.search(text)
                        if m:
                            matched = True
                            no = -1
                            lno = lineno + begin
                            pos = bpos + m.start()
                            linetokens.append(
                                Lexer.Token(no, lno, pos, key, m.group(0))
                            )
                            logger.debug(linetokens[-1])
                            subtexts = text[:m.start()], text[m.end():]
                            if len(subtexts[0]) > 0:
                                newrests.append((bpos, subtexts[0]))
                            if len(subtexts[1]) > 0:
                                newrests.append((bpos + m.end(), subtexts[1]))
                        else:
                            newrests.append((bpos, text))
                    rests = newrests
                    if matched:
                        break
            linetokens.sort(key=lambda t: t.pos)
            for i, token in enumerate(linetokens):
                token.no = len(tokens) + i
            if all([
                len(rests) > 0,
                len(rests) == len(newrests),
                all([rests[i] == newrests[i] for i in range(len(rests))])
            ]):
                raise ThothglyphError(lineno, line, rests)
            tokens.extend(linetokens)
        return tokens


class MdParser(Parser):
    inline_tokens: Dict[str, str] = {
        'ATTR': r'{{%([A-Za-z0-9_\-]+)%}}',
    }
    deco_keymap: Dict[str, str] = {
        'em': 'EMPHASIS',
        'strong': 'STRONG',
    }
    inline_color_deco_tokens: Dict[str, str] = {
        'COLOR1': r'🔴',
        'COLOR2': r'🟡',
        'COLOR3': r'🟢',
        'COLOR4': r'🔵',
        'COLOR5': r'🟣',
    }
    listblock_keymap: Dict[str, nd.ASTNode] = {
        'bullet_list': nd.BulletListBlockNode,
        'ordered_list': nd.OrderedListBlockNode,
    }

    def __init__(self, reader: Reader):
        super().__init__(reader)
        self.pplines: List[Tuple[int, str]] = list()
        self.rootnode: Optional[nd.DocumentNode] = None
        self.nodes: List[nd.ASTNode] = list()
        self.lexer: Lexer = Lexer()

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

    def _tokens(self, token: Lexer.Token, offset: int) -> Lexer.Token:
        if self.tokens.index(token) + offset >= len(self.tokens):
            return None
        return self.tokens[self.tokens.index(token) + offset]

    def preprocess(self, data: str) -> str:
        self._init_config()
        try:
            self.tokens = self.lexer.lex_preproc(data)
        except ThothglyphError as e:
            lineno, line, rests = e.args
            lineno += 1
            msg = 'Unknown token.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        self.pplines = list()
        tokens = list() + self.tokens
        config_parsed = False
        while tokens:
            if tokens[0].key in ('CONFIG_BEGIN_LINE', 'CONFIG_END_LINE'):
                if config_parsed:
                    tokens.pop(0)
                else:
                    tokens = self.p_configblock(tokens)
                    config_parsed = True
            elif tokens[0].key == 'COMMENT':
                if tokens[0].pos == 0:
                    self._line_preprocessed(tokens[0])
                tokens.pop(0)
            elif tokens[0].key == 'CONTROL_FLOW':
                tokens = self.p_controlflow(tokens)
            else:
                self.pplines.append((tokens[0].line, tokens[0].value))
                tokens.pop(0)
        ppdata = '\n'.join(pp[1] for pp in self.pplines)
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

    def _line_preprocessed(self, token: Lexer.Token) -> None:
        is_head = (token.pos == 0)
        is_tail = token == self.tokens[-1] or \
            token.line + 1 == self._tokens(token, +1).line
        if is_head and is_tail:
            # remove config / comment / control-flow line
            pass
        else:
            # remove end-of-line comment
            lineno, lineval = self.pplines[-1]
            self.pplines[-1] = (lineno, lineval.rstrip())

    def p_configblock(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        config = self.rootnode.config
        begintoken = tokens[0]
        self._line_preprocessed(tokens[0])
        tokens.pop(0)
        lang = 'yaml'
        text = ''
        if begintoken.key in ('CONFIG_BEGIN_LINE', 'CONFIG_END_LINE'):
            path = None
            if m := re.match(Lexer.preproc_tokens['CONFIG_BEGIN_LINE'], begintoken.value):
                if m2 := re.match(r'\{include\} (\S+)(?: +(\S+))?', m.group(1)):
                    path = m2.group(1)
                    if m2.group(2):
                        lang = m2.group(2)
                    if os.path.exists(path):
                        with open(path, 'r', encoding=self.reader.encoding) as f:
                            text = f.read().rstrip()
                    else:
                        logger.warn('Include file cannot found: {}'.format(path))
                        text = ''
                else:
                    lang = m.group(1)
            if path is None:
                subtokens = list()
                while tokens:
                    if tokens[0].key == 'CONFIG_END_LINE':
                        break
                    self._line_preprocessed(tokens[0])
                    subtokens.append(tokens.pop(0))
                else:
                    lineno = begintoken.line + 1
                    msg = 'Config block is not closed.'
                    msg = f'{self.reader.path}:{lineno}: {msg}'
                    raise ThothglyphError(msg)
                self._line_preprocessed(tokens[0])
                tokens.pop(0)
                prev = begintoken
                text = str()
                for token in subtokens:
                    if token.line != prev.line:
                        if prev.key != 'CONFIG_END_LINE':
                            text += '\n'
                        text += token.value[0:]
                    else:
                        text += token.value
                    prev = token
                text = self.replace_text_attrs(text)
        try:
            config.parse(text, lang=lang)
        except Exception as e:
            e_type, e_value, e_tb = sys.exc_info()
            tb_depth = 0
            while e_tb.tb_next is not None:
                tb_depth += 1
                e_tb = e_tb.tb_next
            tb_line = 0
            if tb_depth == 1:
                m = re.match(r'line (\d)', str(e))
                if m:
                    tb_line = int(m.group(1))
            else:
                tb_line = e_tb.tb_lineno
            lineno = begintoken.line + tb_line + 1
            msg = 'Config block: ' + str(e)
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        return tokens

    def p_controlflow(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        match = re.match(Lexer.preproc_tokens['CONTROL_FLOW'], tokens[0].value)
        assert match
        keyword, sentence = match.group(1), match.group(2)
        if keyword == 'if':
            self._line_preprocessed(tokens[0])
            tokens.pop(0)
            cond = eval(sentence, {}, self.rootnode.config.attrs)
            tokens = self.p_if_else(tokens, [cond])
        else:
            lineno = tokens[0].line + 1
            msg = 'Illegal ControlFlow token.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        return tokens

    def p_if_else(self, tokens: List[Lexer.Token], conds: List[bool]) -> List[Lexer.Token]:
        firstflowtoken = self._tokens(tokens[0], -1) or tokens[0]
        lastflowtoken = tokens[0]
        lasttoken = tokens[0]
        while tokens:
            if tokens[0].key not in ('CONTROL_FLOW', 'COMMENT') and all(conds):
                self.pplines.append((tokens[0].line, tokens[0].value))
                lasttoken = tokens.pop(0)
            elif tokens[0].key == 'CONTROL_FLOW':
                match = re.match(Lexer.preproc_tokens['CONTROL_FLOW'], tokens[0].value)
                assert match
                lastflowtoken = tokens[0]
                keyword, sentence = match.group(1), match.group(2)
                if keyword == 'end':
                    break
                elif keyword == 'if':
                    self._line_preprocessed(tokens[0])
                    tokens.pop(0)
                    conds += [all(conds) and eval(sentence, {}, self.rootnode.config.attrs)]
                    tokens = self.p_if_else(tokens, conds)
                    lasttoken = tokens[0]
                    conds.pop()
                elif keyword == 'elif':
                    conds[-1] = not all(conds) and eval(sentence, {}, self.rootnode.config.attrs)
                    self._line_preprocessed(tokens[0])
                    lasttoken = tokens.pop(0)
                elif keyword == 'else':
                    conds[-1] = not all(conds)
                    self._line_preprocessed(tokens[0])
                    lasttoken = tokens.pop(0)
                else:
                    lineno = lastflowtoken.line + 1
                    msg = f'Unknown ControlFlow keyword: "{keyword}".'
                    msg = f'{self.reader.path}:{lineno}: {msg}'
                    raise ThothglyphError(msg)
            else:
                self._line_preprocessed(tokens[0])
                lasttoken = tokens.pop(0)
        else:
            lineno0 = firstflowtoken.line + 1
            # lineno1 = lastflowtoken.line + 1
            lineno1 = lasttoken.line + 1
            msg = 'ControlFlow is not closed.'
            msg = f'{self.reader.path}:{lineno0}-{lineno1}: {msg}'
            raise ThothglyphError(msg)
        self._line_preprocessed(tokens[0])
        tokens.pop(0)
        return tokens

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

    def _get_plain_text(self, mdnode: SyntaxTreeNode) -> str:
        text = str()
        for node in mdnode.walk():
            if node.type in ('text', 'code_inline'):
                text += node.content
        return text

    def p_section(self, mdnode: SyntaxTreeNode) -> None:
        m = re.match(r'h(\d+)', mdnode.tag)
        level = int(m.group(1))
        config = self.rootnode.config
        if hasattr(config, "h1_as_title") and config.h1_as_title:
            if level == 1:
                config.title = self._get_plain_text(mdnode.children[0])
                return
            else:
                level -= 1

        accepted = (nd.DocumentNode, nd.SectionNode)
        if not isinstance(self.nodes[-1], accepted):
            symbol = '#' * level
            title = self._get_plain_text(mdnode.children[0])
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
        section.title = self._get_plain_text(mdnode.children[0])
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
        m = re.match(r'([a-zA-Z0-9_-]*)(?: +(.+))?', mdnode.info.strip())
        if m:
            ext, args = m.group(1), m.group(2)
            self.p_customblock(mdnode, ext, args)
            return
        self.p_codeblock(mdnode)

    def p_customblock(self, mdnode: SyntaxTreeNode, ext: str, args: str) -> None:
        custom = nd.CustomBlockNode()
        custom.ext = ext
        self.nodes[-1].add(custom)
        text = self.replace_text_attrs(mdnode.content[:-1])
        custom.text = text

    def p_codeblock(self, mdnode: SyntaxTreeNode) -> None:
        code = nd.CodeBlockNode()
        self.nodes[-1].add(code)
        text = self.replace_text_attrs(mdnode.content[:-1])
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
        elif tp == 'table':
            self.p_basictable2(mdnode, tp, args)
        elif tp == 'list-table':
            self.p_listtable(mdnode, tp, args)
        else:
            msg = '"{}" directive is not supported.'.format(tp)
            logger.warn(msg)
            self.p_codeblock(mdnode)

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
        table.type = 'normal'
        table.row = len(trows)
        table.col = len(trows[0].children)
        table.headers = header_splitter
        if len(aligns) == 0:
            aligns = ['c' for i in range(table.col)]
        table.aligns = aligns
        table.widths = [0 for i in range(table.col)]
        table.width = 0
        table.fontsize = ''
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
                cell.width = table.widths[c]
                style = col_mdnode.attrs.get('style', '')
                m = re.search(r'text-align:(\w+)', style)
                if m:
                    alignkey = m.group(1)
                    align_table = {'left': 'l', 'center': 'c', 'right': 'r'}
                    if alignkey in align_table.keys():
                        cell.align = align_table[alignkey]
                row.add(cell)
                if len(col_mdnode.children[0].children) > 0:
                    text_mdnode = col_mdnode.children[0].children[0]
                    if text_mdnode.type == 'text':
                        self._tablecell_merge(table, cell, r, c, text_mdnode.content)
                self.nodes.append(cell)
                self.p_inlinemarkup(col_mdnode.children[0])
                self.nodes.pop()

    def _parse_table_optargs(self, opts: Dict[str, str]) -> Dict[str, str]:
        newopts: Dict[str, str] = dict()
        newopts['type'] = opts.get('type', 'normal')
        newopts['w'] = opts.get('w', '')
        newopts['fontsize'] = opts.get('fontsize', '')
        for k, v in opts.items():
            if k == 'align':
                newopts['align'] = [c for c in v]
            elif k == 'widths':
                newopts['widths'] = [int(x.strip()) for x in v.split(',')]
            elif k == 'colspec':
                colspec_ptn = r'(-1|[1-9]|[1-9][0-9]+)?(l|c|r|x|xc|xr)'
                colmatchs = [re.match(colspec_ptn, x.strip()) for x in v.split(',')]
                if not all(colmatchs):
                    pass  # logger.warn()
                newopts['align'] = list()
                newopts['widths'] = list()
                for m in colmatchs:
                    newopts['widths'].append(m.group(1) or 1)
                    newopts['align'].append(m.group(2))
        return newopts

    def p_basictable2(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        text = self.replace_text_attrs(mdnode.content)
        opts, data = self._parse_directive(text)
        opts = self._parse_table_optargs(opts)

        table = nd.TableBlockNode()
        self.nodes[-1].add(table)
        lines = data.splitlines()
        tabletexts = list()
        aligns = list()
        header_splitter = -1
        for i, line in enumerate(lines):
            rowtexts = re.split(r' *\| *', line.strip())[1:-1]
            ms = [re.match(r'^[+:]?-+[+:]?$', c) for c in rowtexts]
            if all(ms) and header_splitter == -1:
                aligns = list()
                for m in ms:
                    assert m
                    mg = m.group(0)
                    if mg[0] == mg[-1] == ':':
                        aligns.append('c')
                    elif mg[0] == mg[-1] == '+':
                        aligns.append('xc')
                    elif mg[0] == '-' and mg[-1] == ':':
                        aligns.append('r')
                    elif mg[0] == '-' and mg[-1] == '+':
                        aligns.append('xr')
                    elif mg[0] == ':' and mg[-1] == '-':
                        aligns.append('l')
                    elif mg[0] == '+' and mg[-1] == '-':
                        aligns.append('x')
                    else:
                        aligns.append('l')
                header_splitter = i
            else:
                tabletexts.append(rowtexts)
        if header_splitter < 0:
            header_splitter = 0
        table.type = opts.get('type', 'normal')
        table.row = len(tabletexts)
        table.col = len(tabletexts[0])
        table.headers = header_splitter
        if len(aligns) == 0:
            aligns = ['c' for i in range(table.col)]
        table.aligns = aligns
        table.widths = opts.get('widths', [0 for i in range(table.col)])
        table.width = opts.get('w')
        table.fontsize = opts.get('fontsize', '')
        for r, rowtexts in enumerate(tabletexts):
            row = nd.TableRowNode()
            row.idx = r
            if r < table.headers:
                row.tp = 'header'
            table.add(row)
            if len(rowtexts) != table.col or len(table.aligns) != table.col:
                # lineno = begintoken.line + 1 + r
                lineno = mdnode.map[0]
                if 0 < table.headers < lineno:
                    lineno += 1
                msg = 'Table rows have different sizes.'
                msg = f'{self.reader.path}:{lineno}: {msg}'
                raise ThothglyphError(msg)
            for c, celltext in enumerate(rowtexts):
                cell = nd.TableCellNode()
                row.add(cell)
                cell.idx = c
                cell.align = table.aligns[c]
                cell.width = table.widths[c]
                text = self.replace_text_attrs(celltext)
                text = self._tablecell_merge(table, cell, r, c, text)
                try:
                    text_tokens = mdit.parse(text)
                    text_mdnodes = SyntaxTreeNode(text_tokens)
                    if len(text_mdnodes.children) > 0:
                        self.nodes.append(cell)
                        self.p_inlinemarkup(text_mdnodes.children[0].children[0])
                        self.nodes.pop()
                except Exception as e:
                    print(e)
                    cell.add(nd.TextNode(text))

    def p_listtable(self, mdnode: SyntaxTreeNode, tp: str, args: str) -> None:
        text = self.replace_text_attrs(mdnode.content)
        opts, data = self._parse_directive(text)
        table_headers = opts.get('header-rows', '0')
        opts = self._parse_table_optargs(opts)
        # title = args or ''
        tokens = mdit.parse(data)
        child_mdnodes = SyntaxTreeNode(tokens)
        table = nd.TableBlockNode()
        self.nodes[-1].add(table)
        aligns = list()
        if opts.get('align'):
            for c in opts.get('align'):
                aligns.append(c)
        table.type = opts.get('type', 'normal')
        table.row = len(child_mdnodes.children[0].children)
        table.col = len(child_mdnodes.children[0].children[0].children[0].children)
        try:
            table.headers = int(table_headers)
        except Exception:
            table.headers = 0
        if len(aligns) == 0:
            aligns = ['c' for i in range(table.col)]
        table.aligns = aligns
        table.widths = opts.get('widths', [0 for i in range(table.col)])
        table.width = opts.get('w')
        table.fontsize = opts.get('fontsize', '')
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
                cell.width = table.widths[c]
                self.nodes.append(cell)
                self.p_blocks(col_mdnode.children)
                self.nodes.pop()
                try:
                    text_mdnode = col_mdnode.children[0].children[0].children[0]
                    if text_mdnode.type == 'text':
                        text = self._tablecell_merge(table, cell, r, c, text_mdnode.content)
                        # cell.children[0].children[0].text = text
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
            colors = self.inline_color_deco_tokens.values()
            if len(mdnode.content) > 0 and mdnode.content[0] in colors:
                self.p_color_deco(mdnode)
            else:
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
                colors = self.inline_color_deco_tokens.values()
                if len(mdnode.content) > 0 and mdnode.content[0] in colors:
                    self.p_color_deco(mdnode)
                else:
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

    def p_color_deco(self, mdnode: SyntaxTreeNode) -> None:
        color_keys = list(self.inline_color_deco_tokens.keys())
        color_values = list(self.inline_color_deco_tokens.values())
        deco = nd.DecorationRoleNode()
        deco.role = color_keys[color_values.index(mdnode.content[0])]
        self.nodes[-1].add(deco)
        tokens = mdit.parse(mdnode.content[1:])
        child_mdnodes = SyntaxTreeNode(tokens)
        if len(child_mdnodes.children) > 0:
            self.nodes.append(deco)
            self.p_decotext(child_mdnodes.children[0].children[0].children)
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
            if any([
                isinstance(self.nodes[-1], nd.TableCellNode),  # BasicTable
                all([  # ListTable
                    isinstance(self.nodes[-1], nd.ParagraphNode),
                    isinstance(self.nodes[-2], nd.TableCellNode),
                ]),
            ]) and mdnode.previous_sibling is None:
                hmarker = self._extract_tablecell_merge_hmarker(content)
                vmarker = self._extract_tablecell_merge_vmarker(content)
                if hmarker:
                    content = content[len(hmarker):]
                elif vmarker:
                    content = content[len(vmarker):]
            elif mdnode.parent.parent.parent.type == 'list_item':
                m = re.match(r'^\[[ x-]\] ', mdnode.content)
                if m:
                    content = mdnode.content[4:]
        except Exception:
            pass
        text.text = self.replace_text_attrs(content)
        self.nodes[-1].add(text)


class MdReader(Reader):
    target = 'md'
    ext = 'md'

    def __init__(self, parent: Optional[Reader] = None, **kwargs):
        super().__init__(parent=parent, **kwargs)
        self.parser: MdParser = MdParser(self)

    def read(self, path: str, encoding: Optional[str] = None) -> nd.ASTNode:
        node = super().read(path, encoding)
        self._convert_link_slug(node)
        return node

    def _slugify(self, text):
        slug = re.sub(r'[^\w\- ]', '', text)
        slug = re.sub(r' ', '-', slug)
        slug = '#' + slug.lower()
        return slug

    def _convert_link_slug(self, node: nd.ASTNode) -> None:
        slug_sections = list()
        for n, gofoward in node.walk_depth():
            if not gofoward:
                continue
            if isinstance(n, nd.SectionNode) and not n.id:
                slug = self._slugify(n.title)
                slug_sections.append([n, slug])
        slug_sections.sort(key=lambda x: x[1])
        if len(slug_sections) > 1:
            prev_slug = slug_sections[0][1]
            count = 0
            for i, (n, slug) in enumerate(slug_sections[1:]):
                if slug != prev_slug:
                    count = 0
                else:
                    count += 1
                    new_slug = slug + '-' + str(count)
                    slug_sections[i + 1][1] = new_slug
                prev_slug = slug
        slug_table = dict([(x[1], x[0]) for x in slug_sections])
        for n, gofoward in node.walk_depth():
            if not gofoward:
                continue
            if isinstance(n, nd.LinkNode):
                if '://' in n.value:
                    continue
                if n.target_id in slug_table:
                    n.value = slug_table[n.target_id].auto_id
