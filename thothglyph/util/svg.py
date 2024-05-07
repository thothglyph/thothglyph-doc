from __future__ import annotations
import os
import shutil
import subprocess
import cairosvg
from thothglyph.error import ThothglyphError


def svg2pdf(**kwargs) -> None:
    svg2xxx('pdf', **kwargs)


def svg2png(**kwargs) -> None:
    svg2xxx('png', **kwargs)


def svg2xxx(target, **kwargs) -> None:
    inpath = None
    indata = None
    outpath = None
    scale = 1.0
    if 'url' in kwargs and kwargs['url']:
        inpath = kwargs['url']
    elif 'bytestring' in kwargs and kwargs['bytestring']:
        indata = kwargs['bytestring']
    else:
        msg = 'svg2{}(): input not found.'.format(target)
        raise ThothglyphError(msg)

    if 'write_to' in kwargs and kwargs['write_to']:
        outpath = kwargs['write_to']
    else:
        msg = 'svg2{}(): output not found.'.format(target)
        raise ThothglyphError(msg)
    if 'scale' in kwargs:
        scale = kwargs['scale']

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
            'rsvg-convert', '-f', target, '-o', outpath, '-z', str(scale)
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
        if target == 'pdf':
            cairosvg.svg2pdf(
                bytestring=indata,
                write_to=outpath,
                scale=scale
            )
        elif target == 'png':
            cairosvg.svg2png(
                bytestring=indata,
                write_to=outpath,
                scale=scale
            )
