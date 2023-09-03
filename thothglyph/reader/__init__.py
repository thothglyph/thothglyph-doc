import importlib


readerclass = {
    'tglyph': 'TglyphReader',
    'md': 'MdReader',
}


def ReaderClass(target: str):
    modname = target
    clsname = readerclass[target]
    modpath = 'thothglyph.reader.{}'.format(modname)
    module = importlib.import_module(modpath)
    return getattr(module, clsname)
