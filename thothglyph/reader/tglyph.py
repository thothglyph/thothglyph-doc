from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from thothglyph.error import ThothglyphError
from thothglyph.reader import ReaderClass
from thothglyph.reader.reader import Reader, Parser
from thothglyph.node import nd
import re
import os
import sys

from thothglyph.node import logging

logger = logging.getLogger(__file__)


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
        'CONFIG_LINE': r'⑇⑇⑇$',
        'COMMENT': r'⑇⑇(.+)',
        'CONTROL_FLOW': r'⑇(\w+)(.*)',
        'TEXT': r'[^⑇]*',
    }
    block_tokens: Dict[str, str] = {
        'PREPROCESSED_LINE': r'^⑇$',
        'SECTION_TITLE_LINE': r' *((?:▮+)|(?:▯+))([*+]?) +([^⟦]+) *(?:⟦([^⟧]*)⟧)?',
        'TOC_LINE': r' *¤toc(?:⟦([^⟧]*)⟧)?⸨([^⸩]*)⸩ *$',
        'FIGURE_LINE': r' *¤figure(?:⟦([^⟧]*)⟧)?⸨([^⸩]*)⸩ *$',
        'TABLE_LINE': r'^ *\|.+\| *$',
        'LISTTABLE_BEGIN_LINE': r'^ *\|=== *(?:⟦([^⟧]*)⟧)? *$',
        'LISTTABLE_END_LINE': r'^ *===\| *$',
        'FOOTNOTE_LIST_SYMBOL': r' *•\[\^(.+)\](?: +|$)',
        'REFERENCE_LIST_SYMBOL': r' *•\[\#(.+)\](?: +|$)',
        'CHECK_LIST_SYMBOL': r' *(•+)(\[[ x-]\])(?: +|$)',
        'BULLET_LIST_SYMBOL': r' *(•+)(?: +|$)',
        'ORDERED_LIST_SYMBOL': r' *(꓾+)(?: +|$)',
        'DESC_LIST_SYMBOL': r' *(ᛝ+)([^ᛝ]+)ᛝ(?: +|$)',
        'LIST_TERMINATOR_SYMBOL': r' *(◃+) *$',
        'CUSTOM_LINE': r'( *)¤¤¤(.*)',
        'CODE_LINE': r'( *)⸌⸌⸌(.*)',
        'QUOTE_SYMBOL': r'^ *> ',
        'HR_LINE': r'^ *(?:(={4,})|(-{4,}))$',
        'BREAK_LINE': r' *↲',
        'STR_LINE': r'.+',
        'EMPTY_LINE': r'^$',
    }
    listblock_keys: Tuple[str, ...] = (
        'BULLET_LIST_SYMBOL',
        'ORDERED_LIST_SYMBOL',
        'DESC_LIST_SYMBOL',
        'CHECK_LIST_SYMBOL',
    )

    inline_deco_tokens: Dict[str, str] = {
        'EMPHASIS': r'⁒',
        'STRONG': r'⋄',
        'MARKED': r'‗',
        'STRIKE': r'¬',
        'VAR': r'⫶',
        'CODE': r'⸌',
        'SUP': r'⌃',
        'SUB': r'⌄',
        'TEXT': r'.*',
    }
    deco_keys: Tuple[str, ...] = tuple(inline_deco_tokens.keys())[:-1]

    inline_tokens: Dict[str, str] = {
        'ATTR': r'⁅([A-Za-z0-9_\-]+)⁆',
        'ROLE': r'¤([A-Za-z]+)(?:⟦([^⟧]*)⟧)?⸨([^⸩]*)⸩',
        'LINK': r'(?:⟦([^⟧]*)⟧)?⸨([^⸩]+)⸩',
        'FOOTNOTE': r'\[\^([\w\-.]+)\]',
        'REFERENCE': r'\[\#([\w\-.]+)\]',
        'BRACKET': r'\[[^\]]+\]',
    } | inline_deco_tokens

    def __init__(self):
        self._preproc_tokens: Dict[str, re.Pattern] = {
            k: re.compile(v) for k, v in self.preproc_tokens.items()
        }
        self._block_tokens: Dict[str, re.Pattern] = {
            k: re.compile(v) for k, v in self.block_tokens.items()
        }
        self._inline_deco_tokens: Dict[str, re.Pattern] = {
            k: re.compile(v) for k, v in self.inline_deco_tokens.items()
        }
        self._inline_tokens: Dict[str, re.Pattern] = {
            k: re.compile(v) for k, v in self.inline_tokens.items()
        }

    def lex_preproc(self, data: str) -> List[Lexer.Token]:
        return self.lex_pattern(self._preproc_tokens, data)

    def lex_block(self, data: str) -> List[Lexer.Token]:
        return self.lex_pattern(self._block_tokens, data)

    def lex_inline_deco(self, data: str, begin=1) -> List[Lexer.Token]:
        return self.lex_pattern(self._inline_deco_tokens, data, begin=begin)

    def lex_inline(self, data: str, begin=1) -> List[Lexer.Token]:
        return self.lex_pattern(self._inline_tokens, data, begin=begin)

    def lex_pattern(self, patterns, data: str, begin=0) -> List[Lexer.Token]:
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


