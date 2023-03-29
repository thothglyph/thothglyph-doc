# Thothglyph Language リファレンスマニュアル

## はじめに

この文書は Thothglyph Language (トトグリフ言語) のリファレンスマニュアルです。

### 経緯

* 文中のソースコードにマークアップを適用したい

### 言語の特徴

Thothglyph Language の最大の特徴は、マークアップシンボルの多くに非 ASCII 文字を使っていることです。
これらの文字を使うことで、既存のマークアップ言語やプログラミング言語の構文との衝突を避け、
様々なソースコードをエスケープなしで文書に含められます。
また、シンボルに使用可能な文字が増えたことで、視認のしやすさと構文の単純化を両立できます。

欠点として、通常の文書にはあまり出現しない文字をシンボルに使用しているため、書きにくく感じるかもしれません。
これを軽減するために各種エディタ向けに Thothglyph 用の入力補助やシンタックスハイライトのプラグインを用意しています。

## Preprocess

Thothglyph はドキュメントを構文解析する前に簡単なプリプロセスを実行します。

### Config

`⑇⑇⑇`のみの行で囲まれたテキストは Config ブロックとなります。
ドキュメントの最初のみ記述可能な構文です。
ドキュメントの設定を Python 言語で記述します。

```
⑇⑇⑇
title = 'Document Title'
version = '1.2.3'
author = cmd("git config user.name")
attrs = {'author': 'Foo Bar'}
⑇⑇⑇
```

後述の Include ロールで外部ファイルをインクルードできます。

```
⑇⑇⑇
¤include⸨./conf.py⸩
⑇⑇⑇
```

### ControlFlow

1文字の'⑇'の後に特定のキーワードを記入すると ControlFlow となります。
ドキュメントの一部分を条件により表示/非表示できます。
サポートしているキーワードは if, elif, end です。
条件には Config ブロックで定義した attrs の値を使用できます。

```
⑇if author == 'Smith'
Profile about Smith.
⑇elif author == 'Tanaka'
Profile about Tanaka.
⑇end
```



### Comment

2文字の'⑇'に続く行末までの文字列はコメントとなります。
コメントはプリプロセスの段階で文中から削除されます。

```
This line includes comment --> ⑇⑇ This is comment.
```

## Blocks

ドキュメントはブロックの木構造で構成されています。
ブロックは基本的に行単位でまとまっています。

### Section

1文字以上の`▮`の後に空白とテキストを記入すると Section となります。
ドキュメントの最も大枠となるブロックです。
`▮`の文字数が見出しレベルに相当します。

```
▮ Section Lv.1 Title
▮▮ Section Lv.2 Title
▮▮▮ Section Lv.3 Title
▮▮▮▮ Section Lv.4 Title
▮▮▮▮▮ Section Lv.5 Title
▮▮▮▮▮▮ Section Lv.6 Title
▮▮▮▮▮▮▮ Section Lv.7 Title
```

見出しレベル1, 2のみ ATX-style の記法をサポートしています。
見出しの次の行にレベル1では`=`、レベル2では`-`を4文字以上記入します。

```
Section Lv.1 ATX-style
======================

Section Lv.2 ATX-style
----------------------
```

各見出しにはラベルを付けられます。ラベルは後述の Cross Reference で利用できます。

```
▮ Section Title ⟦sect1⟧
```

`▮` の末尾に `*` を記入すると見出しの番号付けをスキップします。

```
▮ まえがき (1. まえがき)
▮* 目次 (目次)
▮ XXとは (2. XXとは)
▮ YYとは (3. YYとは)
```

### Paragraph

通常の文字から始まる行は Paragraph と判断されます。
Paragraph は空行が出現するまで継続します。

```
これは段落1のテキストです。
改行しても段落は継続します。

これは段落2のテキストです。
```

### Bullet List

1文字以上の`•`と空白から始まるブロックは Bullet List (箇条書きリスト) となります。

```
• apple
• orange
• grape
```

`•`の文字数がリストのレベルに相当します。

