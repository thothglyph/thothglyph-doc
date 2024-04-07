# Thothglyph

A Documentation converter and language for Engineers

(Θωθ)

## Requirements

* python >= 3.8
* pillow
* cairosvg

## Installation

Minimum

```sh
pip install thothglyph-doc
```

\+ writers

```
# pdf
sudo apt install texlive-luatex texlive-fonts-recommended texlive-fonts-extra texlive-lang-cjk
# docx
pip install python-docx
```

\+ extensions

```
# graphviz
sudo apt install graphviz
pip install graphviz
# blockdiag
pip install blockdiag actdiag seqdiag nwdiag
# wavedrom
pip install wavedrom
```

## Usage

```sh
thothglyph -t html document.tglyph
```

## Languages

See [documents](https://thothglyph-doc.readthedocs.io/en/latest/index.html)

## Tools

* [vim-thothglyph](https://github.com/thothglyph/vim-thothglyph)
* [vscode-thothglyph](https://github.com/thothglyph/vscode-thothglyph)
