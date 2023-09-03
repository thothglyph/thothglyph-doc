from __future__ import annotations
from typing import Optional, List
import os
import re
from thothglyph.error import ThothglyphError
from thothglyph.node import nd
from thothglyph.node import logging

logger = logging.getLogger(__file__)


class Writer():
    target: str = 'unknown'
    ext: str = 'unknown'

    default_theme: str = 'default'

    class DocData():
        def __init__(self):
            self.title: str = ''
            self.author: str = ''
            self.version: str = ''
            self.template_dir: str = ''
            self.data: str = ''

        def __getattr__(self, name):
            msg = f'${{doc.{name}}} in template cannot be resolved.' \
                  f' Please define "{name}" in config.'
            logger.warn(msg)
            alt = f'*doc.{name}*'
            return alt

    def __init__(self):
        self.encoding: str = 'utf-8'
        self.data: str = str()
        self.rootnode: Optional[nd.DocumentNode] = None
        self.__continue: bool = False

    def template_dir(self) -> str:
        assert isinstance(self.rootnode, nd.DocumentNode)
        config = self.rootnode.config
        if hasattr(config, 'templatedir'):
            template_dir = config.templatedir
        else:
            libdir = os.path.join(os.path.dirname(__file__), '..')
            template_dir = os.path.join(libdir, 'template')
        return template_dir

    def theme(self, target: Optional[str] = None) -> str:
        assert isinstance(self.rootnode, nd.DocumentNode)
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
        for k, v in self.rootnode.config.docdata_params.items():
            if k not in docdata.__dict__:
                setattr(docdata, k, v)
        docdata.template_dir = self.template_dir()
        docdata.data = self.data
        return docdata

    def parse(self, node) -> None:
        prev_continue: bool = False
        continue_node: Optional[nd.ASTNode] = None
        for n, gofoward in node.walk_depth():
            if not self.__continue or n == continue_node:
                if n == continue_node:
                    self.__continue = False
                if gofoward:
                    mname: str = 'visit_{}'
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
                    logger.error('{}: {}'.format(methodname, e))
            if self.__continue and not prev_continue:
                continue_node = n
            prev_continue = self.__continue

    def _continue(self) -> None:
        self.__continue = True

    def visit_other(self, node) -> None:
        nodename = re.sub(r'Node$', r'', node.__class__.__name__).lower()
        msg = 'Not implemented: vist_{}().'.format(nodename)
        raise ThothglyphError(msg)

    def leave_other(self, node) -> None:
        nodename = re.sub(r'Node$', r'', node.__class__.__name__).lower()
        msg = 'Not implemented: leave_{}().'.format(nodename)
        raise ThothglyphError(msg)

    def make_output_fpath(
        self, infpath: str, outfpath: Optional[str], node: nd.ASTNode
    ) -> List[str, str, str]:
        indir, infname = os.path.split(infpath)
        infbname, infext = os.path.splitext(infname)
        if hasattr(node.config, 'filename'):
            conffbname = node.config.filename
        else:
            conffbname = ''
        if outfpath is None:
            outdir = indir
            outfbname = conffbname or infbname
            outfext = self.ext
        else:
            if os.path.isdir(outfpath):
                outdir = outfpath
                outfbname = conffbname or infbname
                outfext = self.ext
            else:
                outdir, outfname = os.path.split(outfpath)
                outfbname, outfext = os.path.splitext(outfname)
                outfext = outfext[1:] or self.ext
        return (outdir, outfbname, outfext)

    def write(self, fpath: str, node: nd.ASTNode) -> None:
        logger.info('{} write start.'.format(self.__class__.__name__))
        self.rootnode = node
        self.parse(node)
        with open(fpath, 'w', encoding=self.encoding) as f:
            f.write(self.data)
        logger.info('{} write finish.'.format(self.__class__.__name__))
