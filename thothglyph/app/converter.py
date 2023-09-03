import sys
import os
import argparse
from thothglyph.error import ThothglyphError
from thothglyph.reader import ReaderClass
from thothglyph.writer import WriterClass
from thothglyph.node.nd import nodeprint
from thothglyph import __version__

from thothglyph.node import logging

NAMESPACE = 'thothglyph'

logger = logging.getLogger()
logger.setLevel(logging.INFO)


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
        '--from', '-f', metavar='TYPE', default=None,
        help='input file type')
    argparser.add_argument(
        'input',
        help='input file')
    args = argparser.parse_args()

    default_from = 'tglyph'
    default_to = 'html'

    input_type = default_from
    input_dirname, input_fname = os.path.split(os.path.abspath(args.input))
    input_name, input_ext = os.path.splitext(input_fname)
    input_ext = input_ext[1:]
    if args.__dict__['from']:
        input_type = args.__dict__['from']
    else:
        input_type = input_ext

    if args.to:
        output_type = args.to
    else:
        if args.output:
            _, output_ext = os.path.splitext(os.path.abspath(args.output))
            output_ext = output_ext[1:]
        else:
            output_ext = ''
        output_type = output_ext or default_to

    input_absfpath = os.path.abspath(args.input)
    if args.output is None:
        output_absfpath = None
    else:
        output_absfpath = os.path.abspath(args.output)

    os.chdir(input_dirname)
    try:
        reader = ReaderClass(input_type)()
        node = reader.read(input_fname)
        nodeprint(node)

        writer = WriterClass(output_type)()
        odir, ofbname, ofext = writer.make_output_fpath(input_absfpath, output_absfpath, node)
        output_fpath = os.path.join(odir, '{}.{}'.format(ofbname, ofext))
        writer.write(output_fpath, node)
    except Exception as e:
        if isinstance(e, ThothglyphError):
            logger.error(e)
        else:
            logger.exception(e)
        sys.exit(1)


if __name__ == '__main__':
    sys.exit(main())
