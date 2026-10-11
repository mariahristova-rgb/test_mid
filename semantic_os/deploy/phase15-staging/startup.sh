#!/bin/sh
set -eu
# New isolated VM only. No customer database or credentials are transferred.
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq docker.io docker-compose iptables ca-certificates python3
systemctl enable --now docker
install -d -m 0700 /opt/testmid-phase15
# Scope billing egress protection to this new VM's public Docker replies.
# One run is bounded by the Compute Engine fixed termination timestamp.
edge=$(ip route show default | awk '{print $5; exit}')
test -n "$edge"
iptables -N TESTMID_BUDGET 2>/dev/null || true
iptables -F TESTMID_BUDGET
iptables -A TESTMID_BUDGET -o "$edge" -p tcp -m multiport --sports 80,443 -m quota --quota 1000000000 -j RETURN
iptables -A TESTMID_BUDGET -o "$edge" -p tcp -m multiport --sports 80,443 -j DROP
iptables -A TESTMID_BUDGET -j RETURN
iptables -I DOCKER-USER 1 -j TESTMID_BUDGET
# No application is started until its scanned image and reviewed config arrive.
