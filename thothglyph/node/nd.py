from __future__ import annotations
from typing import Any, Callable, Dict, Generator, Iterator, List, Optional, Tuple
import re
import subprocess
import types
from thothglyph.node import logging

logger = logging.getLogger(__file__)


class ASTNode():
    attrkey: Tuple[str, ...] = tuple()

    def __init__(self):
        self.parent: Optional[ASTNode] = None
        self.children: List[ASTNode] = list()
        self.id: str = str()

    def __str__(self):
        cls: str = self.__class__.__name__
        kv: Dict[str, str] = {k: getattr(self, k) for k in self.attrkey}
        attrs: str = ', '.join(['{}:"{}"'.format(k, v) for k, v in kv.items()])
        s: str = '{}({})'.format(cls, attrs)
        return s

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def root(self) -> DocumentNode:
        node: ASTNode = self
        while node.parent is not None:
            node = node.parent
        if not isinstance(node, DocumentNode):
            msg = 'root node is not a DocumentNode'
            logger.error(msg)
            raise Exception(msg)
        return node

    def add(self, node):
        node.parent = self
        self.children.append(node)

    def remove(self, node):
        node.parent = None
        self.children.remove(node)

    def walk_depth(self) -> Generator[Tuple[ASTNode, bool], None, None]:
        def _walk(node: ASTNode, visited: List[ASTNode]):
            visited += [node]
            yield node, True  # go foward
            for child in node.children:
                if child not in visited:
                    for _ in _walk(child, visited): yield _  # noqa
            yield node, False  # go back

        yield self, True  # go foward
        if len(self.children) > 0:
            rest: List[ASTNode] = self.children[:]
            visited: List[ASTNode] = []
            while len(rest) > 0:
                first = rest[0]
                for _ in _walk(first, visited): yield _  # noqa
                for n in visited:
                    if n in rest:
                        rest.remove(n)
        yield self, False  # go back

    def lastnode(self, cond: Optional[Callable[[ASTNode], bool]] = None) -> Optional[ASTNode]:
        def default_cond(n: ASTNode):
            return True

        cond = default_cond if cond is None else cond
        node: Optional[ASTNode] = self
        while node:
            children: List[ASTNode] = [n for n in node.children if cond(n)]
            if not children:
                break
            node = children[-1]
        return node

    def _parent_section(self) -> Optional[SectionNode]:
        node = self.parent
        while node and not isinstance(node, SectionNode):
            node = node.parent
        if isinstance(node, SectionNode):
            return node
        return None

    def _parent_table(self) -> Optional[TableBlockNode]:
        node = self.parent
        while node and not isinstance(node, TableBlockNode):
            node = node.parent
        if isinstance(node, TableBlockNode):
            return node
        return None

    def treeindex(self) -> List[int]:
        if self.parent is None:
            return [0]
        return self.parent.treeindex() + [self.parent.children.index(self)]

    def treeid(self) -> str:
        return '-'.join([str(i) for i in self.treeindex()])


class DocumentNode(ASTNode):
    attrkey = ('config', )

    def __init__(self):
        super().__init__()
        self.level: int = 0
        self.config: ConfigNode = ConfigNode()


class ConfigNode(ASTNode):
    def __init__(self):
        super().__init__()
        self.title: str = 'Document Title'
        self.version: str = str()
        self.author: str = str()
        self.attrs: Dict[str, str] = dict()

    @property
    def docdata_params(self):
        params = dict(self.__dict__.items())
        ignores = ('parent', 'children', 'id', 'attrs')
        for i in ignores:
            params.pop(i)
        return params

    def parse(self, text: str) -> None:
        exec(text)
        params: Dict[str, Any] = locals()
        for param in list(params.keys()):
            if isinstance((params[param]), type):
                params.pop(param)
            elif isinstance((params[param]), types.ModuleType):
                params.pop(param)
        for key in ('self', 'text'):
            if key in params:
                params.pop(key)
        for key in params:
            value: Any = params[key]
            if key == 'attrs':
                self.attrs.update(value)
            else:
                setattr(self, key, value)


