import os
import re

from thothglyph.node import logging

logger = logging.getLogger(__file__)


class Writer():
    target = 'unknown'
    ext = 'unknown'

    default_theme = 'default'

    class DocData():
        def __init__(self):
            pass

    def __init__(self):
        self.encoding = 'utf-8'
        self.data = str()
        self.rootnode = None
        self.__continue = False

    def template_dir(self):
        config = self.rootnode.config
        if hasattr(config, 'templatedir'):
            template_dir = config.templatedir
        else:
            libdir = os.path.join(os.path.dirname(__file__), '..')
            template_dir = os.path.join(libdir, 'template')
        return template_dir

    def theme(self, target=None):
        config = self.rootnode.config
        if hasattr(config, 'theme'):
            theme = config.theme
        else:
            theme = Writer.default_theme
        if isinstance(theme, dict):
            target = target or self.target
            theme = theme.get(target, Writer.default_theme)
        return theme

    @property
    def template_docdata(self):
        docdata = Writer.DocData()
        docdata.title = self.rootnode.config.title if self.rootnode else None
        docdata.author = self.rootnode.config.author if self.rootnode else None
        docdata.version = self.rootnode.config.version if self.rootnode else None
        docdata.data = self.data
        docdata.template_dir = self.template_dir()
        return docdata

    def parse(self, node):
        prev_continue = False
        continue_node = None
        for n, gofoward in node.walk_depth():
            if not self.__continue or n == continue_node:
                if n == continue_node:
                    self.__continue = False
                if gofoward:
                    mname = 'visit_{}'
                else:
                    mname = 'leave_{}'
                nodename = re.sub(r'Node$', r'', n.__class__.__name__).lower()
                methodname = mname.format(nodename)
                try:
                    if not hasattr(self, methodname):
                        raise NotImplementedError()
                    method = getattr(self, methodname)
                    method(n)
                except NotImplementedError:
                    methodname = mname.format('other')
                    method = getattr(self, methodname)
                    method(n)
                except Exception as e:
                    logger.error(e)
            if self.__continue and not prev_continue:
                continue_node = n
            prev_continue = self.__continue

    def _continue(self):
        self.__continue = True

    def visit_other(self, node):
        raise Exception()

    def leave_other(self, node):
        raise Exception()

    def write(self, fpath, node):
        logger.info('{} write start.'.format(self.__class__.__name__))
        self.rootnode = node
        self.parse(node)
        with open(fpath, 'w', encoding=self.encoding) as f:
            f.write(self.data)
        logger.info('{} write finish.'.format(self.__class__.__name__))
