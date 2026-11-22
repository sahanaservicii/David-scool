# Мониторинг WAN и правила Block-Cam191-WAN — 20.11.2026

Интервал 10 мин, 7 замеров (0..60 мин). Только чтение.

## Замер 1 — 2026-11-20 15:54:54 UTC

### Router status
### system
{
	"kernel": "6.12.94",
	"hostname": "Rahmaninova-49",
	"system": "ARMv8 Processor rev 4",
	"model": "Xiaomi AX3600",
	"board_name": "xiaomi,ax3600",
	"rootfs_type": "squashfs",
	"release": {
		"distribution": "OpenWrt",
		"version": "25.12.5",
		"firmware_url": "https://downloads.openwrt.org/",
		"revision": "r33051-f5dae5ece4",
		"target": "qualcommax/ipq807x",
		"description": "OpenWrt 25.12.5 r33051-f5dae5ece4",
		"builddate": "1782737960"
	}
}
### uptime
 18:54:55 up 3 days, 23:55,  load average: 0.00, 0.01, 0.04
### memory
              total        used        free      shared  buff/cache   available
Mem:         414252      279440       38604        6372       96208       77376
Swap:             0           0           0
### disk
Filesystem                Size      Used Available Use% Mounted on
overlayfs:/overlay      174.0M     32.4M    137.0M  19% /
tmpfs                   202.3M      6.2M    196.0M   3% /tmp
### wan
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 1063,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
### wifi
phy0-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:24
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: VHT80
         Center Channel 1: 42 2: unknown
         Tx-Power: 23 dBm  Link Quality: 70/70
         Signal: 0 dBm  Noise: -104 dBm
         Bit Rate: unknown
         Encryption: SAE / WPA-PSK / WPA-PSK-SHA256 (CCMP)
         Type: nl80211  HW Mode(s): 802.11ac/n
         Hardware: 0x168c:0x0050 0x0000:0x0000 [Qualcomm Atheros QCA9887]
         TX power offset: none
         Channel offset: none
         Supports VAPs: yes  PHY name: phy0

phy1-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:23
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: HE80
         Center Channel 1: 42 2: unknown
         Tx-Power: 30 dBm  Link Quality: 49/70
         Signal: -61 dBm  Noise: -109 dBm
### dhcp leases
1795226885 f4:20:15:29:f7:8a 192.168.1.219 SaluteTV 01:f4:20:15:29:f7:8a
1795226159 b4:60:ed:6a:c9:b5 192.168.1.233 yeelink-light-colorb_miapC9B5 *
1795212200 80:3f:5d:30:99:4e 192.168.1.223 * *
1795233206 bc:35:1e:8d:5c:31 192.168.1.171 lwip0 *
1795232904 ce:d8:43:0a:0e:62 192.168.1.175 miwifi-rd10m 01:ce:d8:43:0a:0e:62
1795222373 60:3d:61:59:98:da 192.168.1.140 * ff:61:59:98:da:00:01:00:01:c7:92:bc:8e:60:3d:71:59:98:da
1795230088 d8:c8:0c:cc:d9:1e 192.168.1.213 * *
1795214899 04:f7:78:2a:66:81 192.168.1.126 * 01:04:f7:78:2a:66:81
1795230628 bc:35:1e:4c:48:7e 192.168.1.139 * *
1795233175 bc:35:1e:8d:60:ea 192.168.1.102 * *
1795230719 bc:35:1e:4c:55:3d 192.168.1.111 * *
1795222382 d8:c8:0c:10:91:53 192.168.1.144 * *
1795222427 b8:06:0d:68:ef:3e 192.168.1.148 * *
1795222375 3c:0b:59:b7:e3:0e 192.168.1.248 * *
1795230455 4c:a9:19:12:58:28 192.168.1.188 * *
1795222431 b8:06:0d:68:ea:a3 192.168.1.154 * *
1795230214 38:a5:c9:e8:73:89 192.168.1.242 * *
1795227740 ec:4d:3e:37:40:8d 192.168.1.117 yeelink-light-colorb_miap408D *
1795222397 4c:a9:19:d7:76:2f 192.168.1.150 * *
1795222430 c4:82:e1:d8:fc:4f 192.168.1.196 * *
1795212041 c8:22:02:59:c6:0f 192.168.1.191 reg 01:c8:22:02:59:c6:0f
1795222375 b8:06:0d:7d:e9:57 192.168.1.137 * *
1795222058 84:7a:b6:e8:70:3c 192.168.1.237 * 01:84:7a:b6:e8:70:3c
1795218740 c0:f8:53:5d:fc:5d 192.168.1.138 * *
1795230290 b8:06:0d:68:d4:4d 192.168.1.193 wlan0 *
1795232585 be:59:d4:ce:ea:1c 192.168.1.241 realme-10 01:be:59:d4:ce:ea:1c
1795222911 50:8b:b9:0a:30:4d 192.168.1.153 * *
1795222614 a0:99:21:89:e7:62 192.168.1.136 midea_e1_0523 *
0 04:ea:56:4f:37:c9 192.168.1.156 homeassistant 01:04:ea:56:4f:37:c9
1795212202 0e:67:45:7c:6c:a6 192.168.1.224 HONOR-X5c-Plus 01:0e:67:45:7c:6c:a6

### WAN ubus
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 1064,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
	],
	"dns-server": [
		"1.1.1.1",
		"8.8.8.8"
	],
	"dns-search": [
		
	],
	"neighbors": [
		
	],
	"inactive": {
		"ipv4-address": [
			
		],
		"ipv6-address": [
			
		],
		"route": [
			
		],
		"dns-server": [
			"89.22.52.42",
			"89.22.52.43"
		],
		"dns-search": [
			
		],
		"neighbors": [
			
		]
	},
	"data": {
		"dhcpserver": "10.0.19.3",
		"leasetime": 5297
	}
}

