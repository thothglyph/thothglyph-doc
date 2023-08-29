import sys
import os
import argparse
if True:
    selfdir = os.path.dirname(__file__)
    rootdir = os.path.join(selfdir, '..', '..')
    sys.path.insert(0, rootdir)
from thothglyph.reader.tglyph import TglyphReader
from thothglyph.writer import writerclass
from thothglyph.node.nd import nodeprint

import logging

logger = logging.getLogger('thothglyph')
logger.setLevel(logging.DEBUG)


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument('--target', '-t', default='html')
    args = argparser.parse_args()

    os.chdir(selfdir)
    reader = TglyphReader()
    node = reader.read('main.tglyph')
    print('--------')
    nodeprint(node)
    print('--------')
    writer = writerclass[args.target]()
    writer.write('main.{}'.format(args.target), node)


if __name__ == '__main__':
    main()
