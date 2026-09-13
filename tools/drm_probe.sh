echo MSM_DRIVER
chroot /run/ubuntu /usr/bin/modetest -M msm -c -p
echo MSM_DRM_DRIVER
chroot /run/ubuntu /usr/bin/modetest -M msm_drm -c -p
