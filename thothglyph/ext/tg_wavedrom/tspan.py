import re

def parse(body):
    """
    drom/tspan のロジックに基づき、テキストを解析してtspan構造を返す
    対応: <u>下線</u>, <s>打消線</u>, <b>太字</b>, <i>斜体</i>,
          _{下付き}, ^{上付き}
    """
    if isinstance(body, list):
        return body
    if not isinstance(body, str):
        return [str(body)]

    # 本家 parse.js に近い正規表現
    # <(\/?[usb i]+)> : タグ (u, s, b, i)
    # [_^]\{([^}]+)\} : _{...} または ^{...}
    # [_^](\S)        : _x または ^x
    regex = re.compile(r'<(\/?(?:o|ins|s|b|i|sub|sup|tt)+)>|(\S)')

    result = []
    stack = [result]  # 現在書き込み中のリストを保持するスタック
    last_index = 0

    for match in regex.finditer(body):
        # マッチ前のプレーンテキストを現在の階層に追加
        plain_text = body[last_index:match.start()]
        if plain_text:
            stack[-1].append(plain_text)

        tag, spec_content_short = match.groups()

        if tag:
            # --- HTMLタグ形式の処理 (<u>, <s>, <b>, <i>) ---
            if tag.startswith('/'):
                # 閉じタグ: スタックを一つ戻る
                if len(stack) > 1:
                    stack.pop()
            else:
                # 開始タグ: 新しいtspanを作成し、その中身（子要素リスト）をスタックに積む
                new_tspan = ['tspan', {}]

                # タグに応じたスタイル設定
                if tag == 'o':
                    new_tspan[1]['text-decoration'] = 'overline'
                elif tag == 'ins':
                    new_tspan[1]['text-decoration'] = 'underline'
                elif tag == 's':
                    new_tspan[1]['text-decoration'] = 'line-through'
                elif tag == 'b':
                    new_tspan[1]['font-weight'] = 'bold'
                elif tag == 'i':
                    new_tspan[1]['font-style'] = 'italic'
                elif tag == 'sub':
                    new_tspan[1]['baseline-shift'] = 'sub'
                    new_tspan[1]['font-size'] = '.7em'
                elif tag == 'sup':
                    new_tspan[1]['baseline-shift'] = 'sup'
                    new_tspan[1]['font-size'] = '.7em'
                elif tag == 'tt':
                    new_tspan[1]['font-family'] = 'monospace'

                stack[-1].append(new_tspan)
                stack.append(new_tspan)  # 次のテキストはこのtspanの中に入る
        else:
            # --- 特殊記号形式の処理 (_, ^) ---
            content = spec_content_short
            # stack[-1].append(['tspan', {}, content])
            stack[-1].append(content)

        last_index = match.end()

    # 残りのテキストを追加
    final_text = body[last_index:]
    if final_text:
        stack[-1].append(final_text)

    return result
