#!/usr/bin/env bash
# Chạy locust nhiều mức user cho từng số replica, lưu CSV vào results/.
#   OUT=results/run2 bash loadtest/run_levels.sh   # mặc định: replicas "3 5", users "10 25 50 100"
# Biến môi trường: OUT, REPLICAS, USERS, DURATION, HOST, KUBECTL, LOCUST
set -euo pipefail
cd "$(dirname "$0")/.."

REPLICAS=${REPLICAS:-"3 5"}
USERS=${USERS:-"10 25 50 100"}
DURATION=${DURATION:-90s}
HOST=${HOST:-http://localhost:8088}
KUBECTL=${KUBECTL:-"/mnt/c/Program Files/Docker/Docker/resources/bin/kubectl.exe"}
LOCUST=${LOCUST:-locust}
COOLDOWN=20
OUT=${OUT:-results/run}

mkdir -p "$OUT/locust"
TIMELINE=$OUT/timeline.csv
echo "replicas,users,start_unix,end_unix" > "$TIMELINE"

for rep in $REPLICAS; do
    echo ">>> scale replicas=$rep"
    "$KUBECTL" scale deployment/vn-traffic-api --replicas="$rep"
    "$KUBECTL" rollout status deployment/vn-traffic-api --timeout=180s
    sleep "$COOLDOWN"

    for u in $USERS; do
        name="r${rep}_u${u}"
        echo ">>> $name"
        start=$(date +%s)
        "$LOCUST" -f loadtest/locustfile.py --host "$HOST" --headless \
            -u "$u" -r "$(( u / 5 > 1 ? u / 5 : 1 ))" -t "$DURATION" \
            --csv "$OUT/locust/$name" --only-summary 2>&1 | tail -3 || true
        end=$(date +%s)
        echo "$rep,$u,$start,$end" >> "$TIMELINE"
        sleep "$COOLDOWN"
    done
done
echo ">>> xong, CSV ở $OUT/locust/, mốc thời gian ở $TIMELINE"