### Rule counter
	chain forward_lan {
		ip saddr 192.168.1.191 counter packets 0 bytes 0 jump drop_to_wan comment "!fw4: Block-Cam191-WAN"
		jump accept_to_wan comment "!fw4: Accept lan to wan forwarding"
		jump accept_to_wg comment "!fw4: Accept lan to wg forwarding"

### Cam .191
{
  "host": "192.168.1.191",
  "open_ports": [
    80,
    554,
    34567
  ],
  "http": {
    "status": 200,
    "server": "APPWebs/",
    "title": "index"
  },
  "rtsp": {
    "ok": true,
    "status": "RTSP/1.0 200 OK",
    "server": "Server: Topsvision Server v2.1"
  }
}

### Doctor
Домашняя сеть: 192.168.1.0/24   проверка 2026-11-20 15:55:00
Локальный адрес для 192.168.1.1: 192.168.9.2

  [OK] Шлюз                   192.168.1.1: 22, 80, 443
  [OK] Роутер SSH             SSH работает
  [OK] Home Assistant         API отвечает: API running.
  [!!] Android TV ADB         192.168.1.139 недоступен (ADB выключен?)
  [OK] Мост телефона          локальный мост устройства работает

Проблемы: Android TV ADB. Смотри README и secrets/homelab.env.

### Xray log tail
Fri Nov 20 18:52:19 2026 daemon.info xray[3996]: 2026/11/20 15:52:19.300412 from tcp:127.0.0.1:37854 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 18:53:27 2026 daemon.info xray[3996]: 2026/11/20 15:53:27.334013 from tcp:127.0.0.1:45084 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 18:54:35 2026 daemon.info xray[3996]: 2026/11/20 15:54:35.364048 from tcp:127.0.0.1:48890 accepted tcp:www.facebook.com:443 [socks -> n01]

### Host
 15:55:01 up 0 min,  0 user,  load average: 0.00, 0.00, 0.00
               total        used        free      shared  buff/cache   available
Mem:            10Gi       8.1Gi       140Mi        70Mi       2.3Gi       2.5Gi
Swap:           11Gi       6.9Gi       5.1Gi

## Замер 2 — 2026-11-20 16:05:28 UTC

### Router status
### system
{
	"kernel": "6.12.94",
	"hostname": "Rahmaninova-49",
	"system": "ARMv8 Processor rev 4",
	"model": "Xiaomi AX3600",
	"board_name": "xiaomi,ax3600",
	"rootfs_type": "squashfs",
	"release": {
		"distribution": "OpenWrt",
		"version": "25.12.5",
		"firmware_url": "https://downloads.openwrt.org/",
		"revision": "r33051-f5dae5ece4",
		"target": "qualcommax/ipq807x",
		"description": "OpenWrt 25.12.5 r33051-f5dae5ece4",
		"builddate": "1782737960"
	}
}
### uptime
 19:05:29 up 4 days, 5 min,  load average: 0.05, 0.02, 0.00
### memory
              total        used        free      shared  buff/cache   available
Mem:         414252      254432       63644        6372       96176      102400
Swap:             0           0           0
### disk
Filesystem                Size      Used Available Use% Mounted on
overlayfs:/overlay      174.0M     32.4M    137.0M  19% /
tmpfs                   202.3M      6.2M    196.0M   3% /tmp
### wan
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 1697,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
### wifi
phy0-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:24
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: VHT80
         Center Channel 1: 42 2: unknown
         Tx-Power: 23 dBm  Link Quality: 70/70
         Signal: 0 dBm  Noise: -104 dBm
         Bit Rate: unknown
         Encryption: SAE / WPA-PSK / WPA-PSK-SHA256 (CCMP)
         Type: nl80211  HW Mode(s): 802.11ac/n
         Hardware: 0x168c:0x0050 0x0000:0x0000 [Qualcomm Atheros QCA9887]
         TX power offset: none
         Channel offset: none
         Supports VAPs: yes  PHY name: phy0

phy1-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:23
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: HE80
         Center Channel 1: 42 2: unknown
         Tx-Power: 30 dBm  Link Quality: 49/70
         Signal: -61 dBm  Noise: -109 dBm
### dhcp leases
1795226885 f4:20:15:29:f7:8a 192.168.1.219 SaluteTV 01:f4:20:15:29:f7:8a
1795226159 b4:60:ed:6a:c9:b5 192.168.1.233 yeelink-light-colorb_miapC9B5 *
1795233800 80:3f:5d:30:99:4e 192.168.1.223 * *
1795233843 bc:35:1e:8d:5c:31 192.168.1.171 lwip0 *
1795232904 ce:d8:43:0a:0e:62 192.168.1.175 miwifi-rd10m 01:ce:d8:43:0a:0e:62
1795222373 60:3d:61:59:98:da 192.168.1.140 * ff:61:59:98:da:00:01:00:01:c7:92:bc:8e:60:3d:71:59:98:da
1795230088 d8:c8:0c:cc:d9:1e 192.168.1.213 * *
1795214899 04:f7:78:2a:66:81 192.168.1.126 * 01:04:f7:78:2a:66:81
1795230628 bc:35:1e:4c:48:7e 192.168.1.139 * *
1795233814 bc:35:1e:8d:60:ea 192.168.1.102 * *
1795230719 bc:35:1e:4c:55:3d 192.168.1.111 * *
1795222382 d8:c8:0c:10:91:53 192.168.1.144 * *
1795222427 b8:06:0d:68:ef:3e 192.168.1.148 * *
1795222375 3c:0b:59:b7:e3:0e 192.168.1.248 * *
1795230455 4c:a9:19:12:58:28 192.168.1.188 * *
1795222431 b8:06:0d:68:ea:a3 192.168.1.154 * *
1795230214 38:a5:c9:e8:73:89 192.168.1.242 * *
1795227740 ec:4d:3e:37:40:8d 192.168.1.117 yeelink-light-colorb_miap408D *
1795222397 4c:a9:19:d7:76:2f 192.168.1.150 * *
1795222430 c4:82:e1:d8:fc:4f 192.168.1.196 * *
1795233642 c8:22:02:59:c6:0f 192.168.1.191 reg 01:c8:22:02:59:c6:0f
1795222375 b8:06:0d:7d:e9:57 192.168.1.137 * *
1795222058 84:7a:b6:e8:70:3c 192.168.1.237 * 01:84:7a:b6:e8:70:3c
1795218740 c0:f8:53:5d:fc:5d 192.168.1.138 * *
1795230290 b8:06:0d:68:d4:4d 192.168.1.193 wlan0 *
1795232585 be:59:d4:ce:ea:1c 192.168.1.241 realme-10 01:be:59:d4:ce:ea:1c
1795222911 50:8b:b9:0a:30:4d 192.168.1.153 * *
1795222614 a0:99:21:89:e7:62 192.168.1.136 midea_e1_0523 *
0 04:ea:56:4f:37:c9 192.168.1.156 homeassistant 01:04:ea:56:4f:37:c9
1795233804 0e:67:45:7c:6c:a6 192.168.1.224 HONOR-X5c-Plus 01:0e:67:45:7c:6c:a6

### WAN ubus
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 1698,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
	],
	"dns-server": [
		"1.1.1.1",
		"8.8.8.8"
	],
	"dns-search": [
		
	],
	"neighbors": [
		
	],
	"inactive": {
		"ipv4-address": [
			
		],
		"ipv6-address": [
			
		],
		"route": [
			
		],
		"dns-server": [
			"89.22.52.42",
			"89.22.52.43"
		],
		"dns-search": [
			
		],
		"neighbors": [
			
		]
	},
	"data": {
		"dhcpserver": "10.0.19.3",
		"leasetime": 5297
	}
}

