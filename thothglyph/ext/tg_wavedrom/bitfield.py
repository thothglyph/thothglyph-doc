import math
import html
from . import tspan


def round_val(v):
    return int(round(v))


def get_svg(w, h):
    return ['svg', {
        'class': 'WaveDrom',
        'xmlns': 'http://www.w3.org/2000/svg',
        'width': w,
        'height': h,
        'viewBox': f'0 0 {w} {h}'
    }]


def tt(x, y, obj=None):
    res = {'transform': f'translate({x}{"," + str(y) if y else ""})'}
    if isinstance(obj, dict):
        res.update(obj)
    return res


COLORS = {
    '2': '#ff0000',
    '3': '#aaff00',
    '4': '#00ffd5',
    '5': '#ffbf00',
    '6': '#00ff19',
    '7': '#006aff'
}


def type_style(t):
    t_str = str(t)
    return f';fill:{COLORS[t_str]}' if t_str in COLORS else ''


def norm(obj, other=None):
    res = {}
    for k, v in obj.items():
        try:
            val = int(round(float(v)))
            if val != 0:
                res[k] = val
        except (ValueError, TypeError):
            pass
    if other:
        res.update(other)
    return res


def text_element(body, x, y, rotate=None):
    """
    tspan_parse を利用してリッチテキスト対応したテキスト要素を生成
    """
    props = {'y': 6}
    if rotate is not None:
        props['transform'] = f'rotate({rotate})'

    # tspan_parse の結果を text タグの子要素として展開する
    content = tspan.parse(body)

    # ['g', {transform}, ['text', {props}, ...content]]
    return ['g', tt(round_val(x), round_val(y)),
            ['text', props] + content]


def hline(length, x, y):
    return ['line', norm({'x1': x, 'x2': x + length, 'y1': y, 'y2': y})]


def vline(length, x, y):
    return ['line', norm({'x1': x, 'x2': x, 'y1': y, 'y2': y + length})]


def get_label(val, x, y, step, length, rotate=None):
    if not isinstance(val, int):
        return text_element(val, x, y, rotate)

    res = ['g', {}]
    for i in range(length):
        bit = (val >> i) & 1
        res.append(text_element(
            bit,
            x + step * (length / 2 - i - 0.5),
            y
        ))
    return res


def lane(desc, opt):
    """
    1つのレーン（行）を描画するためのSVG要素（リスト形式）を生成する
    """
    index = opt.get('index', 0)
    vspace = opt.get('vspace', 60)
    hspace = opt.get('hspace', 800)
    margin = opt.get('margin', {})
    hflip = opt.get('hflip', False)
    lanes = opt.get('lanes', 1)
    compact = opt.get('compact', False)
    label_cfg = opt.get('label', {})

    height = vspace - margin.get('top', 0) - margin.get('bottom', 0)
    width = hspace - margin.get('left', 0) - margin.get('right', 0) - 1

    # 配置位置（y座標）の計算
    # hflipがTrueの場合は下から上へ、Falseの場合は上から下へインデックスを割り振る
    idx = index if hflip else (lanes - index - 1)

    tx = margin.get('left', 0)
    if compact:
        ty = round_val(idx * height + margin.get('top', 0))
    else:
        ty = round_val(idx * vspace + margin.get('top', 0))

    # レーンのベースグループ
    # cage(枠線) と label_arr(中身のテキストや塗りつぶし) を結合
    res = ['g', tt(tx, ty),
           cage(desc, opt),
           label_arr(desc, opt)]

    # 左側のラベル (例: "Row 0" など)
    if label_cfg and 'left' in label_cfg:
        lab = label_cfg['left']
        txt = _get_label_text(lab, index)
        res.append(['g', {'text-anchor': 'end'},
                    text_element(txt, -4, round_val(height / 2))])

    # 右側のラベル
    if label_cfg and 'right' in label_cfg:
        lab = label_cfg['right']
        txt = _get_label_text(lab, index)
        res.append(['g', {'text-anchor': 'start'},
                    text_element(txt, width + 4, round_val(height / 2))])

    return res


def _get_label_text(lab, index):
    """ラベルの設定（文字列、数値、配列、辞書）に基づいてテキストを返すヘルパー"""
    if isinstance(lab, str):
        return lab
    elif isinstance(lab, (int, float)):
        return str(int(lab + index))
    elif isinstance(lab, (list, dict)):
        try:
            return str(lab[index])
        except (KeyError, IndexError):
            return str(index)
    return str(index)


