#!/usr/bin/env bash
# IP secundaria declarada también en Azure; no cambia el gateway ni el DHCP.
set -euo pipefail
interface=$(ip -4 route get 168.63.129.16 | awk '{for(i=1;i<=NF;i++)if($i=="dev"){print $(i+1);exit}}')
[[ -n "$interface" ]]
ip address replace 10.0.0.133/28 dev "$interface"
