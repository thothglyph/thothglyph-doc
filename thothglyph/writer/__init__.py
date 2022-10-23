import importlib


writerclass = {
    'html': 'HtmlWriter',
    'latex': 'LatexWriter',
    'pdf': 'PdfWriter',
    'docx': 'DocxWriter',
}


def Writer(target):
    modname = target
    clsname = writerclass[target]
    modpath = 'thothglyph.writer.{}'.format(modname)
    module = importlib.import_module(modpath)
    return getattr(module, clsname)()
