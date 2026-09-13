chroot /run/ubuntu /bin/sh <<'EOF'
nohup sh /usr/local/share/t630/test-audio-cold-order.sh </dev/null >/var/log/t630-audio-cold-calibrated.log 2>&1 &
echo 'Manual calibrated first-load test dispatched.'
EOF