### Rule counter
	chain forward_lan {
		ip saddr 192.168.1.191 counter packets 7 bytes 420 jump drop_to_wan comment "!fw4: Block-Cam191-WAN"
		jump accept_to_wan comment "!fw4: Accept lan to wan forwarding"
		jump accept_to_wg comment "!fw4: Accept lan to wg forwarding"

### Cam .191
{
  "host": "192.168.1.191",
  "open_ports": [
    80,
    554,
    34567
  ],
  "http": {
    "status": 200,
    "server": "APPWebs/",
    "title": "index"
  },
  "rtsp": {
    "ok": true,
    "status": "RTSP/1.0 200 OK",
    "server": "Server: Topsvision Server v2.1"
  }
}

### Doctor
Домашняя сеть: 192.168.1.0/24   проверка 2026-11-20 16:05:36
Локальный адрес для 192.168.1.1: 192.168.9.2

  [OK] Шлюз                   192.168.1.1: 22, 80, 443
  [OK] Роутер SSH             SSH работает
  [OK] Home Assistant         API отвечает: API running.
  [!!] Android TV ADB         192.168.1.139 недоступен (ADB выключен?)
  [OK] Мост телефона          локальный мост устройства работает

Проблемы: Android TV ADB. Смотри README и secrets/homelab.env.

### Xray log tail
Fri Nov 20 19:02:31 2026 daemon.info xray[3996]: 2026/11/20 16:02:31.585891 from tcp:127.0.0.1:39116 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:03:39 2026 daemon.info xray[3996]: 2026/11/20 16:03:39.613396 from tcp:127.0.0.1:33346 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:04:47 2026 daemon.info xray[3996]: 2026/11/20 16:04:47.648917 from tcp:127.0.0.1:38566 accepted tcp:www.facebook.com:443 [socks -> n01]

### Host
 16:05:42 up 0 min,  0 user,  load average: 0.00, 0.00, 0.00
               total        used        free      shared  buff/cache   available
Mem:            10Gi       8.2Gi       130Mi        64Mi       2.4Gi       2.5Gi
Swap:           11Gi       7.6Gi       4.4Gi

## Замер 3 — 2026-11-20 16:17:54 UTC

### Router status
### system
{
	"kernel": "6.12.94",
	"hostname": "Rahmaninova-49",
	"system": "ARMv8 Processor rev 4",
	"model": "Xiaomi AX3600",
	"board_name": "xiaomi,ax3600",
	"rootfs_type": "squashfs",
	"release": {
		"distribution": "OpenWrt",
		"version": "25.12.5",
		"firmware_url": "https://downloads.openwrt.org/",
		"revision": "r33051-f5dae5ece4",
		"target": "qualcommax/ipq807x",
		"description": "OpenWrt 25.12.5 r33051-f5dae5ece4",
		"builddate": "1782737960"
	}
}
### uptime
 19:17:55 up 4 days, 18 min,  load average: 0.00, 0.02, 0.00
### memory
              total        used        free      shared  buff/cache   available
Mem:         414252      277584       40524        6372       96144       79264
Swap:             0           0           0
### disk
Filesystem                Size      Used Available Use% Mounted on
overlayfs:/overlay      174.0M     32.4M    137.0M  19% /
tmpfs                   202.3M      6.2M    196.0M   3% /tmp
### wan
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 2443,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
### wifi
phy0-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:24
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: VHT80
         Center Channel 1: 42 2: unknown
         Tx-Power: 23 dBm  Link Quality: 70/70
         Signal: 0 dBm  Noise: -104 dBm
         Bit Rate: unknown
         Encryption: SAE / WPA-PSK / WPA-PSK-SHA256 (CCMP)
         Type: nl80211  HW Mode(s): 802.11ac/n
         Hardware: 0x168c:0x0050 0x0000:0x0000 [Qualcomm Atheros QCA9887]
         TX power offset: none
         Channel offset: none
         Supports VAPs: yes  PHY name: phy0

phy1-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:23
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: HE80
         Center Channel 1: 42 2: unknown
         Tx-Power: 30 dBm  Link Quality: 54/70
         Signal: -56 dBm  Noise: -109 dBm
### dhcp leases
1795226885 f4:20:15:29:f7:8a 192.168.1.219 SaluteTV 01:f4:20:15:29:f7:8a
1795234660 b4:60:ed:6a:c9:b5 192.168.1.233 yeelink-light-colorb_miapC9B5 *
1795233800 80:3f:5d:30:99:4e 192.168.1.223 * *
1795234618 bc:35:1e:8d:5c:31 192.168.1.171 lwip0 *
1795232904 ce:d8:43:0a:0e:62 192.168.1.175 miwifi-rd10m 01:ce:d8:43:0a:0e:62
1795222373 60:3d:61:59:98:da 192.168.1.140 * ff:61:59:98:da:00:01:00:01:c7:92:bc:8e:60:3d:71:59:98:da
1795230088 d8:c8:0c:cc:d9:1e 192.168.1.213 * *
1795214899 04:f7:78:2a:66:81 192.168.1.126 * 01:04:f7:78:2a:66:81
1795230628 bc:35:1e:4c:48:7e 192.168.1.139 * *
1795234579 bc:35:1e:8d:60:ea 192.168.1.102 * *
1795230719 bc:35:1e:4c:55:3d 192.168.1.111 * *
1795222382 d8:c8:0c:10:91:53 192.168.1.144 * *
1795222427 b8:06:0d:68:ef:3e 192.168.1.148 * *
1795222375 3c:0b:59:b7:e3:0e 192.168.1.248 * *
1795230455 4c:a9:19:12:58:28 192.168.1.188 * *
1795222431 b8:06:0d:68:ea:a3 192.168.1.154 * *
1795230214 38:a5:c9:e8:73:89 192.168.1.242 * *
1795227740 ec:4d:3e:37:40:8d 192.168.1.117 yeelink-light-colorb_miap408D *
1795222397 4c:a9:19:d7:76:2f 192.168.1.150 * *
1795222430 c4:82:e1:d8:fc:4f 192.168.1.196 * *
1795233642 c8:22:02:59:c6:0f 192.168.1.191 reg 01:c8:22:02:59:c6:0f
1795222375 b8:06:0d:7d:e9:57 192.168.1.137 * *
1795222058 84:7a:b6:e8:70:3c 192.168.1.237 * 01:84:7a:b6:e8:70:3c
1795218740 c0:f8:53:5d:fc:5d 192.168.1.138 * *
1795230290 b8:06:0d:68:d4:4d 192.168.1.193 wlan0 *
1795232585 be:59:d4:ce:ea:1c 192.168.1.241 realme-10 01:be:59:d4:ce:ea:1c
1795222911 50:8b:b9:0a:30:4d 192.168.1.153 * *
1795222614 a0:99:21:89:e7:62 192.168.1.136 midea_e1_0523 *
0 04:ea:56:4f:37:c9 192.168.1.156 homeassistant 01:04:ea:56:4f:37:c9
1795233804 0e:67:45:7c:6c:a6 192.168.1.224 HONOR-X5c-Plus 01:0e:67:45:7c:6c:a6

### WAN ubus
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 2444,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
	],
	"dns-server": [
		"1.1.1.1",
		"8.8.8.8"
	],
	"dns-search": [
		
	],
	"neighbors": [
		
	],
	"inactive": {
		"ipv4-address": [
			
		],
		"ipv6-address": [
			
		],
		"route": [
			
		],
		"dns-server": [
			"89.22.52.42",
			"89.22.52.43"
		],
		"dns-search": [
			
		],
		"neighbors": [
			
		]
	},
	"data": {
		"dhcpserver": "10.0.19.3",
		"leasetime": 5297
	}
}