```
• List item 1
•• List item 1-1
••• List item 1-1-1
••• List item 1-1-2
•• List item 1-2
••• List item 1-2-1
••• List item 1-2-2
• List item 2
```

リストの各アイテムの本文には複数ブロックを記入できます。
行頭のインデントを揃える必要はありません。

```
• Item 1 paragraph 1.
new line.

paragraph 2.

• Item 2 paragraph 1.
new line.

paragraph 2.
```

リストを終了して別のリストや段落を開始するには、そのレベルと同数の`◃`から成る行を記入します。
```
• My favorite food
•• apple
•• orange
•• grape
◃◃
•• sushi
•• tempura
◃
New Paragraph.
```

### Ordered List

1文字以上の`꓾`と空白から始まるブロックは Ordered List (順序付きリスト) となります。
`꓾`の文字数がリストのレベルに相当します。

```
꓾ List item 1
꓾꓾ List item 1-1
꓾꓾꓾ List item 1-1-1
꓾꓾꓾ List item 1-1-2
꓾꓾ List item 1-2
꓾꓾꓾ List item 1-2-1
꓾꓾꓾ List item 1-2-2
꓾ List item 2
◃
꓾ List item new 1
```

### Description List

1文字以上の`ᛝ`から始まり途中`ᛝ`と空白が含まれるブロックは Description List (説明リスト) となります。
最初の`ᛝ`の文字数がリストのレベルに相当します。
`ᛝ`で囲まれた文字列は用語、`ᛝ`以降は本文です。

```
ᛝTerm 1ᛝ List item 1
ᛝᛝTerm 1-1ᛝ List item 1-1
ᛝᛝᛝTerm 1-1-1ᛝ List item 1-1-1
ᛝᛝᛝTerm 1-1-2ᛝ List item 1-1-2
ᛝᛝTerm 1-2ᛝ List item 1-2
ᛝᛝᛝTerm 1-2-1ᛝ List item 1-2-1
ᛝᛝᛝTerm 1-2-2ᛝ List item 1-2-2
ᛝTerm 2ᛝ List item 2
◃
ᛝTerm 1ᛝ List item new 1
```

用語と本文は通常横並びで出力されます。
用語の終端に`◃`を記入すると用語の後改行して本文を出力します。

```
ᛝTerm 1◃ᛝ List item 1
ᛝTerm 2◃ᛝ List item 2
```

### Check List

1文字以上の`•`と`[ ]`と空白から始まるブロックは Check List (チェックリスト) となります。
`•`の文字数がリストのレベルに相当します。
チェックボックスの状態は`[ ]`, `[x]`, `[-]`の3つを選択できます。

```
•[ ] List item 1
••[-] List item 1-1
•••[x] List item 1-1-1
•••[ ] List item 1-1-2
••[x] List item 1-2
•••[x] List item 1-2-1
•••[x] List item 1-2-2
•[ ] List item 2
◃
•[x] List item new 1
```

### 複合リスト

これまで説明したリストは別種のリストを入れ子にできます。
ただしリストのレベルは種類に関係なく設定する必要があります。

```
• List item 1
꓾꓾ List item 1-1
ᛝᛝᛝAᛝ List item 1-1-1
ᛝᛝᛝBᛝ List item 1-1-2
꓾꓾ List item 1-2
•••[x] List item 1-2-1
•••[ ] List item 1-2-2
• List item 2
```

### Footnote List