def cage(desc, opt):
    """
    ビットフィールドの外枠と区切り線を生成する
    """
    hspace = opt.get('hspace', 800)
    vspace = opt.get('vspace', 60)
    mod = opt.get('mod', 16)
    margin = opt.get('margin', {})
    index = opt.get('index', 0)
    vflip = opt.get('vflip', False)

    width = hspace - margin.get('left', 0) - margin.get('right', 0) - 1
    height = vspace - margin.get('top', 0) - margin.get('bottom', 0)

    # 線の基本スタイル
    res = ['g', {
        'stroke': 'black',
        'stroke-width': 1,
        'stroke-linecap': 'round'
    }]

    # 外枠の描画 (Sparseモードの特殊処理含む)
    if opt.get('sparse'):
        # uneven かつ 奇数ビット数の場合の端点処理
        skip_edge = all(opt.get('uneven'),
                        (opt.get('bits', 0) % 2 == 1),
                        (index == (opt.get('lanes', 1) - 1)))

        if skip_edge:
            if vflip:
                res.extend([
                    hline(width - (width / mod), 0, 0),
                    hline(width - (width / mod), 0, height)
                ])
            else:
                res.extend([
                    hline(width - (width / mod), width / mod, 0),
                    hline(width - (width / mod), width / mod, height)
                ])
        elif not opt.get('compact'):
            res.extend([
                hline(width, 0, 0),
                hline(width, 0, height),
                vline(height, width if vflip else 0, 0)
            ])
    else:
        # 通常モードの外枠
        res.extend([
            hline(width, 0, 0),
            vline(height, width if vflip else 0, 0),
            hline(width, 0, height)
        ])

    # 内部の区切り線の描画
    i = index * mod
    delta = 1 if vflip else -1
    j = 0 if vflip else mod

    if opt.get('sparse'):
        for k in range(mod + 1):
            xj = j * (width / mod)

            # フィールドが空でない場合の垂直線
            if (not skip_field(desc, opt, i) and k != 0) or \
               (not skip_field(desc, opt, i + 1) and k != mod):

                # フィールドの境界（MSB+1）ならフルサイズ、それ以外は短い目印
                if k == 0 or k == mod or any(e.get('msb', -1) + 1 == i for e in desc):
                    res.append(vline(height, xj, 0))
                else:
                    # ビット間の小さな刻み目
                    res.append(vline(int(height) >> 3, xj, 0))
                    res.append(vline(-(int(height) >> 3), xj, height))

            # Compactモード時の水平線
            if opt.get('compact') and k != 0 and not skip_field(desc, opt, i):
                res.append(hline(width / mod, xj, 0))
                res.append(hline(width / mod, xj, height))

            i += 1
            j += delta
    else:
        # 非Sparseモード（通常）の区切り線
        for k in range(mod):
            xj = j * (width / mod)
            if k == 0 or any(e.get('lsb', -1) == i for e in desc):
                res.append(vline(height, xj, 0))
            else:
                res.append(vline(int(height) >> 3, xj, 0))
                res.append(vline(-(int(height) >> 3), xj, height))

            i += 1
            j += delta

    return res


def skip_field(desc, opt, global_index):
    """
    Compactモード時に、空のフィールドをスキップするか判定するヘルパー
    """
    if not opt.get('compact'):
        return False

    def is_empty(e):
        return e.get('name') is None and e.get('type') is None

    # 指定されたビット位置が空のフィールド内に含まれているかチェック
    for e in desc:
        if is_empty(e) and e.get('lsb', -1) < global_index <= (e.get('msb', -1) + 1):
            return True
    return False