### Rule counter
	chain forward_lan {
		ip saddr 192.168.1.191 counter packets 19 bytes 1140 jump drop_to_wan comment "!fw4: Block-Cam191-WAN"
		jump accept_to_wan comment "!fw4: Accept lan to wan forwarding"
		jump accept_to_wg comment "!fw4: Accept lan to wg forwarding"

### Cam .191
{
  "host": "192.168.1.191",
  "open_ports": [
    80,
    554,
    34567
  ],
  "http": {
    "status": 200,
    "server": "APPWebs/",
    "title": "index"
  },
  "rtsp": {
    "ok": true,
    "status": "RTSP/1.0 200 OK",
    "server": "Server: Topsvision Server v2.1"
  }
}

### Doctor
Домашняя сеть: 192.168.1.0/24   проверка 2026-11-20 16:18:02
Локальный адрес для 192.168.1.1: 192.168.9.2

  [OK] Шлюз                   192.168.1.1: 22, 80, 443
  [OK] Роутер SSH             SSH работает
  [OK] Home Assistant         API отвечает: API running.
  [!!] Android TV ADB         192.168.1.139 недоступен (ADB выключен?)
  [OK] Мост телефона          локальный мост устройства работает

Проблемы: Android TV ADB. Смотри README и secrets/homelab.env.

### Xray log tail
Fri Nov 20 19:14:59 2026 daemon.info xray[3996]: 2026/11/20 16:14:59.935583 from tcp:127.0.0.1:56830 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:16:07 2026 daemon.info xray[3996]: 2026/11/20 16:16:07.966223 from tcp:127.0.0.1:36578 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:17:15 2026 daemon.info xray[3996]: 2026/11/20 16:17:15.990459 from tcp:127.0.0.1:46478 accepted tcp:www.facebook.com:443 [socks -> n01]

### Host
 16:18:03 up 0 min,  0 user,  load average: 0.00, 0.00, 0.00
               total        used        free      shared  buff/cache   available
Mem:            10Gi       8.4Gi        90Mi        55Mi       2.2Gi       2.2Gi
Swap:           11Gi       8.4Gi       3.6Gi

## Замер 4 — 2026-11-20 16:28:55 UTC

### Router status
### system
{
	"kernel": "6.12.94",
	"hostname": "Rahmaninova-49",
	"system": "ARMv8 Processor rev 4",
	"model": "Xiaomi AX3600",
	"board_name": "xiaomi,ax3600",
	"rootfs_type": "squashfs",
	"release": {
		"distribution": "OpenWrt",
		"version": "25.12.5",
		"firmware_url": "https://downloads.openwrt.org/",
		"revision": "r33051-f5dae5ece4",
		"target": "qualcommax/ipq807x",
		"description": "OpenWrt 25.12.5 r33051-f5dae5ece4",
		"builddate": "1782737960"
	}
}
### uptime
 19:28:55 up 4 days, 29 min,  load average: 0.00, 0.02, 0.00
### memory
              total        used        free      shared  buff/cache   available
Mem:         414252      275484       42544        6372       96224       81324
Swap:             0           0           0
### disk
Filesystem                Size      Used Available Use% Mounted on
overlayfs:/overlay      174.0M     32.4M    137.0M  19% /
tmpfs                   202.3M      6.2M    196.0M   3% /tmp
### wan
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 474,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
### wifi
phy0-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:24
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: VHT80
         Center Channel 1: 42 2: unknown
         Tx-Power: 23 dBm  Link Quality: 70/70
         Signal: 0 dBm  Noise: -103 dBm
         Bit Rate: unknown
         Encryption: SAE / WPA-PSK / WPA-PSK-SHA256 (CCMP)
         Type: nl80211  HW Mode(s): 802.11ac/n
         Hardware: 0x168c:0x0050 0x0000:0x0000 [Qualcomm Atheros QCA9887]
         TX power offset: none
         Channel offset: none
         Supports VAPs: yes  PHY name: phy0

phy1-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:23
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: HE80
         Center Channel 1: 42 2: unknown
         Tx-Power: 30 dBm  Link Quality: 52/70
         Signal: -58 dBm  Noise: -109 dBm
### dhcp leases
1795226885 f4:20:15:29:f7:8a 192.168.1.219 SaluteTV 01:f4:20:15:29:f7:8a
1795234660 b4:60:ed:6a:c9:b5 192.168.1.233 yeelink-light-colorb_miapC9B5 *
1795233800 80:3f:5d:30:99:4e 192.168.1.223 * *
1795235279 bc:35:1e:8d:5c:31 192.168.1.171 lwip0 *
1795232904 ce:d8:43:0a:0e:62 192.168.1.175 miwifi-rd10m 01:ce:d8:43:0a:0e:62
1795222373 60:3d:61:59:98:da 192.168.1.140 * ff:61:59:98:da:00:01:00:01:c7:92:bc:8e:60:3d:71:59:98:da
1795230088 d8:c8:0c:cc:d9:1e 192.168.1.213 * *
1795235097 04:f7:78:2a:66:81 192.168.1.126 * 01:04:f7:78:2a:66:81
1795230628 bc:35:1e:4c:48:7e 192.168.1.139 * *
1795235217 bc:35:1e:8d:60:ea 192.168.1.102 * *
1795230719 bc:35:1e:4c:55:3d 192.168.1.111 * *
1795222382 d8:c8:0c:10:91:53 192.168.1.144 * *
1795222427 b8:06:0d:68:ef:3e 192.168.1.148 * *
1795222375 3c:0b:59:b7:e3:0e 192.168.1.248 * *
1795230455 4c:a9:19:12:58:28 192.168.1.188 * *
1795222431 b8:06:0d:68:ea:a3 192.168.1.154 * *
1795230214 38:a5:c9:e8:73:89 192.168.1.242 * *
1795227740 ec:4d:3e:37:40:8d 192.168.1.117 yeelink-light-colorb_miap408D *
1795222397 4c:a9:19:d7:76:2f 192.168.1.150 * *
1795222430 c4:82:e1:d8:fc:4f 192.168.1.196 * *
1795233642 c8:22:02:59:c6:0f 192.168.1.191 reg 01:c8:22:02:59:c6:0f
1795222375 b8:06:0d:7d:e9:57 192.168.1.137 * *
1795222058 84:7a:b6:e8:70:3c 192.168.1.237 * 01:84:7a:b6:e8:70:3c
1795218740 c0:f8:53:5d:fc:5d 192.168.1.138 * *
1795230290 b8:06:0d:68:d4:4d 192.168.1.193 wlan0 *
1795232585 be:59:d4:ce:ea:1c 192.168.1.241 realme-10 01:be:59:d4:ce:ea:1c
1795222911 50:8b:b9:0a:30:4d 192.168.1.153 * *
1795222614 a0:99:21:89:e7:62 192.168.1.136 midea_e1_0523 *
0 04:ea:56:4f:37:c9 192.168.1.156 homeassistant 01:04:ea:56:4f:37:c9
1795233804 0e:67:45:7c:6c:a6 192.168.1.224 HONOR-X5c-Plus 01:0e:67:45:7c:6c:a6

### WAN ubus
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 475,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
	],
	"dns-server": [
		"1.1.1.1",
		"8.8.8.8"
	],
	"dns-search": [
		
	],
	"neighbors": [
		
	],
	"inactive": {
		"ipv4-address": [
			
		],
		"ipv6-address": [
			
		],
		"route": [
			
		],
		"dns-server": [
			"89.22.52.42",
			"89.22.52.43"
		],
		"dns-search": [
			
		],
		"neighbors": [
			
		]
	},
	"data": {
		"dhcpserver": "10.0.19.2",
		"leasetime": 5828
	}
}

