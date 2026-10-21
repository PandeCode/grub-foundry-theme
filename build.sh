#!/usr/bin/env bash
# build.sh [--scale S] [--background FILE] [--mono TTF] [gen.py options] OUT
# writes a complete grub theme to OUT; needs python3 with pillow, grub-mkfont,
# and ffmpeg when --background is given. other options go to gen.py, see
# gen.py --help
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
scale=1
background=
mono=
pass=()

while [ $# -gt 1 ]; do
    case $1 in
    --scale) scale=$2 ;;
    --background) background=$2 ;;
    --mono) mono=$2 ;;
    *) pass+=("$1" "$2") ;;
    esac
    shift 2
done

if [ $# -ne 1 ]; then
    echo "usage: $0 [--scale S] [--background FILE] [--mono TTF] [gen.py options] OUT" >&2
    exit 1
fi
out=$1
mkdir -p "$out"

# the same rounding as gen.py
size() {
    python3 -c "print(max(1, round($1 * $scale)))"
}

grub-mkfont -s "$(size 16)" -n "Titillium Web" -o "$out/regular.pf2" "$here/fonts/TitilliumWeb-Regular.ttf"
grub-mkfont -s "$(size 15)" -n "Titillium Web SemiBold" -o "$out/semibold.pf2" "$here/fonts/TitilliumWeb-SemiBold.ttf"

if [ -n "$mono" ]; then
    grub-mkfont -s "$(size 16)" -o "$out/mono.pf2" "$mono"
fi
if [ -n "$background" ]; then
    # a still for videos, a png for any image
    ffmpeg -nostdin -loglevel error -y -i "$background" -frames:v 1 "$out/background.png"
fi

python3 "$here/gen.py" "$out" --scale "$scale" "${pass[@]}"
