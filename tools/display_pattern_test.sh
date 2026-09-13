echo 'Temporary display test: existing connector 55, CRTC 113, advertised mode #0.'
sleep 20 | timeout 25 chroot /run/ubuntu /usr/bin/modetest -M msm_drm -s '55@113:#0'
echo MODETEST_EXIT=$?
echo RECENT_KERNEL_MESSAGES
dmesg | tail -35
