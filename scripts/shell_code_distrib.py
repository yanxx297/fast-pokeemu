import sys

d = {}

for l in sys.stdin.xreadlines():
    b = l[0:2]
    try:
        d[b] += 1
    except KeyError:
        d[b] = 1

dd = d.items()
dd.sort(lambda x,y: cmp(x, y))

for a,b in dd:
    print a, b
