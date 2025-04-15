---
title = 'CustomBlock Test'
---

# CustomBlock Test

## Math

Tex言語で数式を記述できる。

```
sudo apt install texlive-fonts-recommended texlive-fonts-extra texlive-lang-cjk xdvik-ja evince
```

When {math}`a \ne 0`, there are two solutions
to {math}`ax^2 + bx + c = 0` and they are

```math
x = {-b \pm \sqrt{b^2-4ac} \over 2a}
```

## Graphviz

テキストベースのグラフ作成ツール。dot言語で記述する。

```
pip install graphviz
```

```graphviz
graph my_graph {
    a [label="Foo"];
    b [shape=circle];
    a -- b -- c [color=blue];
}
```

## PlantUML

UML図をテキストベースで作成できる。Java製。

```
sudo apt install plantuml
```

```plantuml
@startuml
Object <|-- ArrayList

Object : equals()
ArrayList : Object[] elementData
ArrayList : size()
@enduml
```

## blockdiag

システム設計、ネットワーク設計でよく使われる図をテキストベースで作成できる。

```
pip install blockdiag actdiag seqdiag nwdiag
```

```blockdiag
blockdiag admin {
  index [label = "List of FOOs"];
  add [label = "Add FOO"];
  add_confirm [label = "Add FOO (confirm)"];
  edit [label = "Edit FOO"];
  edit_confirm [label = "Edit FOO (confirm)"];
  show [label = "Show FOO"];
  delete_confirm [label = "Delete FOO (confirm)"];

  index -> add  -> add_confirm  -> index;
  index -> edit -> edit_confirm -> index;
  index -> show -> index;
  index -> delete_confirm -> index;
}
```

```blockdiag
seqdiag {
  browser  -> webserver [label = "GET /index.html"];
  browser <-- webserver;
  browser  -> webserver [label = "POST /blog/comment"];
              webserver  -> database [label = "INSERT comment"];
              webserver <-- database;
  browser <-- webserver;
}
```

```blockdiag
nwdiag {
  network dmz {
      address = "210.x.x.x/24"

      web01 [address = "210.x.x.1"];
      web02 [address = "210.x.x.2"];
  }
  network internal {
      address = "172.x.x.x/24";

      web01 [address = "172.x.x.1"];
      web02 [address = "172.x.x.2"];
      db01;
      db02;
  }
}
```

```blockdiag
rackdiag {
  // define height of rack
  16U;

  // define rack items
  1: UPS [2U];
  3: DB Server
  4: Web Server
  5: Web Server
  6: Web Server
  7: Load Balancer
  8: L3 Switch
}
```

```blockdiag
packetdiag {
  colwidth = 32
  node_height = 72

  0-15: Source Port
  16-31: Destination Port
  32-63: Sequence Number
  64-95: Acknowledgment Number
  96-99: Data Offset
  100-105: Reserved
  106: URG [rotate = 270]
  107: ACK [rotate = 270]
  108: PSH [rotate = 270]
  109: RST [rotate = 270]
  110: SYN [rotate = 270]
  111: FIN [rotate = 270]
  112-127: Window
  128-143: Checksum
  144-159: Urgent Pointer
  160-191: (Options and Padding)
  192-223: data [colheight = 3]
}
```

## Mermaid

```
npm install -g @mermaid-js/mermaid-cli
```

```mermaid
flowchart LR

A[Hard] -->|Text| B(Round)
B --> C{Decision}
C -->|One| D[Result 1]
C -->|Two| E[Result 2]
```

```mermaid
gantt
    title A Gantt Diagram
    dateFormat YYYY-MM-DD
    section Section
        A task          :a1, 2014-01-01, 30d
        Another task    :after a1, 20d
    section Another
        Task in Another :2014-01-12, 12d
        another task    :24d
```

```mermaid
---
title: Example Git diagram
---
gitGraph
   commit
   commit
   branch develop
   checkout develop
   commit
   commit
   checkout main
   merge develop
   commit
   commit
```

## WaveDrom

HW設計でよく使われる図をテキストベースで作成できる。JSON形式で記述する。

```
pip install wavedrom
```

```wavedrom
{ "signal": [
 { "name": "CK",   "wave": "P.......",                                              "period": 2  },
 { "name": "CMD",  "wave": "x.3x=x4x=x=x=x=x", "data": "RAS NOP CAS NOP NOP NOP NOP", "phase": 0.5 },
 { "name": "ADDR", "wave": "x.=x..=x........", "data": "ROW COL",                     "phase": 0.5 },
 { "name": "DQS",  "wave": "z.......0.1010z." },
 { "name": "DQ",   "wave": "z.........5555z.", "data": "D0 D1 D2 D3" }
]}
```

```wavedrom
{ "assign":[
  ["out",
    ["|",
      ["&", ["~", "a"], "b"],
      ["&", ["~", "b"], "a"]
    ]
  ]
]}
```

```wavedrom
{"reg": [
  { "name": "IPO",   "bits": 8, "attr": "RO" },
  {                  "bits": 7 },
  { "name": "<o>B</o><b>R<i>K</i></b>",   "bits": 5, "attr": "RW", "type": 4 },
  { "name": "CPK",   "bits": 1 },
  { "name": "Clear", "bits": 3 },
  { "bits": 8 }
]}
```


## Extention

```
```

