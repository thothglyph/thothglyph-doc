from __future__ import annotations
from typing import Dict, List, Optional
from thothglyph.node import nd
from thothglyph.node import logging
import os

logger = logging.getLogger(__file__)


class Reader():
    target: str = 'unknown'
    ext: str = 'unknown'

    def __init__(self, parent: Optional[Reader] = None):
        self.encoding: str = 'utf-8'
        self.parent: Optional[Reader] = parent
        self.parser: Parser = Parser(self)
        self.path: str = str()

    def read(self, path: str, encoding: Optional[str] = None) -> nd.ASTNode:
        if encoding:
            self.encoding = encoding
        if self.parent is None:
            logger.info('{}: read documents'.format(self.__class__.__name__))
        self.path = path
        with open(path, 'r', encoding=self.encoding) as f:
            data = f.read()
        node = self.parser.parse(data)
        self.set_sectnums(node)
        self.set_footnote_nums(node)
        self.merge_tablecell_text(node)
        return node

    def set_sectnums(self, rootnode: nd.ASTNode) -> None:
        nums: List[int] = [0 for i in range(10)]
        level: int = 0
        for n, gofoward in rootnode.walk_depth():
            if gofoward:
                if isinstance(n, nd.SectionNode):
                    if not n.opts.get('notoc') and not n.opts.get('nonum'):
                        nums[level] += 1
                        n._sectindex = [i - 1 for i in nums[:level + 1]]
                    level += 1
            else:
                if isinstance(n, nd.SectionNode):
                    if not n.opts.get('notoc') and not n.opts.get('nonum'):
                        nums[level] = 0
                    level -= 1
        nums = [0 for i in range(10)]
        level = 0
        for n, gofoward in rootnode.walk_depth():
            if gofoward:
                if isinstance(n, nd.SectionNode):
                    if not n.opts.get('notoc') and n.opts.get('nonum'):
                        nums[level] += 1
                        n._sectindex = [-i - 1 for i in nums[:level + 1]]
                    level += 1
            else:
                if isinstance(n, nd.SectionNode):
                    if not n.opts.get('notoc') and n.opts.get('nonum'):
                        nums[level] = 0
                    level -= 1

    def set_footnote_nums(self, rootnode: nd.ASTNode) -> None:
        footnotes: Dict[str, Dict[str, List[nd.ASTNode]]] = dict()  # footnotes[sect][id]
        references: Dict[str, List[nd.ASTNode]] = dict()
        LI = nd.ListItemNode
        FNLB = nd.FootnoteListBlockNode
        RFLB = nd.ReferenceListBlockNode
        # Footnote
        for n, gofoward in rootnode.walk_depth():
            if gofoward and isinstance(n, nd.FootnoteNode):
                sect = str(n.treeindex()[:2])
                footnotes.setdefault(sect, dict())
                footnotes[sect].setdefault(n.value, list())
                footnotes[sect][n.value].append(n)
        for n, gofoward in rootnode.walk_depth():
            if gofoward and isinstance(n, LI) and isinstance(n.parent, FNLB):
                sect = str(n.treeindex()[:2])
                footnotes.setdefault(sect, dict())
                footnotes[sect].setdefault(n.title, list())
                footnotes[sect][n.title].insert(0, n)
        fngi: int = 0
        for si, sect in enumerate(footnotes):
            for i, key in enumerate(footnotes[sect]):
                fngi += 1
                for n in footnotes[sect][key]:
                    n.fn_num = fngi
                if footnotes[sect][key] and isinstance(footnotes[sect][key][0], LI):
                    footnotes[sect][key][0].footnotes = footnotes[sect][key][1:]
                    for n in footnotes[sect][key][1:]:
                        n._description = footnotes[sect][key][0]
        # Reference
        for n, gofoward in rootnode.walk_depth():
            if gofoward and isinstance(n, LI) and isinstance(n.parent, RFLB):
                references.setdefault(n.title, list())
                references[n.title].append(n)
        for n, gofoward in rootnode.walk_depth():
            if gofoward and isinstance(n, nd.ReferenceNode):
                references.setdefault(n.value, list())
                references[n.value].append(n)
        for i, key in enumerate(references):
            for n in references[key]:
                n.ref_num = i + 1

    def merge_tablecell_text(self, rootnode: nd.ASTNode) -> None:
        tables = []
        for n, gofoward in rootnode.walk_depth():
            if not gofoward and isinstance(n, nd.TableBlockNode):
                tables.append(n)
        mergelist = {}
        for table in tables:
            for cell in table.cells():
                if cell.mergeto:
                    mergelist.setdefault(cell.mergeto, {'obj': cell.mergeto, 'from': list()})
                    mergelist[cell.mergeto]['from'].append(cell)
        for merge in mergelist.values():
            mergetexts = [c for mf in merge['from'] for c in mf.children]
            mergetexts = ''.join([t.text for t in mergetexts if isinstance(t, nd.TextNode)])
            if mergetexts == '':
                continue
            cell = merge['obj']
            paragraph = nd.ParagraphNode()
            for child in cell.children:
                paragraph.add(child)
            cell.children.clear()
            cell.add(paragraph)
            for mergefrom in merge['from']:
                paragraph = nd.ParagraphNode()
                for child in mergefrom.children:
                    paragraph.add(child)
                mergefrom.children.clear()
                cell.add(paragraph)


class Parser():
    def __init__(self, reader: Reader):
        self.reader = reader

    def parse(self, data: str) -> nd.ASTNode:
        return nd.ASTNode()

    def _check_recursive_include(self, path: str) -> bool:
        if not os.path.exists(path):
            return False
        pathlist: List[str] = list()
        parser: Parser = self
        while parser.reader.parent:
            pathlist.insert(0, parser.reader.path)
            parser = parser.reader.parent.parser
        pathlist.insert(0, parser.reader.path)
        if path in pathlist:
            # msg = 'Detect recursive include'
            # raise ThothglyphError("{}: {}, {}".format(msg, path, pathlist))
            return False
        return True

    def _extract_tablecell_merge_hmarker(self, text: str):
        return ''

    def _extract_tablecell_merge_vmarker(self, text: str):
        return ''

    def _tablecell_merge(
        self, table: nd.TableBlockNode, cell: nd.TableCellNode, r: int, c: int, text: str
    ) -> str:
        hmarker = self._extract_tablecell_merge_hmarker(text)
        vmarker = self._extract_tablecell_merge_vmarker(text)
        if len(hmarker) > 0:
            text = text[len(hmarker):]
            to = table.cell(r, c - 1)
            to = to.mergeto if to.mergeto else to
            if to.parent.idx == cell.parent.idx:
                to.size.x += 1
            cell.mergeto = to
        elif len(vmarker) > 0:
            text = text[len(vmarker):]
            to = table.cell(r - 1, c)
            to = to.mergeto if to.mergeto else to
            to.size.y += 1
            if to.idx == cell.idx:
                cell.mergeto = to
        return text
