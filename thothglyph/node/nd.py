import re
import subprocess
import types

from thothglyph.node import logging

logger = logging.getLogger(__file__)


class ASTNode():
    attrkey = ()

    def __init__(self):
        self.parent = None
        self.children = list()
        self.id = str()

    def __str__(self):
        cls = self.__class__.__name__
        kv = {k: getattr(self, k) for k in self.attrkey}
        attrs = ', '.join(['{}:"{}"'.format(k, v) for k, v in kv.items()])
        s = '{}({})'.format(cls, attrs)
        return s

    def __repr__(self):
        return self.__str__()

    @property
    def root(self):
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    def add(self, node):
        node.parent = self
        self.children.append(node)

    def remove(self, node):
        node.parent = None
        self.children.remove(node)

    def walk_depth(self):
        def _walk(node, visited):
            visited += [node]
            yield node, True  # go foward
            for child in node.children:
                if child not in visited:
                    for _ in _walk(child, visited): yield _  # noqa
            yield node, False  # go back

        yield self, True  # go foward
        if len(self.children) > 0:
            rest = self.children[:]
            visited = []
            while len(rest) > 0:
                first = rest[0]
                for _ in _walk(first, visited): yield _  # noqa
                for n in visited:
                    if n in rest:
                        rest.remove(n)
        yield self, False  # go back

    def lastnode(self, cond=None):
        def default_cond(n):
            return True

        cond = default_cond if cond is None else cond
        node = self
        while node:
            children = [n for n in node.children if cond(n)]
            if not children:
                break
            node = children[-1]
        return node

    def _parent_section(self):
        node = self
        while not isinstance(node, SectionNode):
            node = node.parent
        return node

    def _parent_table(self):
        node = self
        while node and not isinstance(node, TableBlockNode):
            node = node.parent
        return node

    def treeindex(self):
        if self.parent is None:
            return [0]
        return self.parent.treeindex() + [self.parent.children.index(self)]

    def treeid(self):
        return '-'.join([str(i) for i in self.treeindex()])


class DocumentNode(ASTNode):
    attrkey = ('config', )

    def __init__(self):
        super().__init__()
        self.level = 0
        self.config = ConfigNode()


class ConfigNode(ASTNode):
    def __init__(self):
        super().__init__()
        self.title = 'Document Title'
        self.version = str()
        self.author = str()
        self.attrs = dict()

    def parse(self, text):
        exec(text)
        params = locals()
        for param in list(params.keys()):
            if isinstance((params[param]), type):
                params.pop(param)
            elif isinstance((params[param]), types.ModuleType):
                params.pop(param)
        for key in ('self', 'text'):
            if key in params:
                params.pop(key)
        for key in params:
            value = params[key]
            if key == 'attrs':
                self.attrs.update(value)
            else:
                setattr(self, key, value)


class SectionNode(ASTNode):
    attrkey = ('level', 'title', 'opts')

    def __init__(self):
        super().__init__()
        self.level = 0
        self.title = str()
        self.opts = dict()
        self._sectindex = None

    def sectindex(self):
        return self._sectindex

    @property
    def sectnum(self):
        sectnums = [str(i + 1) for i in self.sectindex()]
        sectnum = '.'.join(sectnums)
        return sectnum


class BlockNode(ASTNode):
    def __init__(self):
        super().__init__()


class TocBlockNode(BlockNode):
    def __init__(self):
        super().__init__()

    def walk_sections(self):
        for n, gofoward in self.root.walk_depth():
            if isinstance(n, SectionNode):
                yield n, gofoward


class ListBlockNode(BlockNode):
    attrkey = ('level', 'indent')

    def __init__(self):
        super().__init__()
        self.level = -1
        self.indent = -1


class BulletListBlockNode(ListBlockNode):
    def __init__(self):
        super().__init__()


class OrderedListBlockNode(ListBlockNode):
    def __init__(self):
        super().__init__()


class DescriptionListBlockNode(ListBlockNode):
    def __init__(self):
        super().__init__()


class CheckListBlockNode(ListBlockNode):
    def __init__(self):
        super().__init__()


class ListItemNode(ASTNode):
    def __init__(self):
        super().__init__()
        self.options = dict()


class FootnoteListBlockNode(ASTNode):
    def __init__(self):
        super().__init__()


class ReferenceListBlockNode(ASTNode):
    def __init__(self):
        super().__init__()


class FigureBlockNode(ASTNode):
    def __init__(self):
        super().__init__()
        self.caption = None
        self.align = 'l'

    def _parent_section(self):
        node = self
        while not isinstance(node, SectionNode):
            node = node.parent
        return node

    def _fignum_format(self, gindex, lindex):
        def default_figure_fignum_format(gindex, lindex):
            return 'Figure {}.'.format(gindex)

        def default_table_fignum_format(gindex, lindex):
            return 'Table {}.'.format(gindex)

        if isinstance(self.children[0], TableBlockNode):
            if hasattr(self.root.config, 'table_fignum_format'):
                return self.root.config.table_fignum_format(gindex, lindex)
            return default_table_fignum_format(gindex, lindex)
        else:
            if hasattr(self.root.config, 'figure_fignum_format'):
                return self.root.config.figure_fignum_format(gindex, lindex)
            return default_figure_fignum_format(gindex, lindex)

    @property
    def fignum(self):
        gindex = 1
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
        section = self._parent_section()
        lindex = 1
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
        lindex = section.sectindex() + [lindex]
        return self._fignum_format(gindex, lindex)


