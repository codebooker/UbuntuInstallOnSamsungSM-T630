#!/usr/bin/env python3
"""Read-only Waydroid host-kernel prerequisite check for the SM-T630."""
import gzip
from pathlib import Path
import sys


REQUIRED = {
    'CONFIG_SYSVIPC', 'CONFIG_NAMESPACES', 'CONFIG_UTS_NS', 'CONFIG_IPC_NS', 'CONFIG_USER_NS',
    'CONFIG_PID_NS', 'CONFIG_NET_NS', 'CONFIG_CGROUPS', 'CONFIG_CGROUP_PIDS',
    'CONFIG_CGROUP_DEVICE', 'CONFIG_MEMCG', 'CONFIG_VETH', 'CONFIG_BRIDGE',
    'CONFIG_ASHMEM', 'CONFIG_ANDROID_BINDER_IPC', 'CONFIG_ANDROID_BINDERFS',
    'CONFIG_OVERLAY_FS', 'CONFIG_SECCOMP', 'CONFIG_SECCOMP_FILTER',
    'CONFIG_NF_CONNTRACK', 'CONFIG_NF_NAT', 'CONFIG_IP_NF_IPTABLES',
    'CONFIG_IP_NF_FILTER', 'CONFIG_IP_NF_NAT',
    'CONFIG_IP_NF_TARGET_MASQUERADE', 'CONFIG_IP_NF_MANGLE',
    'CONFIG_NETFILTER_XT_TARGET_CHECKSUM', 'CONFIG_NETFILTER_XT_MATCH_OWNER',
}


def parse(text):
    values = {}
    for line in text.splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            key, value = line.split('=', 1)
            values[key] = value
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line.split()[1]] = 'n'
    return values


def check(text):
    values = parse(text)
    return sorted(key for key in REQUIRED if values.get(key) not in ('y', 'm'))


def read_config(path):
    if str(path).endswith('.gz'):
        with gzip.open(path, 'rt') as stream:
            return stream.read()
    return Path(path).read_text()


def main():
    if len(sys.argv) > 2:
        raise SystemExit('Usage: check_waydroid_kernel.py [KERNEL_CONFIG]')
    path = Path(sys.argv[1]) if len(sys.argv) == 2 else Path('/proc/config.gz')
    missing = check(read_config(path))
    if missing:
        print('Missing Waydroid kernel features:')
        for feature in missing:
            print(f'  {feature}')
        return 1
    print('Waydroid kernel prerequisites are enabled.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
