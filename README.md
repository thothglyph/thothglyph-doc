# Thothglyph

A Documentation converter and language for Engineers

(Θωθ)

## Requirements

* python >= 3.7
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
tglyph -t html document.tglyph
```

## Thothglyph Language

See [quick-reference.ja.md](doc/language/quick-reference.ja.md)

## Tools

* [vim-thothglyph](https://github.com/nakandev/vim-thothglyph)
* [vscode-thothglyph](https://github.com/nakandev/vscode-thothglyph)