### Rule counter
	chain forward_lan {
		ip saddr 192.168.1.191 counter packets 24 bytes 1440 jump drop_to_wan comment "!fw4: Block-Cam191-WAN"
		jump accept_to_wan comment "!fw4: Accept lan to wan forwarding"
		jump accept_to_wg comment "!fw4: Accept lan to wg forwarding"

### Cam .191
{
  "host": "192.168.1.191",
  "open_ports": [],
  "http": null,
  "rtsp": null
}

### Doctor
Домашняя сеть: 192.168.1.0/24   проверка 2026-11-20 16:29:07
Локальный адрес для 192.168.1.1: 192.168.0.15

  [OK] Шлюз                   192.168.1.1: 80, 443
  [OK] Роутер SSH             SSH работает
  [!!] Home Assistant         192.168.1.156:8123 недоступен
  [!!] Android TV ADB         192.168.1.139 недоступен (ADB выключен?)
  [OK] Мост телефона          локальный мост устройства работает

Проблемы: Home Assistant, Android TV ADB. Смотри README и secrets/homelab.env.

### Xray log tail
Fri Nov 20 19:26:08 2026 daemon.info xray[3996]: 2026/11/20 16:26:08.331283 from tcp:127.0.0.1:56964 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:27:16 2026 daemon.info xray[3996]: 2026/11/20 16:27:16.361188 from tcp:127.0.0.1:39970 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:28:24 2026 daemon.info xray[3996]: 2026/11/20 16:28:24.395634 from tcp:127.0.0.1:45646 accepted tcp:www.facebook.com:443 [socks -> n01]

### Host
 16:29:08 up 0 min,  0 user,  load average: 0.00, 0.00, 0.00
               total        used        free      shared  buff/cache   available
Mem:            10Gi       8.6Gi       248Mi        68Mi       1.7Gi       2.0Gi
Swap:           11Gi       8.4Gi       3.6Gi

## Замер 5 — 2026-11-20 16:39:08 UTC

### Router status
### system
{
	"kernel": "6.12.94",
	"hostname": "Rahmaninova-49",
	"system": "ARMv8 Processor rev 4",
	"model": "Xiaomi AX3600",
	"board_name": "xiaomi,ax3600",
	"rootfs_type": "squashfs",
	"release": {
		"distribution": "OpenWrt",
		"version": "25.12.5",
		"firmware_url": "https://downloads.openwrt.org/",
		"revision": "r33051-f5dae5ece4",
		"target": "qualcommax/ipq807x",
		"description": "OpenWrt 25.12.5 r33051-f5dae5ece4",
		"builddate": "1782737960"
	}
}
### uptime
 19:39:08 up 4 days, 39 min,  load average: 0.07, 0.03, 0.00
### memory
              total        used        free      shared  buff/cache   available
Mem:         414252      276836       41224        6372       96192       79988
Swap:             0           0           0
### disk
Filesystem                Size      Used Available Use% Mounted on
overlayfs:/overlay      174.0M     32.4M    137.0M  19% /
tmpfs                   202.3M      6.2M    196.0M   3% /tmp
### wan
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 1087,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
### wifi
phy0-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:24
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: VHT80
         Center Channel 1: 42 2: unknown
         Tx-Power: 23 dBm  Link Quality: 70/70
         Signal: 0 dBm  Noise: -104 dBm
         Bit Rate: unknown
         Encryption: SAE / WPA-PSK / WPA-PSK-SHA256 (CCMP)
         Type: nl80211  HW Mode(s): 802.11ac/n
         Hardware: 0x168c:0x0050 0x0000:0x0000 [Qualcomm Atheros QCA9887]
         TX power offset: none
         Channel offset: none
         Supports VAPs: yes  PHY name: phy0

phy1-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:23
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: HE80
         Center Channel 1: 42 2: unknown
         Tx-Power: 30 dBm  Link Quality: 51/70
         Signal: -59 dBm  Noise: -109 dBm
### dhcp leases
1795226885 f4:20:15:29:f7:8a 192.168.1.219 SaluteTV 01:f4:20:15:29:f7:8a
1795234660 b4:60:ed:6a:c9:b5 192.168.1.233 yeelink-light-colorb_miapC9B5 *
1795233800 80:3f:5d:30:99:4e 192.168.1.223 * *
1795235917 bc:35:1e:8d:5c:31 192.168.1.171 lwip0 *
1795232904 ce:d8:43:0a:0e:62 192.168.1.175 miwifi-rd10m 01:ce:d8:43:0a:0e:62
1795222373 60:3d:61:59:98:da 192.168.1.140 * ff:61:59:98:da:00:01:00:01:c7:92:bc:8e:60:3d:71:59:98:da
1795230088 d8:c8:0c:cc:d9:1e 192.168.1.213 * *
1795235097 04:f7:78:2a:66:81 192.168.1.126 * 01:04:f7:78:2a:66:81
1795230628 bc:35:1e:4c:48:7e 192.168.1.139 * *
1795235855 bc:35:1e:8d:60:ea 192.168.1.102 * *
1795230719 bc:35:1e:4c:55:3d 192.168.1.111 * *
1795222382 d8:c8:0c:10:91:53 192.168.1.144 * *
1795222427 b8:06:0d:68:ef:3e 192.168.1.148 * *
1795222375 3c:0b:59:b7:e3:0e 192.168.1.248 * *
1795230455 4c:a9:19:12:58:28 192.168.1.188 * *
1795222431 b8:06:0d:68:ea:a3 192.168.1.154 * *
1795230214 38:a5:c9:e8:73:89 192.168.1.242 * *
1795227740 ec:4d:3e:37:40:8d 192.168.1.117 yeelink-light-colorb_miap408D *
1795222397 4c:a9:19:d7:76:2f 192.168.1.150 * *
1795222430 c4:82:e1:d8:fc:4f 192.168.1.196 * *
1795233642 c8:22:02:59:c6:0f 192.168.1.191 reg 01:c8:22:02:59:c6:0f
1795222375 b8:06:0d:7d:e9:57 192.168.1.137 * *
1795222058 84:7a:b6:e8:70:3c 192.168.1.237 * 01:84:7a:b6:e8:70:3c
1795218740 c0:f8:53:5d:fc:5d 192.168.1.138 * *
1795230290 b8:06:0d:68:d4:4d 192.168.1.193 wlan0 *
1795232585 be:59:d4:ce:ea:1c 192.168.1.241 realme-10 01:be:59:d4:ce:ea:1c
1795222911 50:8b:b9:0a:30:4d 192.168.1.153 * *
1795222614 a0:99:21:89:e7:62 192.168.1.136 midea_e1_0523 *
0 04:ea:56:4f:37:c9 192.168.1.156 homeassistant 01:04:ea:56:4f:37:c9
1795233804 0e:67:45:7c:6c:a6 192.168.1.224 HONOR-X5c-Plus 01:0e:67:45:7c:6c:a6

### WAN ubus
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 1088,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
	],
	"dns-server": [
		"1.1.1.1",
		"8.8.8.8"
	],
	"dns-search": [
		
	],
	"neighbors": [
		
	],
	"inactive": {
		"ipv4-address": [
			
		],
		"ipv6-address": [
			
		],
		"route": [
			
		],
		"dns-server": [
			"89.22.52.42",
			"89.22.52.43"
		],
		"dns-search": [
			
		],
		"neighbors": [
			
		]
	},
	"data": {
		"dhcpserver": "10.0.19.2",
		"leasetime": 5828
	}
}