class SectionNode(ASTNode):
    attrkey = ('level', 'title', 'opts')

    def __init__(self):
        super().__init__()
        self.level: int = 0
        self.title: str = str()
        self.opts: Dict[str, Any] = dict()
        self._sectindex: List[int] = list()

    def sectindex(self) -> List[int]:
        return self._sectindex

    @property
    def sectnum(self) -> str:
        sectnums: List[str] = [str(i + 1) for i in self.sectindex()]
        sectnum: str = '.'.join(sectnums)
        return sectnum


class BlockNode(ASTNode):
    def __init__(self):
        super().__init__()


class TocBlockNode(BlockNode):
    def __init__(self):
        super().__init__()

    def walk_sections(self) -> Generator[Tuple[ASTNode, bool], None, None]:
        for n, gofoward in self.root.walk_depth():
            if isinstance(n, SectionNode):
                yield n, gofoward


class ListBlockNode(BlockNode):
    attrkey = ('level', 'indent')

    def __init__(self):
        super().__init__()
        self.level: int = -1
        self.indent: int = -1


class BulletListBlockNode(ListBlockNode):
    def __init__(self):
        super().__init__()


class OrderedListBlockNode(ListBlockNode):
    def __init__(self):
        super().__init__()


class DescriptionListBlockNode(ListBlockNode):
    def __init__(self):
        super().__init__()

    @property
    def titlebreak(self):
        if len(self.children) == 0:
            return False
        for child in self.children:
            if hasattr(child, 'titlebreak') and child.titlebreak:
                return True
        return False


class CheckListBlockNode(ListBlockNode):
    def __init__(self):
        super().__init__()


class ListItemNode(ASTNode):
    def __init__(self):
        super().__init__()
        self.options: Dict[str, Any] = dict()
        self.title: Any = None
        self.titlebreak: bool = False


class FootnoteListBlockNode(BlockNode):
    def __init__(self):
        super().__init__()


class ReferenceListBlockNode(BlockNode):
    def __init__(self):
        super().__init__()


class FigureBlockNode(BlockNode):
    def __init__(self):
        super().__init__()
        self.caption: str = str()
        self.align: str = 'l'

    def _fignum_format(self, gindex: int, lindex: List[int]) -> str:
        def default_figure_fignum_format(gindex: int, lindex: List[int]) -> str:
            return 'Figure {}.'.format(gindex)

        def default_table_fignum_format(gindex: int, lindex: List[int]) -> str:
            return 'Table {}.'.format(gindex)

        if isinstance(self.children[0], TableBlockNode):
            if hasattr(self.root.config, 'table_fignum_format'):
                fmt = getattr(self.root.config, 'table_fignum_format')
                return fmt(gindex, lindex)
            return default_table_fignum_format(gindex, lindex)
        else:
            if hasattr(self.root.config, 'figure_fignum_format'):
                fmt = getattr(self.root.config, 'figure_fignum_format')
                return fmt(gindex, lindex)
            return default_figure_fignum_format(gindex, lindex)

    @property
    def fignum(self) -> str:
        gindex: int = 1
        if isinstance(self.children[0], TableBlockNode):
            for n, gofoward in self.root.walk_depth():
                if not gofoward:
                    continue
                if isinstance(n, FigureBlockNode) and isinstance(n.children[0], TableBlockNode):
                    if n == self:
                        break
                    gindex += 1
        else:
            for n, gofoward in self.root.walk_depth():
                if not gofoward:
                    continue
                if isinstance(n, FigureBlockNode):
                    if n == self:
                        break
                    gindex += 1
        section: Optional[SectionNode] = self._parent_section()
        if section is None:
            msg: str = 'The figure is not into any sections'
            logger.error(msg)
            raise Exception(msg)
        lindex: int = 1
        if isinstance(self.children[0], TableBlockNode):
            for n, gofoward in self.root.walk_depth():
                if not gofoward:
                    continue
                if isinstance(n, FigureBlockNode) and isinstance(n.children[0], TableBlockNode):
                    if n == self:
                        break
                    lindex += 1
        else:
            for n, gofoward in self.root.walk_depth():
                if not gofoward:
                    continue
                if isinstance(n, FigureBlockNode):
                    if n == self:
                        break
                    lindex += 1
        lindexs: List[int] = section.sectindex() + [lindex]
        return self._fignum_format(gindex, lindexs)


