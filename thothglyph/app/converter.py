import sys
import os
import argparse
from thothglyph.reader import Reader
from thothglyph.writer import Writer
from thothglyph.node.nd import nodeprint
from thothglyph import __version__

import logging

NAMESPACE = 'thothglyph'

logger = logging.getLogger(NAMESPACE)
logger.setLevel(logging.WARNING)


def main():
    argparser = argparse.ArgumentParser(
        prog=NAMESPACE,
    )
    argparser.add_argument(
        '--version', '-v', action='version',
        version='{} {}'.format(NAMESPACE, __version__),
        help='display version and exit')
    argparser.add_argument(
        '--to', '-t', metavar='TYPE', default=None,
        help='output file type')
    argparser.add_argument(
        '--output', '-o', metavar='FILE', default=None,
        help='output file')
    argparser.add_argument(
        'input',
        help='input file')
    args = argparser.parse_args()

    default_from = 'tglyph'
    default_to = 'html'

    input_type = default_from
    input_dirname, input_fname = os.path.split(os.path.abspath(args.input))
    input_name, input_ext = os.path.splitext(input_fname)

    if args.to:
        output_type = args.to
        if args.output:
            output_name, output_ext = os.path.splitext(os.path.abspath(args.output))
            output_ext = output_ext[1:]
        else:
            output_name = input_name
            output_ext = None
    else:
        if args.output:
            output_name, output_ext = os.path.splitext(os.path.abspath(args.output))
            output_ext = output_ext[1:]
        else:
            output_name = input_name
            output_ext = default_to
        output_type = output_ext

    os.chdir(input_dirname)
    reader = Reader(input_type)
    node = reader.read(input_fname)
    nodeprint(node)

    writer = Writer(output_type)
    ext = output_ext or writer.ext
    writer.write('{}.{}'.format(output_name, ext), node)


if __name__ == '__main__':
    sys.exit(main())