### Rule counter
	chain forward_lan {
		ip saddr 192.168.1.191 counter packets 55 bytes 3300 jump drop_to_wan comment "!fw4: Block-Cam191-WAN"
		jump accept_to_wan comment "!fw4: Accept lan to wan forwarding"
		jump accept_to_wg comment "!fw4: Accept lan to wg forwarding"

### Cam .191
{
  "host": "192.168.1.191",
  "open_ports": [
    8000
  ],
  "http": null,
  "rtsp": null
}

### Doctor
Домашняя сеть: 192.168.1.0/24   проверка 2026-11-20 16:39:20
Локальный адрес для 192.168.1.1: 192.168.0.15

  [OK] Шлюз                   192.168.1.1: 80, 443
  [OK] Роутер SSH             SSH работает
  [!!] Home Assistant         192.168.1.156:8123 недоступен
  [!!] Android TV ADB         192.168.1.139 недоступен (ADB выключен?)
  [OK] Мост телефона          локальный мост устройства работает

Проблемы: Home Assistant, Android TV ADB. Смотри README и secrets/homelab.env.

### Xray log tail
Fri Nov 20 19:36:20 2026 daemon.info xray[3996]: 2026/11/20 16:36:20.610125 from tcp:127.0.0.1:38916 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:37:28 2026 daemon.info xray[3996]: 2026/11/20 16:37:28.641605 from tcp:127.0.0.1:33732 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:38:36 2026 daemon.info xray[3996]: 2026/11/20 16:38:36.673976 from tcp:127.0.0.1:46346 accepted tcp:www.facebook.com:443 [socks -> n01]

### Host
 16:39:20 up 0 min,  0 user,  load average: 0.00, 0.00, 0.00
               total        used        free      shared  buff/cache   available
Mem:            10Gi       8.9Gi       129Mi        68Mi       1.6Gi       1.7Gi
Swap:           11Gi       8.0Gi       4.0Gi

## Замер 6 — 2026-11-20 16:52:31 UTC

### Router status
### system
{
	"kernel": "6.12.94",
	"hostname": "Rahmaninova-49",
	"system": "ARMv8 Processor rev 4",
	"model": "Xiaomi AX3600",
	"board_name": "xiaomi,ax3600",
	"rootfs_type": "squashfs",
	"release": {
		"distribution": "OpenWrt",
		"version": "25.12.5",
		"firmware_url": "https://downloads.openwrt.org/",
		"revision": "r33051-f5dae5ece4",
		"target": "qualcommax/ipq807x",
		"description": "OpenWrt 25.12.5 r33051-f5dae5ece4",
		"builddate": "1782737960"
	}
}
### uptime
 19:52:31 up 4 days, 52 min,  load average: 0.02, 0.01, 0.00
### memory
              total        used        free      shared  buff/cache   available
Mem:         414252      279852       38224        6372       96176       76980
Swap:             0           0           0
### disk
Filesystem                Size      Used Available Use% Mounted on
overlayfs:/overlay      174.0M     32.4M    137.0M  19% /
tmpfs                   202.3M      6.2M    196.0M   3% /tmp
### wan
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 1890,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
### wifi
phy0-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:24
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: VHT80
         Center Channel 1: 42 2: unknown
         Tx-Power: 23 dBm  Link Quality: 70/70
         Signal: 0 dBm  Noise: -104 dBm
         Bit Rate: unknown
         Encryption: SAE / WPA-PSK / WPA-PSK-SHA256 (CCMP)
         Type: nl80211  HW Mode(s): 802.11ac/n
         Hardware: 0x168c:0x0050 0x0000:0x0000 [Qualcomm Atheros QCA9887]
         TX power offset: none
         Channel offset: none
         Supports VAPs: yes  PHY name: phy0

phy1-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:23
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: HE80
         Center Channel 1: 42 2: unknown
         Tx-Power: 30 dBm  Link Quality: 52/70
         Signal: -58 dBm  Noise: -109 dBm
### dhcp leases
1795233804 0e:67:45:7c:6c:a6 192.168.1.224 HONOR-X5c-Plus 01:0e:67:45:7c:6c:a6
0 04:ea:56:4f:37:c9 192.168.1.156 homeassistant 01:04:ea:56:4f:37:c9
1795222614 a0:99:21:89:e7:62 192.168.1.136 midea_e1_0523 *
1795222911 50:8b:b9:0a:30:4d 192.168.1.153 * *
1795232585 be:59:d4:ce:ea:1c 192.168.1.241 realme-10 01:be:59:d4:ce:ea:1c
1795230290 b8:06:0d:68:d4:4d 192.168.1.193 wlan0 *
1795218740 c0:f8:53:5d:fc:5d 192.168.1.138 * *
1795222058 84:7a:b6:e8:70:3c 192.168.1.237 * 01:84:7a:b6:e8:70:3c
1795222375 b8:06:0d:7d:e9:57 192.168.1.137 * *
1795233642 c8:22:02:59:c6:0f 192.168.1.191 reg 01:c8:22:02:59:c6:0f
1795222430 c4:82:e1:d8:fc:4f 192.168.1.196 * *
1795222397 4c:a9:19:d7:76:2f 192.168.1.150 * *
1795227740 ec:4d:3e:37:40:8d 192.168.1.117 yeelink-light-colorb_miap408D *
1795230214 38:a5:c9:e8:73:89 192.168.1.242 * *
1795222431 b8:06:0d:68:ea:a3 192.168.1.154 * *
1795230455 4c:a9:19:12:58:28 192.168.1.188 * *
1795222375 3c:0b:59:b7:e3:0e 192.168.1.248 * *
1795222427 b8:06:0d:68:ef:3e 192.168.1.148 * *
1795222382 d8:c8:0c:10:91:53 192.168.1.144 * *
1795230719 bc:35:1e:4c:55:3d 192.168.1.111 * *
1795236747 bc:35:1e:8d:60:ea 192.168.1.102 lwip0 *
1795230628 bc:35:1e:4c:48:7e 192.168.1.139 xiaomi-tv-139 *
1795235097 04:f7:78:2a:66:81 192.168.1.126 * 01:04:f7:78:2a:66:81
1795230088 d8:c8:0c:cc:d9:1e 192.168.1.213 * *
1795222373 60:3d:61:59:98:da 192.168.1.140 * ff:61:59:98:da:00:01:00:01:c7:92:bc:8e:60:3d:71:59:98:da
1795232904 ce:d8:43:0a:0e:62 192.168.1.175 miwifi-175 01:ce:d8:43:0a:0e:62
1795236682 bc:35:1e:8d:5c:31 192.168.1.171 * *
1795233800 80:3f:5d:30:99:4e 192.168.1.223 * *
1795234660 b4:60:ed:6a:c9:b5 192.168.1.233 yeelink-light-colorb_miapC9B5 *
1795226885 f4:20:15:29:f7:8a 192.168.1.219 SaluteTV 01:f4:20:15:29:f7:8a

### WAN ubus
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 1890,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
	],
	"dns-server": [
		"1.1.1.1",
		"8.8.8.8"
	],
	"dns-search": [
		
	],
	"neighbors": [
		
	],
	"inactive": {
		"ipv4-address": [
			
		],
		"ipv6-address": [
			
		],
		"route": [
			
		],
		"dns-server": [
			"89.22.52.42",
			"89.22.52.43"
		],
		"dns-search": [
			
		],
		"neighbors": [
			
		]
	},
	"data": {
		"dhcpserver": "10.0.19.2",
		"leasetime": 5828
	}
}