class TableBlockNode(BlockNode):
    attrkey = ('row', 'col', 'headers')

    def __init__(self):
        super().__init__()
        self.type: str = 'normal'  # 'normal', 'long'
        self.row: int = 0
        self.col: int = 0
        self.headers: int = 0
        self.caption: Optional[str] = None
        self.align: str = 'l'  # table align
        self.aligns: List[str] = list()  # column alings

    def cell(self, row: int, col: int) -> ASTNode:
        return self.children[row].children[col]

    def cells(self) -> Iterator:
        for row in self.children:
            for cell in row.children:
                yield cell

    def _fignum_format(self, gindex: int, lindex: List[int]) -> str:
        def default_fignum_format(gindex: int, lindex: List[int]) -> str:
            return 'Table {}.'.format(gindex)

        if hasattr(self.root.config, 'table_fignum_format'):
            fmt = getattr(self.root.config, 'table_fignum_format')
            return fmt(gindex, lindex)
        return default_fignum_format(gindex, lindex)

    @property
    def fignum(self) -> str:
        gindex: int = 1
        for n, gofoward in self.root.walk_depth():
            if gofoward:
                if isinstance(n, TableBlockNode) and n.caption is not None:
                    if n == self:
                        break
                    gindex += 1
        section: Optional[SectionNode] = self._parent_section()
        if section is None:
            msg: str = 'The figure is not into any sections'
            logger.error(msg)
            raise Exception(msg)
        lindex: int = 1
        for n, gofoward in section.walk_depth():
            if gofoward:
                if isinstance(n, TableBlockNode) and n.caption is not None:
                    if n == self:
                        break
                    lindex += 1
        lindexs: List[int] = section.sectindex() + [lindex]
        return self._fignum_format(gindex, lindexs)


class TableRowNode(ASTNode):
    def __init__(self):
        super().__init__()
        self.tp: str = 'data'  # 'header', 'data'
        self.idx: int = -1


class TableCellNode(ASTNode):
    class Size():
        def __init__(self, x: int, y: int):
            self.x: int = x
            self.y: int = y

    def __init__(self):
        super().__init__()
        self.idx: int = -1
        self.align: str = 'c'
        self.mergeto: Optional[TableCellNode] = None
        self.size: TableCellNode.Size = TableCellNode.Size(1, 1)


class LiteralBlockNode(BlockNode):
    def __init__(self):
        super().__init__()


class QuoteBlockNode(BlockNode):
    def __init__(self):
        super().__init__()


class CodeBlockNode(BlockNode):
    attrkey = ('lang',)

    def __init__(self):
        super().__init__()
        self.lang: str = str()


class CustomBlockNode(BlockNode):
    attrkey = ('ext',)

    def __init__(self):
        super().__init__()
        self.ext: str = str()
        self.text: str = str()


class HorizonBlockNode(BlockNode):
    def __init__(self):
        super().__init__()


class ParagraphNode(BlockNode):
    def __init__(self):
        super().__init__()


class TitleNode(ParagraphNode):
    def __init__(self):
        super().__init__()


class InlineNode(ASTNode):
    def __init__(self):
        super().__init__()

    @property
    def parent_block(self):
        p = self.parent
        while p:
            if isinstance(p, BlockNode):
                break
            p = p.parent
        return p


