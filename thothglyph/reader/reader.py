from thothglyph.node import nd

from thothglyph.node import logging

logger = logging.getLogger(__file__)


class Reader():
    def __init__(self, parent=None):
        self.encoding = 'utf-8'
        self.parent = parent
        self.parser = None
        self.path = None

    def read(self, path, encoding=None):
        if encoding:
            self.encoding = encoding
        logger.info('{} read start.'.format(self.__class__.__name__))
        self.path = path
        with open(path, 'r', encoding=self.encoding) as f:
            data = f.read()
        node = self.parser.parse(data)
        self.set_sectnums(node)
        self.set_footnote_nums(node)
        logger.info('{} read finish.'.format(self.__class__.__name__))
        return node

    def set_sectnums(self, rootnode):
        nums = [0 for i in range(10)]
        level = 0
        for n, gofoward in rootnode.walk_depth():
            if gofoward:
                if isinstance(n, nd.SectionNode):
                    if not n.opts.get('nonum'):
                        nums[level] += 1
                        n._sectindex = [i - 1 for i in nums[:level + 1]]
                    level += 1
            else:
                if isinstance(n, nd.SectionNode):
                    if not n.opts.get('nonum'):
                        nums[level] = 0
                    level -= 1

    def set_footnote_nums(self, rootnode):
        footnotes = dict()
        references = dict()
        LI = nd.ListItemNode
        FNLB = nd.FootnoteListBlockNode
        RFLB = nd.ReferenceListBlockNode
        # Footnote
        for n, gofoward in rootnode.walk_depth():
            if gofoward and isinstance(n, nd.FootnoteNode):
                footnotes.setdefault(n.value, list())
                footnotes[n.value].append(n)
        for n, gofoward in rootnode.walk_depth():
            if gofoward and isinstance(n, LI) and isinstance(n.parent, FNLB):
                footnotes.setdefault(n.term, list())
                footnotes[n.term].append(n)
        for i, key in enumerate(footnotes):
            for n in footnotes[key]:
                n.fn_num = i + 1
        # Reference
        for n, gofoward in rootnode.walk_depth():
            if gofoward and isinstance(n, LI) and isinstance(n.parent, RFLB):
                references.setdefault(n.term, list())
                references[n.term].append(n)
        for n, gofoward in rootnode.walk_depth():
            if gofoward and isinstance(n, nd.ReferenceNode):
                references.setdefault(n.value, list())
                references[n.value].append(n)
        for i, key in enumerate(references):
            for n in references[key]:
                n.ref_num = i + 1