### Rule counter
	chain forward_lan {
		ip saddr 192.168.1.191 counter packets 94 bytes 5640 jump drop_to_wan comment "!fw4: Block-Cam191-WAN"
		jump accept_to_wan comment "!fw4: Accept lan to wan forwarding"
		jump accept_to_wg comment "!fw4: Accept lan to wg forwarding"

### Cam .191
{
  "host": "192.168.1.191",
  "open_ports": [],
  "http": null,
  "rtsp": null
}

### Doctor
Домашняя сеть: 192.168.1.0/24   проверка 2026-11-20 16:52:43
Локальный адрес для 192.168.1.1: 192.168.0.15

  [OK] Шлюз                   192.168.1.1: 80, 443
  [OK] Роутер SSH             SSH работает
  [!!] Home Assistant         192.168.1.156:8123 недоступен
  [!!] Android TV ADB         192.168.1.139 недоступен (ADB выключен?)
  [OK] Мост телефона          локальный мост устройства работает

Проблемы: Home Assistant, Android TV ADB. Смотри README и secrets/homelab.env.

### Xray log tail
Fri Nov 20 19:49:56 2026 daemon.info xray[3996]: 2026/11/20 16:49:56.986997 from tcp:127.0.0.1:42514 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:51:05 2026 daemon.info xray[3996]: 2026/11/20 16:51:05.017755 from tcp:127.0.0.1:57932 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 19:52:13 2026 daemon.info xray[3996]: 2026/11/20 16:52:13.049249 from tcp:127.0.0.1:53034 accepted tcp:www.facebook.com:443 [socks -> n01]

### Host
 16:52:43 up 0 min,  0 user,  load average: 0.00, 0.00, 0.00
               total        used        free      shared  buff/cache   available
Mem:            10Gi       8.4Gi       151Mi        61Mi       2.1Gi       2.2Gi
Swap:           11Gi       7.9Gi       4.1Gi

## Замер 7 — 2026-11-20 17:02:47 UTC

### Router status
### system
{
	"kernel": "6.12.94",
	"hostname": "Rahmaninova-49",
	"system": "ARMv8 Processor rev 4",
	"model": "Xiaomi AX3600",
	"board_name": "xiaomi,ax3600",
	"rootfs_type": "squashfs",
	"release": {
		"distribution": "OpenWrt",
		"version": "25.12.5",
		"firmware_url": "https://downloads.openwrt.org/",
		"revision": "r33051-f5dae5ece4",
		"target": "qualcommax/ipq807x",
		"description": "OpenWrt 25.12.5 r33051-f5dae5ece4",
		"builddate": "1782737960"
	}
}
### uptime
 20:02:48 up 4 days,  1:03,  load average: 0.06, 0.06, 0.00
### memory
              total        used        free      shared  buff/cache   available
Mem:         414252      274812       43292        6376       96148       82032
Swap:             0           0           0
### disk
Filesystem                Size      Used Available Use% Mounted on
overlayfs:/overlay      174.0M     32.4M    137.0M  19% /
tmpfs                   202.3M      6.2M    196.0M   3% /tmp
### wan
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 2507,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
### wifi
phy0-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:24
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: VHT80
         Center Channel 1: 42 2: unknown
         Tx-Power: 23 dBm  Link Quality: 70/70
         Signal: 0 dBm  Noise: -104 dBm
         Bit Rate: unknown
         Encryption: SAE / WPA-PSK / WPA-PSK-SHA256 (CCMP)
         Type: nl80211  HW Mode(s): 802.11ac/n
         Hardware: 0x168c:0x0050 0x0000:0x0000 [Qualcomm Atheros QCA9887]
         TX power offset: none
         Channel offset: none
         Supports VAPs: yes  PHY name: phy0

phy1-ap0 ESSID: "RT-WIFI-47"
         Access Point: 28:d1:27:4d:78:23
         Mode: Master  Channel: 36 (5.180 GHz)  HT Mode: HE80
         Center Channel 1: 42 2: unknown
         Tx-Power: 30 dBm  Link Quality: 52/70
         Signal: -58 dBm  Noise: -109 dBm
### dhcp leases
1795233804 0e:67:45:7c:6c:a6 192.168.1.224 HONOR-X5c-Plus 01:0e:67:45:7c:6c:a6
0 04:ea:56:4f:37:c9 192.168.1.156 homeassistant 01:04:ea:56:4f:37:c9
1795222614 a0:99:21:89:e7:62 192.168.1.136 midea_e1_0523 *
1795222911 50:8b:b9:0a:30:4d 192.168.1.153 * *
1795232585 be:59:d4:ce:ea:1c 192.168.1.241 realme-10 01:be:59:d4:ce:ea:1c
1795230290 b8:06:0d:68:d4:4d 192.168.1.193 wlan0 *
1795218740 c0:f8:53:5d:fc:5d 192.168.1.138 * *
1795222058 84:7a:b6:e8:70:3c 192.168.1.237 * 01:84:7a:b6:e8:70:3c
1795222375 b8:06:0d:7d:e9:57 192.168.1.137 * *
1795233642 c8:22:02:59:c6:0f 192.168.1.191 reg 01:c8:22:02:59:c6:0f
1795222430 c4:82:e1:d8:fc:4f 192.168.1.196 * *
1795222397 4c:a9:19:d7:76:2f 192.168.1.150 * *
1795227740 ec:4d:3e:37:40:8d 192.168.1.117 yeelink-light-colorb_miap408D *
1795230214 38:a5:c9:e8:73:89 192.168.1.242 * *
1795222431 b8:06:0d:68:ea:a3 192.168.1.154 * *
1795230455 4c:a9:19:12:58:28 192.168.1.188 * *
1795222375 3c:0b:59:b7:e3:0e 192.168.1.248 * *
1795222427 b8:06:0d:68:ef:3e 192.168.1.148 * *
1795222382 d8:c8:0c:10:91:53 192.168.1.144 * *
1795230719 bc:35:1e:4c:55:3d 192.168.1.111 * *
1795237257 bc:35:1e:8d:60:ea 192.168.1.102 * *
1795230628 bc:35:1e:4c:48:7e 192.168.1.139 xiaomi-tv-139 *
1795235097 04:f7:78:2a:66:81 192.168.1.126 * 01:04:f7:78:2a:66:81
1795230088 d8:c8:0c:cc:d9:1e 192.168.1.213 * *
1795222373 60:3d:61:59:98:da 192.168.1.140 * ff:61:59:98:da:00:01:00:01:c7:92:bc:8e:60:3d:71:59:98:da
1795232904 ce:d8:43:0a:0e:62 192.168.1.175 miwifi-175 01:ce:d8:43:0a:0e:62
1795237319 bc:35:1e:8d:5c:31 192.168.1.171 lwip0 *
1795233800 80:3f:5d:30:99:4e 192.168.1.223 * *
1795234660 b4:60:ed:6a:c9:b5 192.168.1.233 yeelink-light-colorb_miapC9B5 *
1795226885 f4:20:15:29:f7:8a 192.168.1.219 SaluteTV 01:f4:20:15:29:f7:8a

### WAN ubus
{
	"up": true,
	"pending": false,
	"available": true,
	"autostart": true,
	"dynamic": false,
	"uptime": 2507,
	"l3_device": "wan",
	"proto": "dhcp",
	"device": "wan",
	"updated": [
		"addresses",
		"routes",
		"data"
	],
	"metric": 0,
	"dns_metric": 0,
	"delegation": true,
	"ipv4-address": [
		{
			"address": "172.25.213.7",
			"mask": 24
		}
	],
	"ipv6-address": [
		
	],
	"ipv6-prefix": [
		
	],
	"ipv6-prefix-assignment": [
		
	],
	"route": [
		{
			"target": "0.0.0.0",
			"mask": 0,
			"nexthop": "172.25.213.1",
			"source": "172.25.213.7/32"
		}
	],
	"dns-server": [
		"1.1.1.1",
		"8.8.8.8"
	],
	"dns-search": [
		
	],
	"neighbors": [
		
	],
	"inactive": {
		"ipv4-address": [
			
		],
		"ipv6-address": [
			
		],
		"route": [
			
		],
		"dns-server": [
			"89.22.52.42",
			"89.22.52.43"
		],
		"dns-search": [
			
		],
		"neighbors": [
			
		]
	},
	"data": {
		"dhcpserver": "10.0.19.2",
		"leasetime": 5828
	}
}

### Rule counter
	chain forward_lan {
		ip saddr 192.168.1.191 counter packets 125 bytes 7500 jump drop_to_wan comment "!fw4: Block-Cam191-WAN"
		jump accept_to_wan comment "!fw4: Accept lan to wan forwarding"
		jump accept_to_wg comment "!fw4: Accept lan to wg forwarding"

### Cam .191
{
  "host": "192.168.1.191",
  "open_ports": [],
  "http": null,
  "rtsp": null
}

### Doctor
Домашняя сеть: 192.168.1.0/24   проверка 2026-11-20 17:03:00
Локальный адрес для 192.168.1.1: 192.168.0.15

  [OK] Шлюз                   192.168.1.1: 80, 443
  [OK] Роутер SSH             SSH работает
  [!!] Home Assistant         192.168.1.156:8123 недоступен
  [!!] Android TV ADB         192.168.1.139 недоступен (ADB выключен?)
  [OK] Мост телефона          локальный мост устройства работает

Проблемы: Home Assistant, Android TV ADB. Смотри README и secrets/homelab.env.

### Xray log tail
Fri Nov 20 20:00:09 2026 daemon.info xray[3996]: 2026/11/20 17:00:09.267746 from tcp:127.0.0.1:45802 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 20:01:17 2026 daemon.info xray[3996]: 2026/11/20 17:01:17.298873 from tcp:127.0.0.1:41934 accepted tcp:www.facebook.com:443 [socks -> n01]
Fri Nov 20 20:02:25 2026 daemon.info xray[3996]: 2026/11/20 17:02:25.330346 from tcp:127.0.0.1:33874 accepted tcp:www.facebook.com:443 [socks -> n01]

### Host
 17:03:01 up 0 min,  0 user,  load average: 0.00, 0.00, 0.00
               total        used        free      shared  buff/cache   available
Mem:            10Gi       8.4Gi       207Mi        67Mi       1.8Gi       2.2Gi
Swap:           11Gi       7.9Gi       4.1Gi

ДONE 2026-11-20 17:03:01 UTC