class TglyphParser(Parser):
    def __init__(self, reader: Reader):
        super().__init__(reader)
        self.pplines: List[str] = list()
        self.rootnode: Optional[nd.DocumentNode] = None
        self.nodes: List[nd.ASTNode] = list()
        self.lexer: Lexer = Lexer()

        self.rootnode = nd.DocumentNode()
        self.nodes.append(self.rootnode)

    def parse(self, data: str) -> Optional[nd.DocumentNode]:
        ppdata = self.preprocess(data)
        try:
            self.tokens = self.lexer.lex_block(ppdata)
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
        return self.tokens[token.no + offset]

    def preprocess(self, data: str) -> str:
        self._init_config()
        try:
            tokens = self.lexer.lex_preproc(data)
        except ThothglyphError as e:
            lineno, line, rests = e.args
            lineno += 1
            msg = 'Unknown token.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        self.pplines = list()
        while tokens:
            if tokens[0].key == 'CONFIG_LINE':
                tokens = self.p_configblock(tokens)
            elif tokens[0].key == 'COMMENT':
                if tokens[0].pos == 0:
                    self._line_preprocessed()
                tokens.pop(0)
            elif tokens[0].key == 'CONTROL_FLOW':
                tokens = self.p_controlflow(tokens)
            else:
                self.pplines.append(tokens[0].value)
                tokens.pop(0)
        ppdata = '\n'.join(self.pplines)
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

    def _line_preprocessed(self):
        self.pplines.append('⑇')

    def p_configblock(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        config = self.rootnode.config
        begintoken = tokens[0]
        self._line_preprocessed()
        tokens.pop(0)
        subtokens = list()
        while tokens:
            if tokens[0].key == 'CONFIG_LINE':
                break
            self._line_preprocessed()
            subtokens.append(tokens.pop(0))
        else:
            lineno = begintoken.line + 1
            msg = 'Config block is not closed.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        self._line_preprocessed()
        tokens.pop(0)
        m = re.match(Lexer.inline_tokens['ROLE'], subtokens[0].value) if subtokens else None
        if m and m.group(1) == 'include':
            role = nd.RoleNode()
            role.role = m.group(1)
            role.opts = m.group(2).split(',') if m.group(2) is not None else ['']
            role.value = self.replace_text_attrs(m.group(3))
            text = nd.TextNode()
            self.nodes.append(text)
            self.p_plaininclude(subtokens, role)
            self.nodes.pop()
            config.parse(text.text)
        else:
            prev = begintoken
            text = str()
            for token in subtokens:
                if token.line != prev.line:
                    if prev.key != 'CONFIG_LINE':
                        text += '\n'
                    text += token.value[0:]
                else:
                    text += token.value
                prev = token
            text = self.replace_text_attrs(text)
            try:
                config.parse(text)
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
            self._line_preprocessed()
            tokens.pop(0)
            cond = eval(sentence, {}, self.rootnode.config.attrs)
            tokens = self.p_if_else(tokens, cond)
        else:
            lineno = tokens[0].line + 1
            msg = 'Illegal text token.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        return tokens

    def p_if_else(self, tokens: List[Lexer.Token], cond: bool) -> List[Lexer.Token]:
        while tokens:
            if tokens[0].key == 'TEXT' and cond:
                self.pplines.append(tokens[0].value)
            elif tokens[0].key == 'CONTROL_FLOW':
                match = re.match(Lexer.preproc_tokens['CONTROL_FLOW'], tokens[0].value)
                assert match
                keyword, sentence = match.group(1), match.group(2)
                if keyword == 'end':
                    break
                elif keyword == 'elif':
                    cond = not cond and eval(sentence, {}, self.rootnode.config.attrs)
                elif keyword == 'else':
                    cond = not cond
            self._line_preprocessed()
            tokens.pop(0)
        self._line_preprocessed()
        tokens.pop(0)
        return tokens

    def p_document(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        tokens = self.p_ignore_emptylines(tokens)
        tokens = self.p_blocks(tokens)
        tokens = self.p_ignore_emptylines(tokens)
        return tokens

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

    def p_blocks(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        while tokens:
            if tokens[0].key == 'BREAK_LINE':
                tokens.pop(0)
            elif tokens[0].key == 'BLOCKS_TERMINATOR':
                tokens.pop(0)
                break
            elif tokens[0].key == 'SECTION_TERMINATOR':
                tokens.pop(0)
                break
            else:
                tokens = self.p_block(tokens)
            tokens = self.p_ignore_emptylines(tokens)
        return tokens

    def p_block(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        if tokens[0].key == 'SECTION_TITLE_LINE':
            tokens = self.p_section(tokens)
        elif tokens[0].key == 'TOC_LINE':
            tokens = self.p_tocblock(tokens)
        elif tokens[0].key == 'FIGURE_LINE':
            tokens = self.p_figureblock(tokens)
        elif tokens[0].key == 'TABLE_LINE':
            tokens = self.p_basictableblock(tokens)
        elif tokens[0].key == 'LISTTABLE_BEGIN_LINE':
            tokens = self.p_listtableblock(tokens)
        elif tokens[0].key == 'FOOTNOTE_LIST_SYMBOL':
            tokens = self.p_monolistitem(tokens)
        elif tokens[0].key == 'REFERENCE_LIST_SYMBOL':
            tokens = self.p_monolistitem(tokens)
        elif tokens[0].key == 'LIST_TERMINATOR_SYMBOL':
            tokens = self.p_listitem(tokens)
        elif tokens[0].key == 'BULLET_LIST_SYMBOL':
            tokens = self.p_listitem(tokens)
        elif tokens[0].key == 'ORDERED_LIST_SYMBOL':
            tokens = self.p_listitem(tokens)
        elif tokens[0].key == 'DESC_LIST_SYMBOL':
            tokens = self.p_listitem(tokens)
        elif tokens[0].key == 'CHECK_LIST_SYMBOL':
            tokens = self.p_listitem(tokens)
        elif tokens[0].key == 'QUOTE_SYMBOL':
            tokens = self.p_quoteblock(tokens)
        elif tokens[0].key == 'CODE_LINE':
            tokens = self.p_codeblock(tokens)
        elif tokens[0].key == 'CUSTOM_LINE':
            tokens = self.p_customblock(tokens)
        elif tokens[0].key == 'STR_LINE':
            if len(tokens) >= 2 and tokens[1].key == 'HR_LINE':
                tokens = self.p_section(tokens)
            else:
                tokens = self.p_paragraph(tokens)
        elif tokens[0].key == 'HR_LINE':
            tokens = self.p_horizon(tokens)
        else:
            tokens.pop(0)
        return tokens

    def p_error(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        if tokens[0].key == 'CONFIG_LINE':
            lineno = tokens[0].line + 1
            msg = ''
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        return tokens

    def p_section(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        # terminate
        accepted = (nd.DocumentNode, nd.SectionNode)
        if not isinstance(self.nodes[-1], accepted):
            tokens.insert(0, Lexer.Token(-1, -1, -1, 'BLOCKS_TERMINATOR', ''))
            return tokens
        if tokens[0].key == 'SECTION_TITLE_LINE':
            m = re.match(Lexer.block_tokens['SECTION_TITLE_LINE'], tokens[0].value)
            assert m
            level = len(m.group(1))
        else:
            if tokens[1].value[-1] == '=':
                level = 1
            else:
                level = 2
        if self._lastsection.level >= level:
            tokens.insert(0, Lexer.Token(-1, -1, -1, 'SECTION_TERMINATOR', ''))
            return tokens

        if level > self._lastsection.level + 1:
            token = tokens[0]
            msg = 'Section level {} appears suddenly.'.format(level)
            msg += ' Section level must not be skipped.'
            lineno = token.line + 1
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        # body
        if tokens[0].key == 'SECTION_TITLE_LINE':
            assert m
            section = nd.SectionNode()
            section.level = len(m.group(1))
        else:
            ast_section_title_token = r'(^)(?:([*+]?) +)?([^⟦]+) *(?:⟦([^⟧]*)⟧)?'
            m = re.match(ast_section_title_token, tokens[0].value)
            assert m
            section = nd.SectionNode()
            if tokens[1].value[-1] == '=':
                section.level = 1
            else:
                section.level = 2
        section.level = level
        section.opts['nonum'] = (m.group(2) in ('*', '+'))
        section.opts['notoc'] = (m.group(2) == '*')
        section.title = self.replace_text_attrs(m.group(3))
        section.id = m.group(4) or ''
        if tokens[0].key == 'SECTION_TITLE_LINE':
            tokens.pop(0)
        else:
            tokens.pop(0)
            tokens.pop(0)
        self.nodes[-1].add(section)
        self.nodes.append(section)
        tokens = self.p_blocks(tokens)
        self.nodes.pop()
        return tokens

    def p_monolistitem(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        # terminate
        accepted = (nd.DocumentNode, nd.SectionNode)
        if not isinstance(self.nodes[-1], accepted):
            tokens.insert(0, Lexer.Token(-1, -1, -1, 'BLOCKS_TERMINATOR', ''))
            return tokens
        # body
        m = re.match(r' *•\[([\^#])(.+)\] +', tokens[0].value)
        assert m
        clstable = {'^': nd.FootnoteListBlockNode, '#': nd.ReferenceListBlockNode}
        children = self.nodes[-1].children
        if children and isinstance(children[-1], tuple(clstable.values())):
            monolist = self.nodes[-1].children[-1]
        else:
            monolist = clstable[m.group(1)]()
            self.nodes[-1].add(monolist)
        item = nd.ListItemNode()
        item.level = 1
        item.indent = 0
        item.title = m.group(2)
        monolist.add(item)
        tokens.pop(0)
        text = str()
        while tokens:
            if tokens[0].key != 'STR_LINE':
                break
            text += tokens[0].value
            tokens.pop(0)
        # item.add(text)
        text = self.replace_text_attrs(text)
        texttokens = self.lexer.lex_inline(text)
        self.nodes.append(item)
        self.p_inlinemarkup(texttokens)
        self.nodes.pop()
        return tokens

    def _get_listblock_by_token(self, token: Lexer.Token) -> List[nd.ListBlockNode]:
        table = {
            'BULLET_LIST_SYMBOL': nd.BulletListBlockNode,
            'ORDERED_LIST_SYMBOL': nd.OrderedListBlockNode,
            'DESC_LIST_SYMBOL': nd.DescriptionListBlockNode,
            'CHECK_LIST_SYMBOL': nd.CheckListBlockNode,
        }
        if token.key in table:
            listblock = table[token.key]()
            m = re.match(r' *([•꓾ᛝ]+)([^ ]*)( +|$)', token.value)
            assert m
            listblock.level = len(m.group(1))
            listblock.indent = len(m.group(0))
            return listblock
        lineno = token.line + 1
        msg = 'Not list symbol.'
        msg = f'{self.reader.path}:{lineno}: {msg}'
        raise ThothglyphError(msg)

    def p_listitem(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        # terminate
        table = {
            'BULLET_LIST_SYMBOL': nd.BulletListBlockNode,
            'ORDERED_LIST_SYMBOL': nd.OrderedListBlockNode,
            'DESC_LIST_SYMBOL': nd.DescriptionListBlockNode,
            'CHECK_LIST_SYMBOL': nd.CheckListBlockNode,
            'LIST_TERMINATOR_SYMBOL': object,
        }
        m = re.match(Lexer.block_tokens[tokens[0].key], tokens[0].value)
        assert m
        item = nd.ListItemNode()
        item.level = len(m.group(1))
        item.indent = len(m.group(0))
        item_type = table[tokens[0].key].__name__
        if tokens[0].key == 'DESC_LIST_SYMBOL':
            text = self.replace_text_attrs(m.group(2))
            if text[-1] == '◃':
                item.titlebreak = True
                text = text[:-1]
            texttokens = self.lexer.lex_inline(text)
            title = nd.TitleNode()
            item.add(title)
            self.nodes.append(title)
            self.p_inlinemarkup(texttokens)
            self.nodes.pop()
        elif tokens[0].key == 'CHECK_LIST_SYMBOL':
            checktext = m.group(2)[1]
            item.marker = checktext
        if isinstance(self.nodes[-1], nd.ListItemNode):
            item0 = self.nodes[-1]
            if item0.level >= item.level:
                tokens.insert(0, Lexer.Token(-1, -1, -1, 'BLOCKS_TERMINATOR', ''))
                return tokens
        # body
        if tokens[0].key == 'LIST_TERMINATOR_SYMBOL':
            tokens.pop(0)
            return tokens
        bros = self.nodes[-1].children
        if bros and isinstance(bros[-1], nd.ListBlockNode) and \
           item_type == bros[-1].__class__.__name__ and \
           self._tokens(tokens[0], -1).key != 'LIST_TERMINATOR_SYMBOL':
            listblock = self.nodes[-1].children[-1]
            assert listblock.children[-1].level == item.level
        else:
            if tokens[0].key == 'LIST_TERMINATOR_SYMBOL':
                tokens.pop(0)
                return tokens
            listblock = self._get_listblock_by_token(tokens[0])
            listblock.level = item.level
            listblock.indent = item.indent
            self.nodes[-1].add(listblock)
        listblock.add(item)

        self.nodes.append(item)
        tokens.pop(0)
        tokens = self.p_blocks(tokens)
        self.nodes.pop()
        return tokens

    def p_quoteblock(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        quote = nd.QuoteBlockNode()
        self.nodes[-1].add(quote)
        subtokens = list()
        prev = begintoken = tokens[0]
        prev = Lexer.Token(-1, -1, -1, 'DUMMY', '')
        text = str()
        while tokens:
            if tokens[0].line != prev.line:
                if tokens[0].key != 'QUOTE_SYMBOL':
                    break
            else:
                text += tokens[0].value
                subtokens.append(tokens[0])
            prev = tokens.pop(0)
        else:
            lineno = begintoken.line + 1
            msg = 'Quote block is not closed.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        subtokens.append(Lexer.Token(-1, -1, -1, 'BLOCKS_TERMINATOR', ''))
        self.nodes.append(quote)
        self.p_blocks(subtokens)
        self.nodes.pop()
        return tokens

    def _insert_linebreak(self, tokens: List[Lexer.Token]) -> None:
        for i in reversed(range(1, len(tokens))):
            prev = tokens[i - 1]
            token = tokens[i]
            if token.line != prev.line:
                lineno = prev.line
                pos = prev.pos + len(prev.value)
                tokens.insert(i, Lexer.Token(-1, lineno, pos, 'TEXT', '\n'))

    def p_codeblock(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        m = re.match(Lexer.block_tokens['CODE_LINE'], tokens[0].value)
        assert m
        indent = tokens[0].pos + len(m.group(1))
        code = nd.CodeBlockNode()
        code.lang = m.group(2)
        self.nodes[-1].add(code)
        begintoken = tokens[0]
        tokens.pop(0)
        subtokens = list()
        while tokens:
            if tokens[0].key == 'CODE_LINE':
                break
            subtokens.append(tokens.pop(0))
        else:
            lineno = begintoken.line + 1
            msg = 'Code block is not closed.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        tokens.pop(0)
        m = re.match(Lexer.inline_tokens['ROLE'], subtokens[0].value) if subtokens else None
        if m and m.group(1) == 'include':
            role = nd.RoleNode()
            role.role = m.group(1)
            role.opts = m.group(2).split(',') if m.group(2) is not None else ['']
            role.value = self.replace_text_attrs(m.group(3))
            self.nodes.append(code)
            self.p_plaininclude(subtokens, role)
            self.nodes.pop()
        else:
            text = str()
            prev = begintoken
            warned = False
            for token in subtokens:
                if token.line != prev.line:
                    if prev.key != 'CODE_LINE':
                        text += '\n'
                    numspace = re.match(r' *', token.value).end()
                    if numspace < indent and not warned:
                        msg = 'Code indentation is to the left of the block indentation.'
                        lineno = token.line + 1
                        msg = f'{self.reader.path}:{lineno}: {msg}'
                        logger.warn(msg)
                        warned = True
                    text += token.value[indent:]
                else:
                    text += token.value
                prev = token
            text = self.replace_text_attrs(text)
            texttokens = self.lexer.lex_inline_deco(text, begin=begintoken.line)
            self._insert_linebreak(texttokens)
            self.nodes.append(code)
            self.p_decotext(texttokens)
            self.nodes.pop()
        return tokens

    def p_customblock(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        m = re.match(Lexer.block_tokens['CUSTOM_LINE'], tokens[0].value)
        assert m
        indent = tokens[0].pos + len(m.group(1))
        custom = nd.CustomBlockNode()
        custom.ext = m.group(2)
        self.nodes[-1].add(custom)
        begintoken = tokens[0]
        tokens.pop(0)
        subtokens = list()
        while tokens:
            if tokens[0].key == 'CUSTOM_LINE':
                break
            subtokens.append(tokens.pop(0))
        else:
            lineno = begintoken.line + 1
            msg = 'Custom block is not closed.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        tokens.pop(0)
        m = re.match(Lexer.inline_tokens['ROLE'], subtokens[0].value) if subtokens else None
        if m and m.group(1) == 'include':
            role = nd.RoleNode()
            role.role = m.group(1)
            role.opts = m.group(2).split(',') if m.group(2) is not None else ['']
            role.value = self.replace_text_attrs(m.group(3))
            self.nodes.append(custom)
            self.p_plaininclude(subtokens, role)
            self.nodes.pop()
        else:
            prev = begintoken
            text = str()
            warned = False
            for token in subtokens:
                if token.line != prev.line:
                    if prev.key != 'CUSTOM_LINE':
                        text += '\n'
                    numspace = re.match(r' *', token.value).end()
                    if numspace < indent and not warned:
                        msg = 'Code indentation is to the left of the block indentation.'
                        lineno = token.line + 1
                        msg = f'{self.reader.path}:{lineno}: {msg}'
                        warned = True
                    text += token.value[indent:]
                else:
                    text += token.value
                prev = token
            text = self.replace_text_attrs(text)
            custom.text = text
        return tokens

    def p_horizon(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        tokens.pop(0)
        horizon = nd.HorizonBlockNode()
        self.nodes[-1].add(horizon)
        return tokens

    def p_tocblock(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        m = re.match(Lexer.block_tokens['TOC_LINE'], tokens[0].value)
        assert m
        toc = nd.TocBlockNode()
        toc.opts = nd.parse_optargs(m.group(1))
        toc.value = m.group(2)
        self.nodes[-1].add(toc)
        tokens.pop(0)
        return tokens

    def p_figureblock(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        m = re.match(Lexer.block_tokens['FIGURE_LINE'], tokens[0].value)
        assert m
        fig = nd.FigureBlockNode()
        fig.opts = m.group(1).split(',') if m.group(1) is not None else ['']
        fig.caption = self.replace_text_attrs(m.group(2))
        self.nodes[-1].add(fig)
        tokens.pop(0)
        self.nodes.append(fig)
        tokens = self.p_block(tokens)
        self.nodes.pop()
        return tokens

    def _extract_tablecell_merge_hmarker(self, text: str):
        if text.startswith('⏴'):
            return '⏴'
        return ''

    def _extract_tablecell_merge_vmarker(self, text: str):
        if text.startswith('⏶'):
            return '⏶'
        return ''

    def p_basictableblock(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        table = nd.TableBlockNode()
        self.nodes[-1].add(table)
        lines = list()
        begintoken = tokens[0]
        while tokens:
            if tokens[0].key != 'TABLE_LINE':
                break
            lines.append(tokens[0].value)
            tokens.pop(0)
        tabletexts = list()
        aligns = list()
        header_splitter = -1
        for i, line in enumerate(lines):
            rowtexts = re.split(r' *\| *', line.strip())[1:-1]
            ms = [re.match(r'^[+:]?-+[+:]?$', c) for c in rowtexts]
            if all(ms) and header_splitter == -1:
                for m in ms:
                    assert m
                    mg = m.group(0)
                    if mg[0] == mg[-1] == ':':
                        aligns.append('c')
                    elif mg[-1] == ':':
                        aligns.append('r')
                    elif mg[0] == '+':
                        aligns.append('x')
                    else:
                        aligns.append('l')
                header_splitter = i
            else:
                tabletexts.append(rowtexts)
        if header_splitter < 0:
            header_splitter = 0
        # table.type = opts.get('type', 'normal')
        table.row = len(tabletexts)
        table.col = len(tabletexts[0])
        table.headers = header_splitter
        if len(aligns) == 0:
            aligns = ['c' for i in range(table.col)]
        table.aligns = aligns
        for r, rowtexts in enumerate(tabletexts):
            row = nd.TableRowNode()
            row.idx = r
            if r < table.headers:
                row.tp = 'header'
            table.add(row)
            if len(rowtexts) != table.col or len(table.aligns) != table.col:
                lineno = begintoken.line + 1 + r
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
                text = self.replace_text_attrs(celltext)
                text = self._tablecell_merge(table, cell, r, c, text)
                try:
                    texttokens = self.lexer.lex_inline(text)
                    self.nodes.append(cell)
                    self.p_inlinemarkup(texttokens)
                    self.nodes.pop()
                except Exception:
                    cell.add(nd.TextNode(text))
        return tokens

    def p_listtableblock(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        m = re.match(Lexer.block_tokens['LISTTABLE_BEGIN_LINE'], tokens[0].value)
        assert m
        opts = nd.parse_optargs(m.group(1))
        begintoken = tokens[0]
        tokens.pop(0)
        nested = 1
        subtokens = list()
        while tokens:
            if tokens[0].key == 'LISTTABLE_BEGIN_LINE':
                nested += 1
            if tokens[0].key == 'LISTTABLE_END_LINE':
                nested -= 1
                if nested == 0:
                    break
            subtokens.append(tokens.pop(0))
        tokens.pop(0)
        table = nd.TableBlockNode()
        self.nodes[-1].add(table)
        self.nodes.append(table)
        self.p_blocks(subtokens)
        self.nodes.pop()
        if len(table.children) == 1:
            header_rowlist = nd.BulletListBlockNode()
            data_rowlist = table.children[0]
        else:
            header_rowlist = table.children[0]
            data_rowlist = table.children[1]
        rowitems = header_rowlist.children + data_rowlist.children
        if not all([
            isinstance(header_rowlist, nd.BulletListBlockNode),
            isinstance(data_rowlist, nd.BulletListBlockNode),
        ] + [
            len(item.children) == 1 and isinstance(item.children[0], nd.BulletListBlockNode)
            for item in rowitems
        ] + [
            len(item.children[0].children) == len(rowitems[0].children[0].children)
            for item in rowitems
        ]):
            # print(
            #     isinstance(header_rowlist, nd.BulletListBlockNode),
            #     isinstance(data_rowlist, nd.BulletListBlockNode),
            #     len(rowitems) <= 2, len(rowitems),
            # )
            lineno = begintoken.line + 1
            msg = 'ListTable data must be two-dimensional BulletList.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        for node in table.children[:]:
            table.remove(node)
        table.type = opts.get('type', 'normal')
        table.aligns = ['l' for i in range(len(rowitems[0].children[0].children))]
        for i, align in enumerate(opts.get('align', '')):
            table.aligns[i] = align
        table.row = len(rowitems)
        table.col = len(rowitems[0].children[0].children)
        table.headers = len(header_rowlist.children)
        for r, rowitem in enumerate(rowitems):
            row = nd.TableRowNode()
            row.idx = r
            if r < table.headers:
                row.tp = 'header'
            table.add(row)
            collist = rowitem.children[0]
            for c, citem in enumerate(collist.children):
                cell = nd.TableCellNode()
                for node in citem.children[:]:
                    citem.remove(node)
                    cell.add(node)
                row.add(cell)
                cell.idx = c
                cell.align = table.aligns[c]
                if not (all([
                    cell.children,
                    isinstance(cell.children[0], nd.ParagraphNode),
                    cell.children[0].children,
                    isinstance(cell.children[0].children[0], nd.TextNode),
                ])):
                    continue
                text = cell.children[0].children[0].text
                text = self._tablecell_merge(table, cell, r, c, text)
                cell.children[0].children[0].text = text
        return tokens

    def p_paragraph(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        paragraph = nd.ParagraphNode()
        self.nodes[-1].add(paragraph)
        text = str()
        prev = begintoken = tokens[0]
        while tokens:
            if tokens[0].key != 'STR_LINE':
                break
            if tokens[0].line != prev.line:
                text += '\n'
                text += tokens[0].value
            else:
                text += tokens[0].value
            prev = tokens.pop(0)
        text = self.replace_text_attrs(text)
        texttokens = self.lexer.lex_inline(text, begintoken.line)
        self.nodes.append(paragraph)
        self.p_inlinemarkup(texttokens)
        self.nodes.pop()
        return tokens

    def p_inlinemarkup(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        while tokens:
            if tokens[0].key == 'ROLE':
                tokens = self.p_role(tokens)
            elif tokens[0].key == 'LINK':
                tokens = self.p_link(tokens)
            elif tokens[0].key == 'FOOTNOTE':
                tokens = self.p_footnote(tokens)
            elif tokens[0].key == 'REFERENCE':
                tokens = self.p_reference(tokens)
            elif tokens[0].key in Lexer.deco_keys:
                tokens = self.p_deco(tokens)
            else:
                tokens = self.p_text(tokens)
        return tokens

    def p_role(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        m = re.match(Lexer.inline_tokens['ROLE'], tokens[0].value)
        assert m
        role = nd.RoleNode()
        role.role = m.group(1)
        role.opts = m.group(2) if m.group(2) is not None else ''
        role.value = self.replace_text_attrs(m.group(3))
        if role.role == 'image':
            tokens = self.p_image(tokens, role)
        elif role.role == 'include':
            tokens = self.p_include(tokens, role)
        elif role.role == 'kbd':
            tokens = self.p_kbd(tokens, role)
        elif role.role == 'btn':
            tokens = self.p_btn(tokens, role)
        elif role.role == 'menu':
            tokens = self.p_menu(tokens, role)
        else:
            self.nodes[-1].add(role)
            tokens.pop(0)
        return tokens

    def p_image(self, tokens: List[Lexer.Token], role: nd.RoleNode) -> List[Lexer.Token]:
        image = nd.ImageRoleNode()
        image.role = role.role
        image.opts = nd.parse_optargs(role.opts)
        image.value = role.value
        self.nodes[-1].add(image)
        tokens.pop(0)
        return tokens

    def p_plaininclude(self, tokens: List[Lexer.Token], role: nd.RoleNode) -> List[Lexer.Token]:
        tokens.pop(0)
        path = role.value
        block = self.nodes[-1]
        if os.path.exists(path) and hasattr(block, 'text'):
            text = nd.TextNode()
            with open(path, 'r', encoding=self.reader.encoding) as f:
                text.text = f.read().rstrip()
            block.text = text.text
        elif os.path.exists(path) and isinstance(block, nd.CodeBlockNode):
            text = nd.TextNode()
            with open(path, 'r', encoding=self.reader.encoding) as f:
                text.text = f.read().rstrip()
            block.add(text)
        else:
            logger.warn('Include file cannot found: {}'.format(path))
            text = nd.TextNode(role.value)
            block.add(text)
        return tokens

    def p_include(self, tokens: List[Lexer.Token], role: nd.RoleNode) -> List[Lexer.Token]:
        tokens.pop(0)
        path = role.value
        if self._check_recursive_include(path):
            _, ext = os.path.splitext(path)
            reader: Reader = ReaderClass(ext[1:])(parent=self.reader)
            # reader: Reader = TglyphReader(parent=self.reader)
            subdoc = reader.read(path)
            lastsection = self._lastsection
            for node, gofoward in subdoc.walk_depth():
                if not gofoward:
                    continue
                if isinstance(node, nd.SectionNode):
                    node.level += lastsection.level
            p = self.nodes[-1]
            block = p.parent
            if len(p.children) == 0:
                for node in subdoc.children:
                    block.add(node)
                block.remove(p)
        return tokens

    def p_kbd(self, tokens: List[Lexer.Token], role: nd.RoleNode) -> List[Lexer.Token]:
        kbd = nd.KbdRoleNode()
        kbd.role = role.role
        kbd.opts = role.opts
        kbd.value = role.value.strip().split()
        self.nodes[-1].add(kbd)
        tokens.pop(0)
        return tokens

    def p_btn(self, tokens: List[Lexer.Token], role: nd.RoleNode) -> List[Lexer.Token]:
        btn = nd.BtnRoleNode()
        btn.role = role.role
        btn.opts = role.opts
        btn.value = role.value
        self.nodes[-1].add(btn)
        tokens.pop(0)
        return tokens

    def p_menu(self, tokens: List[Lexer.Token], role: nd.RoleNode) -> List[Lexer.Token]:
        menu = nd.MenuRoleNode()
        menu.role = role.role
        menu.opts = role.opts
        menu.value = re.split(r' +\> +', role.value.strip())
        self.nodes[-1].add(menu)
        tokens.pop(0)
        return tokens

    def p_link(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        m = re.match(Lexer.inline_tokens['LINK'], tokens[0].value)
        assert m
        link = nd.LinkNode()
        link.opts = m.group(1).split(',') if m.group(1) is not None else ['']
        link.value = self.replace_text_attrs(m.group(2))
        self.nodes[-1].add(link)
        tokens.pop(0)
        return tokens

    def p_footnote(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        m = re.match(Lexer.inline_tokens['FOOTNOTE'], tokens[0].value)
        assert m
        link = nd.FootnoteNode()
        link.value = m.group(1)
        self.nodes[-1].add(link)
        tokens.pop(0)
        return tokens

    def p_reference(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        m = re.match(Lexer.inline_tokens['REFERENCE'], tokens[0].value)
        assert m
        link = nd.ReferenceNode()
        link.value = m.group(1)
        self.nodes[-1].add(link)
        tokens.pop(0)
        return tokens

    def p_decotext(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        while tokens:
            if tokens[0].key in Lexer.deco_keys:
                tokens = self.p_deco(tokens)
            elif tokens[0].key == 'TEXT':
                tokens = self.p_text(tokens)
            elif tokens[0].key == 'ATTR':
                tokens = self.p_text(tokens)
            else:
                lineno = tokens[0].line + 1
                msg = 'Illegal text token.'
                msg = f'{self.reader.path}:{lineno}: {msg}'
                raise ThothglyphError(msg)
        return tokens

    def p_deco(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        deco = nd.DecorationRoleNode()
        deco.role = tokens[0].key
        begintoken = tokens[0]
        tokens.pop(0)
        self.nodes[-1].add(deco)
        self.nodes.append(deco)
        subtokens = list()
        while tokens:
            if tokens[0].key == deco.role:
                break
            subtokens.append(tokens[0])
            tokens.pop(0)
        else:
            lineno = begintoken.line + 1
            msg = f'Inline {deco.role} is not closed.'
            msg = f'{self.reader.path}:{lineno}: {msg}'
            raise ThothglyphError(msg)
        tokens.pop(0)
        self.p_decotext(subtokens)
        self.nodes.pop()
        return tokens

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
            Lexer.inline_tokens['ATTR'], attrvalue, text,
            flags=re.MULTILINE | re.DOTALL
        )
        return newtext

    def p_text(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        if len(self.nodes[-1].children) == 0:
            text = nd.TextNode()
            self.nodes[-1].add(text)
            text.text += tokens[0].value
        elif not isinstance(self.nodes[-1].children[-1], nd.TextNode):
            text = nd.TextNode()
            self.nodes[-1].add(text)
            text.text += tokens[0].value
        else:
            text = self.nodes[-1].children[-1]
            text.text += '' + tokens[0].value
        tokens.pop(0)
        return tokens

    def p_ignore_emptylines(self, tokens: List[Lexer.Token]) -> List[Lexer.Token]:
        while tokens and tokens[0].key == 'EMPTY_LINE':
            tokens.pop(0)
        return tokens


class TglyphReader(Reader):
    target = 'tglyph'
    ext = 'pdf'

    def __init__(self, parent: Optional[Reader] = None):
        super().__init__(parent=parent)
        self.parser: TglyphParser = TglyphParser(self)

    def read(self, path: str, encoding: Optional[str] = None) -> nd.ASTNode:
        try:
            return super().read(path, encoding)
        except Exception as e:
            _, errormsg = e.args
            msg = 'File cannot found: {}'.format(e.filename)
            raise ThothglyphError(msg)
