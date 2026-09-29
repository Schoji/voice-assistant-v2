#!/bin/bash
# One-off, as root on the pi: lets aleksy-client drive NetworkManager and turns
# its fallback hotspot into a captive portal. Safe to run again.
#   sudo ./setup-wifi.sh [user]
set -euo pipefail

USER_NAME=${1:-schoji}
HOTSPOT_IP=10.42.0.1 # keep in sync with HOTSPOT_IP in client/config.py
PANEL_PORT=5000      # and PANEL_PORT

# dnsmasq-base serves dhcp/dns on the hotspot, nft sends port 80 to the panel, iw tells if anyone is connected
apt-get install -y dnsmasq-base nftables iw

# the hotspot password stays on the device, not in the repo
PASSWORD_FILE=/etc/aleksy/hotspot-password # keep in sync with HOTSPOT_PASSWORD_FILE
install -d -m 755 /etc/aleksy
if [ ! -s "$PASSWORD_FILE" ]; then
    read -rsp "hasło do hotspotu Aleksy (min. 8 znaków): " PASSWORD; echo
    [ ${#PASSWORD} -ge 8 ] || { echo "za krótkie, WPA2 wymaga co najmniej 8 znaków" >&2; exit 1; }
    (umask 077; printf '%s' "$PASSWORD" > "$PASSWORD_FILE")
fi
chown "root:$USER_NAME" "$PASSWORD_FILE"
chmod 640 "$PASSWORD_FILE"

# the service runs without a login session, so polkit would refuse every nmcli change
cat > /etc/polkit-1/rules.d/50-aleksy-network.rules <<EOF
polkit.addRule(function (action, subject) {
    if (action.id.indexOf("org.freedesktop.NetworkManager.") === 0 && subject.user === "$USER_NAME") {
        return polkit.Result.YES;
    }
});
EOF

# NetworkManager's dnsmasq for shared connections reads this dir: on the hotspot
# every name resolves to the pi, so phones open the wi-fi page by themselves
mkdir -p /etc/NetworkManager/dnsmasq-shared.d
cat > /etc/NetworkManager/dnsmasq-shared.d/aleksy-captive.conf <<EOF
address=/#/$HOTSPOT_IP
EOF

# phones check for a captive portal on port 80, the panel listens on $PANEL_PORT
cat > /etc/NetworkManager/dispatcher.d/90-aleksy-portal <<EOF
#!/bin/sh
[ "\$CONNECTION_ID" = aleksy-hotspot ] || exit 0
case "\$2" in
    up)
        nft delete table ip aleksy_portal 2>/dev/null
        nft -f - <<NFT
table ip aleksy_portal {
    chain prerouting {
        type nat hook prerouting priority dstnat;
        iifname "\$1" tcp dport 80 redirect to :$PANEL_PORT
    }
}
NFT
        ;;
    down)
        nft delete table ip aleksy_portal 2>/dev/null || true
        ;;
esac
EOF
chmod 755 /etc/NetworkManager/dispatcher.d/90-aleksy-portal

systemctl restart polkit
echo "gotowe: restart aleksy-client, żeby watchdog Wi-Fi ruszył z nowymi uprawnieniami"