def label_arr(desc, opt):
    """
    各フィールドのビット番号、名称、背景色、属性を描画する
    """
    margin = opt.get('margin', {})
    hspace = opt.get('hspace', 800)
    vspace = opt.get('vspace', 60)
    mod = opt.get('mod', 16)
    index = opt.get('index', 0)
    fontsize = opt.get('fontsize', 14)
    vflip = opt.get('vflip', False)
    trim = opt.get('trim')
    compact = opt.get('compact', False)
    offset = opt.get('offset', 0)

    width = hspace - margin.get('left', 0) - margin.get('right', 0) - 1
    height = vspace - margin.get('top', 0) - margin.get('bottom', 0)
    step = width / mod

    # 4つの描画レイヤー（グループ）
    blanks = ['g']  # 背景色
    bits = ['g', tt(round_val(step / 2), -round_val(0.5 * fontsize + 4))]  # ビット番号
    names = ['g', tt(round_val(step / 2), round_val(0.5 * height + 0.4 * fontsize - 6))]  # フィールド名
    attrs = ['g', tt(round_val(step / 2), round_val(height + 0.7 * fontsize - 2))]  # 属性

    for e in desc:
        lsbm = 0
        msbm = mod - 1
        lsb = index * mod
        msb = (index + 1) * mod - 1

        # このレーンにフィールドが含まれているか判定
        if int(e['lsb'] // mod) == index:
            lsbm = e['lsbm']
            lsb = e['lsb']
            if int(e['msb'] // mod) == index:
                msb = e['msb']
                msbm = e['msbm']
        else:
            if int(e['msb'] // mod) == index:
                msb = e['msb']
                msbm = e['msbm']
            elif not (lsb > e['lsb'] and msb < e['msb']):
                continue

        # 1. ビット番号の配置 (Compactモード以外)
        if not compact:
            bits.append(text_element(
                lsb + offset,
                step * (lsbm if vflip else (mod - lsbm - 1)),
                0  # ?
            ))
            if lsbm != msbm:
                bits.append(text_element(
                    msb + offset,
                    step * (msbm if vflip else (mod - msbm - 1)),
                    0  # ?
                ))

        # 2. フィールド名の配置
        if e.get('name') is not None:
            # trim設定があればテキストを切り詰める
            display_name = trim_text(e['name'], step * e.get('bits', 1), trim) \
                if trim else e['name']

            # 中央位置の計算
            center_pos = (msbm + lsbm) / 2
            x_pos = step * (center_pos if vflip else (mod - center_pos - 1))

            names.append(get_label(
                display_name,
                x_pos,
                0,
                step,
                e.get('bits', 1),
                e.get('rotate')
            ))

        # 3. 背景の塗りつぶし (type指定がある場合)
        if e.get('name') is None or e.get('type') is not None:
            if not (compact and e.get('type') is None):
                rect_props = norm({
                    'x': step * (lsbm if vflip else (mod - msbm - 1)),
                    'width': step * (msbm - lsbm + 1),
                    'height': height
                }, {
                    'field': html.escape(str(e.get('name', ''))),
                    'style': 'fill-opacity:0.1' + type_style(e.get('type'))
                })
                # カスタムrect属性があれば上書き
                if 'rect' in e:
                    rect_props.update(e['rect'])
                blanks.append(['rect', rect_props])

        # 4. 属性 (attr) の配置
        if e.get('attr') is not None:
            attrs.append(get_attr(e, opt, step, lsbm, msbm))

    return ['g', blanks, bits, names, attrs]


def trim_text(text, available_space, char_width):
    """テキストが入り切らない場合に '...' で省略する"""
    if not isinstance(text, str):
        return text

    text_width = len(text) * char_width
    if text_width <= available_space:
        return text

    end = len(text) - ((text_width - available_space) / char_width) - 3
    if end > 0:
        return text[:round_val(end)] + '...'
    return text[0:1] + '...'


def get_attr(e, opt, step, lsbm, msbm):
    """フィールドの下に表示される属性テキストを生成する"""
    vflip = opt.get('vflip', False)
    mod = opt.get('mod', 16)
    fontsize = opt.get('fontsize', 14)

    center_pos = (msbm + lsbm) / 2
    x = step * (center_pos if vflip else (mod - center_pos - 1))

    attrs = e.get('attr')
    if not isinstance(attrs, list):
        return get_label(attrs, x, 0, step, e.get('bits', 1))

    res = ['g', {}]
    for i, a in enumerate(attrs):
        if a is not None:
            res.append(get_label(a, x, fontsize * i, step, e.get('bits', 1)))
    return res


def compact_labels(desc, opt):
    """
    Compactモード時に、全ビットのインデックスラベルを一括生成する
    """
    hspace = opt.get('hspace', 800)
    margin = opt.get('margin', {})
    mod = opt.get('mod', 16)
    fontsize = opt.get('fontsize', 14)
    vflip = opt.get('vflip', False)
    legend = opt.get('legend')
    offset = opt.get('offset', 0)

    width = hspace - margin.get('left', 0) - margin.get('right', 0) - 1
    step = width / mod

    # ラベルのベースグループ。Legendがある場合は位置を調整
    tx = margin.get('left', 0)
    ty = 0 if legend else -3
    res = ['g', tt(tx, ty)]

    # どの位置にラベルを描画すべきかのマスクを取得
    mask = get_label_mask(desc, mod)

    for i in range(mod):
        # vflip（ビット0が左か右か）に応じてインデックスを決定
        idx = i if vflip else (mod - i - 1)

        if idx < len(mask) and mask[idx]:
            # ラベルテキストの生成
            res.append(text_element(
                idx + offset,
                step * (i + 0.5),
                0.5 * fontsize + 4
            ))

    return res


def get_label_mask(desc, mod):
    """
    各フィールドの開始(LSB)と終了(MSB)の位置を特定し、
    ラベルを表示すべきインデックスの真偽値リストを返す
    """
    mask = [False] * mod
    idx = 0

    for e in desc:
        # フィールドの開始位置
        mask[idx % mod] = True

        bits = e.get('bits', 0)
        idx += bits

        # フィールドの終了位置（次のフィールドの直前）
        if idx > 0:
            mask[(idx - 1) % mod] = True

    return mask


def get_max_attributes(desc):
    """全フィールドの中で最大の属性数（行数）を返す"""
    max_attr = 0
    for field in desc:
        attr = field.get('attr')
        if attr is None:
            count = 0
        elif isinstance(attr, list):
            count = len(attr)
        else:
            count = 1
        max_attr = max(max_attr, count)
    return max_attr


def get_total_bits(desc):
    """全フィールドの合計ビット数を計算する"""
    return sum(field.get('bits', 0) for field in desc)


def opt_defaults(opt):
    """オプションのデフォルト値を設定する"""
    if not isinstance(opt, dict):
        opt = {}

    # 基本設定
    opt['hspace'] = opt.get('hspace', 800)
    opt['lanes'] = opt.get('lanes', 1)
    opt['fontsize'] = opt.get('fontsize', 14)
    opt['fontfamily'] = opt.get('fontfamily', 'sans-serif')
    opt['fontweight'] = opt.get('fontweight', 'normal')
    opt['compact'] = opt.get('compact', False)
    opt['hflip'] = opt.get('hflip', False)
    opt['vflip'] = opt.get('vflip', False)
    opt['uneven'] = opt.get('uneven', False)
    opt['offset'] = opt.get('offset', 0)

    # マージンの初期化
    margin = opt.get('margin', {})
    opt['margin'] = margin

    return opt


def render(desc, opt=None):
    """
    ビットフィールド記述(desc)からSVG構造(リスト形式)を生成するメイン関数
    """
    opt = opt_defaults(opt)
    max_attributes = get_max_attributes(desc)

    # 垂直方向のスペース計算
    if 'vspace' not in opt:
        opt['vspace'] = (max_attributes + 4) * opt['fontsize']

    # ビット数の確定
    if 'bits' not in opt:
        opt['bits'] = get_total_bits(desc)

    # マージンの詳細設定
    margin = opt['margin']
    label_cfg = opt.get('label', {})

    if 'right' not in margin:
        margin['right'] = round_val(0.1 * opt['hspace']) if 'right' in label_cfg else 4
    if 'left' not in margin:
        margin['left'] = round_val(0.1 * opt['hspace']) if 'left' in label_cfg else 4

    if 'top' not in margin:
        margin['top'] = 1.5 * opt['fontsize']
        if 'bottom' not in margin:
            margin['bottom'] = opt['fontsize'] * max_attributes + 4
    else:
        if 'bottom' not in margin:
            margin['bottom'] = 4

    # 全体の高さ計算
    width = opt['hspace']
    lanes = opt['lanes']
    height = opt['vspace'] * lanes

    if opt['compact']:
        # Compact時はマージンを各行で共有するため高さを削る
        height -= (lanes - 1) * (margin['top'] + margin['bottom'])

    legend = opt.get('legend')
    if legend:
        height += 12

    # SVGのルートグループ構築
    # 0.5のオフセットは線のボケを防ぐためのWaveDrom特有の処理
    res_root = ['g', tt(0.5, 12.5 if legend else 0.5, {
        'text-anchor': 'middle',
        'font-size': opt['fontsize'],
        'font-family': opt['fontfamily'],
        'font-weight': opt['fontweight']
    })]

    # 各フィールドの絶対位置(lsb/msb)と相対位置(lsbm/msbm)を事前計算
    lsb = 0
    mod = math.ceil(opt['bits'] / lanes)
    opt['mod'] = mod

    for e in desc:
        e['lsb'] = lsb
        e['lsbm'] = lsb % mod
        lsb += e.get('bits', 0)
        e['msb'] = lsb - 1
        e['msbm'] = e['msb'] % mod

    # 各レーンの描画
    for i in range(lanes):
        opt['index'] = i
        res_root.append(lane(desc, opt))

    # Compactモード用ラベルの追加
    if opt['compact']:
        res_root.append(compact_labels(desc, opt))

    # 凡例(Legend)の追加（必要に応じて get_legend_items を実装）
    if legend:
        # ここに get_legend_items(opt) の呼び出しを追加可能
        res_root.append(get_legend_items(opt))
        pass

    # 最終的なSVGタグで包んで返す
    svg_tag = get_svg(width, height)
    svg_tag.append(res_root)
    return svg_tag


def get_legend_items(opt):
    """
    SVGの下部に表示される凡例（カラーチップとラベル）を生成する
    """
    hspace = opt.get('hspace', 800)
    margin = opt.get('margin', {})
    fontsize = opt.get('fontsize', 14)
    legend = opt.get('legend', {})  # 例: {"Reserved": 2, "Read-Only": 3}

    width = hspace - margin.get('left', 0) - margin.get('right', 0) - 1

    # 凡例全体のグループ（マージン分右に寄せ、少し上に配置）
    items = ['g', tt(margin.get('left', 0), -10)]

    # レイアウト用の定数
    legend_square_padding = 36
    legend_name_padding = 24

    # 凡例が中央揃えになるように開始位置(x)を計算
    # 凡例の個数 * (四角形+テキストの幅) を全体の幅から引いて半分にする
    total_legend_width = len(legend) * (legend_square_padding + legend_name_padding)
    x = (width / 2) - (total_legend_width / 2)

    for key, value in legend.items():
        # カラーチップ（小さな四角形）
        items.append(['rect', norm({
            'x': x,
            'width': 12,
            'height': 12
        }, {
            'style': 'fill-opacity:0.15; stroke: #000; stroke-width: 1.2;' + type_style(value)
        })])

        x += legend_square_padding

        # 凡例のテキスト
        items.append(text_element(
            key,
            x,
            0.1 * fontsize + 4
        ))

        x += legend_name_padding

    return items


def to_svg_string(element):
    """
    JSON形式のリスト構造をSVG文字列(XML)に変換する
    """
    # 1. 単純なテキストや数値の場合
    if isinstance(element, (str, int, float)):
        return str(element)

    # 2. リスト形式のタグ処理: ['tag', {props}, child1, ...]
    if isinstance(element, list) and len(element) > 0:
        tag = element[0]
        props = {}
        children = []

        # 2番目の要素が辞書なら属性として扱う
        start_idx = 1
        if len(element) > 1 and isinstance(element[1], dict):
            props = element[1]
            start_idx = 2

        # 残りの要素はすべて子要素（再帰的に処理）
        children = element[start_idx:]

        # 属性文字列の組み立て
        attr_parts = []
        for k, v in props.items():
            # 属性値にリストが含まれる場合（viewBoxなど）を考慮
            if isinstance(v, list):
                v = " ".join(map(str, v))
            attr_parts.append(f'{k}="{v}"')

        attr_str = " " + " ".join(attr_parts) if attr_parts else ""

        # 子要素の組み立て
        inner_html = "".join([to_svg_string(c) for c in children])

        # 閉じタグの生成（中身が空なら自己完結タグでも良いが、互換性のためフル形式）
        return f'<{tag}{attr_str}>{inner_html}</{tag}>'

    return ""


# # 1. データの定義
# fields = [
#     { "name": "IPO",   "bits": 8, "attr": "RO" },
#     {                  "bits": 7 },
#     { "name": "BRK",   "bits": 5, "attr": "RW", "type": 4 },
#     { "name": "CPK",   "bits": 1 },
#     { "name": "Clear", "bits": 3 },
#     { "bits": 8 }
# ]
#
# # 2. オプションの定義
# options = {
#     'lanes': 1,
#     'compact': True,
#     'legend': {'System': 4, 'Peripheral': 2}
# }
# options = {}
#
# # 3. レンダリング実行
# svg_list = render(fields, options)
#
# # 4. XML文字列へ変換 (前述の to_svg_string を使用)
# svg_output = to_svg_string(svg_list)
# print(svg_output)
