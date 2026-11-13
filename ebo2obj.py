#!/usr/bin/env python3
"""
ebo2obj.py - NBA Live 06 head morph (.ebo) + neutral base mesh (.obj) -> player head .obj

사용법:
    python ebo2obj.py base.obj damilicB.ebo                  -> damilicB.obj
    python ebo2obj.py base.obj damilicB.ebo -o out.obj
    python ebo2obj.py base.obj a.ebo b.ebo c.ebo -d out_dir  (여러 개 일괄 변환)
    python ebo2obj.py base.obj a.ebo -s 0.5                  (델타 강도 조절)

원리:
    .ebo 의 coord 스트림 = 정점 N개 x (dx,dy,dz) float32 (little-endian) 델타.
    기본(neutral) 메시 정점에 더하면 선수별 얼굴 형태가 된다.
    면/UV/법선(vn)은 기본 메시 것을 그대로 쓴다 (법선은 뷰어에서 재계산 권장).

    헤더 위치(분석 결과): 0x11c = coord 스트림 크기(바이트), 0x120 = 파일 내 오프셋.
"""
import argparse
import os
import struct
import sys


def read_deltas(path, n_verts):
    d = open(path, "rb").read()
    if d[:3] != b"EBO":
        raise ValueError("EBO 헤더가 아닙니다: %s" % path)
    size, off = struct.unpack_from("<II", d, 0x11C)
    if size != n_verts * 12:
        raise ValueError(
            "%s: coord 스트림 크기 %d != 정점 %d x 12 (기본 메시와 정점 수가 다릅니다)"
            % (path, size, n_verts)
        )
    if off + size > len(d):
        raise ValueError("%s: 오프셋/크기가 파일 범위를 벗어났습니다" % path)
    flat = struct.unpack_from("<%df" % (n_verts * 3), d, off)
    return [flat[i:i + 3] for i in range(0, len(flat), 3)]


def convert(base_obj, ebo, out, scale=1.0):
    lines = open(base_obj, encoding="utf-8").read().splitlines(True)
    n_verts = sum(1 for l in lines if l.startswith("v "))
    deltas = read_deltas(ebo, n_verts)

    name = os.path.splitext(os.path.basename(ebo))[0]
    res, i = [], 0
    for l in lines:
        if l.startswith("v "):
            x, y, z = (float(t) for t in l.split()[1:4])
            dx, dy, dz = deltas[i]
            i += 1
            res.append("v %.9g %.9g %.9g\n" % (x + dx * scale, y + dy * scale, z + dz * scale))
        elif l.startswith("# NBA"):
            res.append("# %s = base mesh + .ebo coord deltas x%g (%d verts)\n" % (name, scale, n_verts))
        else:
            res.append(l)
    with open(out, "w", encoding="utf-8") as f:
        f.write("".join(res))
    return n_verts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("base", help="기본(neutral) 메시 .obj")
    ap.add_argument("ebo", nargs="+", help="변환할 .ebo 파일(들)")
    ap.add_argument("-o", "--out", help="출력 파일 (ebo 1개일 때)")
    ap.add_argument("-d", "--outdir", help="출력 폴더 (기본: ebo 와 같은 폴더)")
    ap.add_argument("-s", "--scale", type=float, default=1.0, help="델타 배율 (기본 1.0)")
    a = ap.parse_args()

    if a.out and len(a.ebo) > 1:
        ap.error("-o 는 ebo 가 1개일 때만 쓸 수 있습니다 (여러 개는 -d)")
    if a.outdir:
        os.makedirs(a.outdir, exist_ok=True)

    rc = 0
    for e in a.ebo:
        base = os.path.splitext(os.path.basename(e))[0] + ".obj"
        out = a.out or os.path.join(a.outdir or os.path.dirname(os.path.abspath(e)), base)
        try:
            n = convert(a.base, e, out, a.scale)
            print("OK  %s -> %s (%d verts)" % (e, out, n))
        except Exception as ex:
            print("ERR %s" % ex, file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
