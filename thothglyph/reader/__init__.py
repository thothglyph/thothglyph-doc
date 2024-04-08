import importlib
from thothglyph.error import ThothglyphError


readerclass = {
    'tglyph': 'TglyphReader',
    'md': 'MdReader',
}


def ReaderClass(target: str):
    modname = target
    if target not in readerclass:
        msg = 'Unknown input file type: {}'.format(target)
        raise ThothglyphError(msg)

    clsname = readerclass[target]
    modpath = 'thothglyph.reader.{}'.format(modname)
    module = importlib.import_module(modpath)
    return getattr(module, clsname)