class TableBlockNode(ASTNode):
    attrkey = ('row', 'col', 'headers')

    def __init__(self):
        super().__init__()
        self.row = 0
        self.col = 0
        self.headers = 0
        self.caption = None
        self.align = 'l'  # table align
        self.aligns = list()  # column alings

    def cell(self, row, col):
        # return self.children[row * self.col + col]
        return self.children[row].children[col]

    def _fignum_format(self, gindex, lindex):
        def default_fignum_format(gindex, lindex):
            return 'Table {}.'.format(gindex)

        if hasattr(self.root.config, 'table_fignum_format'):
            return self.root.config.table_fignum_format(gindex, lindex)
        return default_fignum_format(gindex, lindex)

    @property
    def fignum(self):
        gindex = 1
        for n, gofoward in self.root.walk_depth():
            if gofoward:
                if isinstance(n, TableBlockNode) and n.caption is not None:
                    if n == self:
                        break
                    gindex += 1
        section = self._parent_section()
        lindex = 1
        for n, gofoward in section.walk_depth():
            if gofoward:
                if isinstance(n, TableBlockNode) and n.caption is not None:
                    if n == self:
                        break
                    lindex += 1
        lindex = section.sectindex() + [lindex]
        return self._fignum_format(gindex, lindex)


class TableRowNode(ASTNode):
    def __init__(self):
        super().__init__()
        self.tp = 'data'  # 'header', 'data'
        self.idx = -1


class TableCellNode(ASTNode):
    class Size():
        def __init__(self, x, y):
            self.x = x
            self.y = y

    def __init__(self):
        super().__init__()
        self.idx = -1
        self.align = 'c'
        self.mergeto = None
        self.size = TableCellNode.Size(1, 1)


class LiteralBlockNode(ASTNode):
    def __init__(self):
        super().__init__()


class QuoteBlockNode(ASTNode):
    def __init__(self):
        super().__init__()


class CodeBlockNode(ASTNode):
    attrkey = ('lang',)

    def __init__(self):
        super().__init__()
        self.lang = str()
        self.text = str()


class CustomBlockNode(ASTNode):
    attrkey = ('ext',)

    def __init__(self):
        super().__init__()
        self.ext = str()
        self.text = str()


class HorizonBlockNode(ASTNode):
    def __init__(self):
        super().__init__()


class ParagraphNode(ASTNode):
    def __init__(self):
        super().__init__()


class TextNode(ASTNode):
    attrkey = ('text',)

    def __init__(self, text=None):
        super().__init__()
        self.text = str() if text is None else text


class RoleNode(ASTNode):
    attrkey = ('role', 'args', 'opts', 'value')

    def __init__(self, role=None, args=None, opts=None, value=None):
        super().__init__()
        self.role = str() if role is None else role
        self.args = list() if args is None else args
        self.opts = list() if opts is None else opts
        self.value = str() if value is None else value


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


class LinkNode(ASTNode):
    attrkey = ('opts', 'value')

    def __init__(self, opts=None, value=None):
        super().__init__()
        self.opts = list() if opts is None else opts
        self.value = str() if value is None else value

    @property
    def target_id(self):
        root = self.root
        # find by id
        for n, gofoward in root.walk_depth():
            if gofoward and isinstance(n, SectionNode):
                if n.id == self.value:
                    return n.id
        return self.value.replace(' ', '_')

    @property
    def target_title(self):
        root = self.root
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


class FootnoteNode(ASTNode):
    attrkey = ('value',)

    def __init__(self, value=None):
        super().__init__()
        self.value = str() if value is None else value
        self._description = None

    @property
    def description(self):
        if self._description:
            return self._description
        msg = 'Footnote not found: {}'.format(self.value)
        logger.error(msg)
        fn = FootnoteListBlockNode()
        fn.value = msg
        return fn


class ReferenceNode(ASTNode):
    attrkey = ('value',)

    def __init__(self, value=None):
        super().__init__()
        self.value = str() if value is None else value


def parse_optargs(argstr):
    tstr = argstr[:] if argstr else ''
    opts = {}
    while tstr:
        m = re.match(r'^(?: *([0-9a-z_\-]+)="([^"]*)") *', tstr)
        if m:
            opts[m.group(1)] = m.group(2)
        else:
            raise Exception('option parse error: [{}]'.format(argstr))
        tstr = tstr[len(m.group(0)):]
    return opts


def parse_funcargs(argstr):
    def f(*args, **kwargs):
        return args, kwargs

    exec('args = f({})'.format(argstr))
    params = locals()
    return params['args']


def nodeprint(node):
    depth = 0
    for n, gofoward in node.walk_depth():
        if gofoward:
            indent = '  ' * depth
            logger.debug('{}{}'.format(indent, n))
            depth += 1
        else:
            depth -= 1


def cmd(cmdstr):
    p = subprocess.run(cmdstr.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.stderr:
        logger.error(p.stderr.decode())
    out = p.stdout.decode()
    return out