1文字だけの`•`と`[^ID]`と空白から始まるブロックは Footnote List (脚注リスト) となります。
リストは入れ子にできません。
文中の脚注の書き方は [Footnote](#Footnote) 参照。

```
•[^1] This is footnote.
•[^2] This is footnote too.
```

### Reference List

1文字だけの`•`と`[#ID]`と空白から始まるブロックは Reference List (参照リスト) となります。
リストは入れ子にできません。
文中の参照の書き方は [Reference](#Reference) 参照。

```
•[#1] The Awesome Document, 1990, Anonymous.
•[#2] The theory of theory, 2000-01-01, Anonymous.
```

### Basic Table

`|`で囲まれた行が連続するブロックは Basic Table となります。
基本的な構文は既存の軽量マークアップ言語のものと似ています。

```
| data11 | data12 | data13 |
| data21 | data22 | data23 |
```

`:-:` で構成された行はヘッダ部とデータ部を分割し、セル内のテキストアライメントを設定します。
ヘッダ部がない場合はテキストアライメントのみ設定します。
`+-` は左アライメントかつセル幅をページ幅に合うよう調節します。(latex, pdfのみ)

```
| head11 | head12 | head13 | head14 |
| head21 | head22 | head23 | head24 |
|:-------|:------:|-------:|+-------|
| data11 | data12 | data13 | data14 |
| data21 | data22 | data23 | data24 |
| a | b | c | d |
```

セルの内容を`⏴`もしくは`⏶`で開始することで、セルを結合できます。

```
| head11 | head12 | ⏴      | ⏴      |
|--------|--------|--------|--------|
| data11 | data12 | data13 | data14 |
| data21 | data22 | ⏴      | data24 |
| data31 | ⏶      | ⏴      | ⏶      |
| data41 | data42 | ⏴      | data44 |
| data51 | data52 | data53 |⏴data54 |
| data61 |⏶data62 |⏶data63 |⏴data64 |
```

### List Table
`|===`という行から始まり`===|`という行で終わるブロックは List Table となります。
List Table 内はレベル2以上の Bullet List で構成されます。
レベル1の文は無視され、レベル2のリストアイテムが各セルの内容になります。
レベル3のリストは表内のレベル1のリストに置き換わります。

```
|===
• •• data11
  •• data12
     ••• item1
     ••• item2
     ••• item3
  •• data13
• •• data21
  •• data22
  •• data23
===|
```

`◃`でリストを分割すると、第1リストがヘッダ、第2リストがデータになります。

```
|===
• •• head1
  •• head2
  •• head3
◃
• •• data11
  •• data12
  •• data13
• •• data23
  •• data22
  •• data23
===|
```

Basic Tableと 同様にセルの内容を`⏴`もしくは`⏶`で開始することで、セルを結合できます。

```
|===
• •• head1
  •• head2
  •• ⏴
◃
• •• data11
  •• data12
  •• data13
• •• data23
  •• ⏶data22
  •• data23
===|
```

開始行の `|===` に続き `⟦⟧` でオプションを記述できます。

```
|===⟦align="lcr"⟧
• •• data11
  •• data12
  •• data13
• •• A
  •• B
  •• C
===|
```

### Figure

後述の Role という記法で図や表にキャプションを付けられます。
実際にキャプションが表示される位置は出力形式やテンプレートに依存します。

```
¤figure⸨caption⸩
¤image⸨./tglyph_64.png⸩
```

```
¤figure⸨caption⸩
| head11 | head12 | head13 |
| head21 | head22 | head23 |
|--------|--------|--------|
| data11 | data12 | data13 |
| data21 | data22 | data23 |
| data31 | data32 | data33 |
```

```
¤figure⸨caption⸩
[Not Image.]
```

### Quote Block

`> `で始まる行が連続したブロックは Quote Block (引用ブロック) となります。

```
> Quote text text text.
> new line text.
> > Nested quote text.
> return first quote.

> New quote text.
```

### Code Block

`⸌⸌⸌`という行で囲まれたブロックは Code Block となります。
始めの`⸌⸌⸌`に続き言語名を記入することでシンタックスハイライトのヒントを与えます。

```
⸌⸌⸌c
#include <stdio.h>
# include <stdlib.h>
int main()
{
  printf("Hello World!!\n");
  exit(0);
}
⸌⸌⸌
```

後述の Include ロールで外部ファイルをインクルードできます。

```
⸌⸌⸌c
¤include⸨./example.c⸩
⸌⸌⸌
```

### Custom Block

`¤¤¤`という行で囲まれたブロックは Custom Block となります。
始めの`¤¤¤`に続き拡張名を記入することで様々な拡張機能を実行します。

```
¤¤¤graphviz
digraph graph_name {
  alpha;
  beta;
  alpha -> beta;
}
¤¤¤
```

後述の Include ロールで外部ファイルをインクルードできます。

```
¤¤¤graphviz
¤include⸨./graph1.dot⸩
¤¤¤
```

### Horizontal Line

4文字以上の`=`もしくは`-`で始まる1行は Horizontal Line (水平線) となります。

```
paragraph

====

paragraph
```

## Inline markup

ブロック内のいくつかのテキストにはインラインマークアップを適用できます。

### Decoration

特定のシンボルでテキストを囲むことで、テキストを装飾できます。

```
装飾の種類は⁒強調⁒、⋄重要⋄、‗挿入‗、¬削除¬があります。
⋄⁒強調かつ重要⁒⋄のように入れ子にできます。
また⌃上付き文字⌃や⌄下付き文字⌄にもできます。
更に⫶変数⫶や⸌コード⸌も記入できます。
```

### Role

`¤ロール名⟦オプション⟧⸨本文⸩`という構文は Role となります。
`⟦オプション⟧`は省略可能です。

### Image Role

画像を挿入します。

```
Thothglyph のアイコンはこちら: ¤image⸨./tglyph_64.png⸩
```

オプションで画像の幅を設定できます。縦横比は固定です。

```
ピクセル数で指定: ¤image⟦w="150px"⟧⸨./tglyph_64.png⸩

ページ幅の割合で指定: ¤image⟦w="20%"⟧⸨./tglyph_64.png⸩
```

### Include Role

外部のtglyphファイルを解釈して挿入します。

```
¤include⸨./sub1.tglyph⸩
```

### Keyboard / Button / Menu Role

テキストの装飾の一種です。

```
Type ¤kbd⸨Ctrl A⸩ right now.

Click ¤btn⸨OK⸩ or ¤btn⸨Cancel⸩.

Select ¤menu⸨File > Quit⸩ to exit application.
```

### Hyper Link

`⟦テキスト⟧⸨URL⸩`という構文は Hyper Link となります。
`⟦テキスト⟧`は省略可能です。
Role に似ていますが別の構文です。

```
Search ⸨https://www.yahoo.com/⸩ !

For more information, check ⟦here⟧⸨https://www.google.com/⸩ !
```

### Cross Reference

Hyper Link と同じ構文でURLの代わりに文書中のラベル名を指定すると Cross Reference となります。
テキストを指定しない場合、ラベルの参照先から取得します。

```
First section: ⸨sect1⸩!

⟦Here⟧⸨sect1⸩ is the same!
```

### Footnote

文中に`[^ID]`と記入すると Footnote となります。
別の場所で Footnote List ブロックに脚注の内容を記入します。
ID には数字も指定可能です。ただし本文中に出現した順に番号が割り振られるため数値に意味はありません。
ID はセクションレベル1以下で一意のものにする必要があります。
セクションレベル1が異なる Footnote List は参照できません。

```
The important text. [^1] And the important text too. [^2]

•[^1] This is footnote.
•[^2] This is footnote too.
```

### Refenrence

文中に`[#ID]`と記入すると Reference となります。
別の場所で Reference List ブロックに参考文献の内容を記入します。
Reference List のリストには本文中で引用されていないものも含められます。
ID には数字も指定可能です。ただし Reference List のリスト順に番号が割り振られるため数値に意味はありません。

```
The important text. [#1] And the important text too. [#2]

•[#1] The Awesome Document, 1990, Anonymous.
•[#2] The theory of theory, 2000-01-01, Anonymous.
•[#3] Unreferenced bibliograpy I, 2XXX-XX-XX, Anonymous.
•[#4] Unreferenced bibliograpy II, 2XXX-XX-XX, Anonymous.
```

### Replace

`⁅`と`⁆`で囲まれた文字列は Config で attrs として定義した辞書をもとに置換できます。

```
Hello, I am ⁅author⁆.
```
