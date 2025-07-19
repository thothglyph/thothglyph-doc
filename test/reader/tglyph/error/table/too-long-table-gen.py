import os

result = '''
* 740 x 1 : OK
* 750 x 1 : NG

* 435 x 4 = 1740 : OK
* 436 x 4 = 1744 : NG

* 291 x 6 = 1746 : OK
* 292 x 6 = 1752 : NG

* 218 x 8 = 1746 : OK
* 219 x 8 = 1752 : NG
'''

def main():
    nrows, ncols = 219, 8
    rows = []
    for ri in range(nrows):
        cols = [str(ci + ri * ncols) for ci in range(ncols)]
        row = '| {row} |'.format(row=' | '.join(cols))
        rows.append(row)
    s = '\n'.join(rows)
    cur_dir = os.path.dirname(__file__)
    ofname = os.path.join(cur_dir, 'too-long-table.tglyph')
    with open(ofname, 'w') as f:
        # f.write(result)
        f.write(s)


main()
