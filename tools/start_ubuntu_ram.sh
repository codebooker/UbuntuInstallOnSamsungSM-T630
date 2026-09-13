set -e
test ! -e /run/ubuntu
mkdir /run/ubuntu
tar -xzf /run/ubuntu-base-24.04.5-arm64.tar.gz -C /run/ubuntu
echo UBUNTU_RELEASE
chroot /run/ubuntu /bin/bash -c 'cat /etc/os-release; echo ARCHITECTURE; uname -m; dpkg --print-architecture; echo LIBC; ldd --version | head -1; echo SHELL; bash --version | head -1; echo PACKAGES; dpkg-query -W base-files libc6 bash apt; echo ID; id'
echo KERNEL_PID1
tr '\000' ' ' </proc/1/cmdline
echo
echo STORAGE
df -h /run
cat /proc/mounts
