---{include} ./sub1.conf.py python
---

# Sub1 Doc Section 1

hogehoge

## Section 1-1

This line include comment -->  %// This is a comment.

## Section 1-2

hogehoge

# Sub1 Doc Section 2

hogehoge

## Section 2-1

hogehoge

## Section 2-2

hogehoge

%#if val == 'A'
# Sub1 Doc Section 3-a

hogehoge
%#elif val == 'B'
# Sub1 Doc Section 3-b

fugafuga
%#else
# Sub1 Doc Section 3-c

piyopiyo
%#end

## Recursive include

```{include} ./sub1.md
```

## Config Inheritance

Hi, {{%author%}}. I am {{%subauthor%}}.