class TextNode(InlineNode):
    attrkey = ('text',)

    def __init__(self, text: Optional[str] = None):
        super().__init__()
        self.text: str = str() if text is None else text


class RoleNode(InlineNode):
    attrkey = ('role', 'args', 'opts', 'value')

    def __init__(self, role=None, args=None, opts=None, value=None):
        super().__init__()
        self.role: str = str() if role is None else role
        self.args: Any = list() if args is None else args
        self.opts: Any = list() if opts is None else opts
        self.value: str = str() if value is None else value


class DecorationRoleNode(RoleNode):
    def __init__(self):
        super().__init__()


class ImageRoleNode(RoleNode):
    def __init__(self):
        super().__init__()


class IncludeRoleNode(RoleNode):
    def __init__(self):
        super().__init__()


class KbdRoleNode(RoleNode):
    def __init__(self):
        super().__init__()


class BtnRoleNode(RoleNode):
    def __init__(self):
        super().__init__()


class MenuRoleNode(RoleNode):
    def __init__(self):
        super().__init__()


class LinkNode(InlineNode):
    attrkey = ('opts', 'value')

    def __init__(self, opts=None, value=None):
        super().__init__()
        self.opts: Any = list() if opts is None else opts
        self.value: str = str() if value is None else value

    @property
    def target_id(self) -> str:
        root: ASTNode = self.root
        # find by id
        for n, gofoward in root.walk_depth():
            if gofoward and isinstance(n, SectionNode):
                if n.id == self.value:
                    return n.id
        return self.value.replace(' ', '_')

    @property
    def target_title(self) -> str:
        root: ASTNode = self.root
        # find by id
        for n, gofoward in root.walk_depth():
            if gofoward and isinstance(n, SectionNode):
                if n.id == self.value:
                    # title = '{}. {}'.format(n.sectnum, n.title)
                    return n.title
        # find by title
        for n, gofoward in root.walk_depth():
            if gofoward and isinstance(n, SectionNode):
                if n.title == self.value:
                    # title = '{}. {}'.format(n.sectnum, n.title)
                    return n.title
        return self.value


class FootnoteNode(InlineNode):
    attrkey = ('value',)

    def __init__(self, value: Optional[str] = None):
        super().__init__()
        self.value: str = str() if value is None else value
        self._description = None

    @property
    def description(self) -> ListItemNode:
        if self._description:
            return self._description
        msg: str = 'Footnote not found: {}'.format(self.value)
        logger.error(msg)
        item: ListItemNode = ListItemNode()
        return item


class ReferenceNode(InlineNode):
    attrkey = ('value',)

    def __init__(self, value=None):
        super().__init__()
        self.value: str = str() if value is None else value


def parse_optargs(argstr: str) -> Dict[str, str]:
    tstr: str = argstr[:] if argstr else ''
    opts: Dict[str, str] = dict()
    while tstr:
        m = re.match(r'^(?: *([0-9a-z_\-]+)="([^"]*)") *', tstr)
        if m:
            opts[m.group(1)] = m.group(2)
        else:
            raise Exception('option parse error: [{}]'.format(argstr))
        tstr = tstr[len(m.group(0)):]
    return opts


def parse_funcargs(argstr) -> List[Any]:
    def f(*args, **kwargs):
        return args, kwargs

    exec('args = f({})'.format(argstr))
    params: Dict[str, Any] = locals()
    return params['args']


def nodeprint(node) -> None:
    depth: int = 0
    for n, gofoward in node.walk_depth():
        if gofoward:
            indent: str = '  ' * depth
            logger.debug('{}{}'.format(indent, n))
            depth += 1
        else:
            depth -= 1


def cmd(cmdstr) -> str:
    p = subprocess.run(cmdstr.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.stderr:
        logger.error(p.stderr.decode())
    out: str = p.stdout.decode()
    return out
