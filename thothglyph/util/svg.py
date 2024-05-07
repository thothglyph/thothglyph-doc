from __future__ import annotations
import os
import shutil
import subprocess
import cairosvg
from thothglyph.error import ThothglyphError


def svg2pdf(**kwargs) -> None:
    inpath = None
    indata = None
    outpath = None
    if 'url' in kwargs and kwargs['url']:
        inpath = kwargs['url']
    elif 'bytestring' in kwargs and kwargs['bytestring']:
        indata = kwargs['bytestring']
    else:
        msg = 'svg2pdf(): input not found.'
        raise ThothglyphError(msg)

    if 'write_to' in kwargs and kwargs['write_to']:
        outpath = kwargs['write_to']
    else:
        msg = 'svg2pdf(): output not found.'
        raise ThothglyphError(msg)

    if inpath:
        with open(inpath, 'rb') as f:
            indata = f.read()
    if isinstance(indata, str):
        indata = indata.encode()

    outdir = os.path.dirname(os.path.abspath(outpath))
    if not os.path.exists(outdir):
        os.makedirs(outdir, exist_ok=True)

    rsvg_convert = shutil.which('rsvg-convert')
    if rsvg_convert:
        rsvg_cmd = [
            'rsvg-convert', '-f', 'pdf', '-o', '{}.pdf'.format(outpath)
        ]
        p = subprocess.Popen(
            rsvg_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        p.communicate(input=indata)
        if p.returncode != 0:
            msg = '{} command exit with code {}.'.format(rsvg_cmd[0], p.returncode)
            raise ThothglyphError(msg)
    else:
        cairosvg.svg2pdf(bytestring=indata, write_to='{}.pdf'.format(outpath))
