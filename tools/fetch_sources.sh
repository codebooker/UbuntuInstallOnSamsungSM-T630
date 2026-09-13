#!/bin/sh
# Fetch third-party build sources at the revisions used for this port.
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

fetch_one() {
    destination=$1
    url=$2
    revision=$3
    if [ ! -d "$destination/.git" ]; then
        test ! -e "$destination"
        git clone --filter=blob:none --no-checkout "$url" "$destination"
    fi
    git -C "$destination" fetch --depth=1 origin "$revision"
    git -C "$destination" checkout --detach "$revision"
    test "$(git -C "$destination" rev-parse HEAD)" = "$revision"
}

fetch_one "$root/tools/aosp-mkbootimg" \
    https://android.googlesource.com/platform/system/tools/mkbootimg \
    d2bb0af5ba6d3198a3e99529c97eda1be0b5a093
fetch_one "$root/tools/aosp-avb" \
    https://android.googlesource.com/platform/external/avb \
    c5066a96caa7bf4150c0a8cc8cc14ab81733fdc7
fetch_one "$root/tools/heimdall-source" \
    https://git.sr.ht/~grimler/Heimdall \
    8f3044db985fd9710038f04886b51240ddbb2834
fetch_one "$root/ubuntu/pd-mapper-source" \
    https://github.com/linux-msm/pd-mapper.git \
    5ecd2fe926aca7abfe40724177f63b942cff3947

echo "Pinned source checkouts are ready."
