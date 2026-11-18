# Swachh Nayan — Luckfox Pico Upload & Launch Guide

## Option 1: SCP Direct Upload (Recommended over USB RNDIS / Ethernet)

Open Windows PowerShell and run:

```powershell
scp -r c:\Users\gupta\Downloads\Swachh_Nayan\* root@172.32.0.93:/root/
```

*Default Password for Luckfox Pico*: Press `Enter` (or `root` / `luckfox`).

---

## Option 2: Launch Standalone Engine on Luckfox Pico

Once uploaded, log into your Luckfox Pico via SSH:

```powershell
ssh root@172.32.0.93
```

And run:

```bash
cd /root
chmod +x deploy_standalone_pico.sh
./deploy_standalone_pico.sh
```

---

## Option 3: Access Live Board Feed & Dashboard

Open any web browser on your PC/Phone connected to the network:
👉 **`http://172.32.0.93:8080`**

For the default USB RNDIS connection, configure the PC's Remote NDIS adapter
as `172.32.0.100` with subnet mask `255.255.255.0`. The board default is
`172.32.0.93`.

* Live Video Feed: Onboard **MIPI CSI Camera Module** (`/dev/video11`).
* Hardware Servo: Controls MG996R overhead mesh scoop via Linux PWM0 (`/sys/class/pwm/pwmchip0`).
