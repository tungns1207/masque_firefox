import subprocess
import time
import os
import signal
import datetime
import random
import string
import sys

# ==========================================
# 1. SYSTEM CONFIGURATION
# ==========================================
INTERFACE = "eth0"
OUTPUT_DIR = "/home/headless/Documents"
CURL_PATH = "/usr/local/bin/curl"
REST_TIME = 15   # Rest time between cycles (seconds)

# Traffic Configuration
UPLOAD_SIZE_MB = 5 
DOWNLOAD_PHOTOS = 8      # Number of photos to download per cycle
DOWNLOAD_WEBSITES = 40    # Number of websites to download per cycle (8-10)
TIMEOUT_SEC = 25         # Safe timeout

# ==========================================
# 2. TARGET CONFIGURATION (FIXED - HTTP/3 ONLY)
# ==========================================

# Upload: Cloudflare QUIC test endpoint - SUPPORTS HTTP/3 UPLOAD
VALID_UPLOAD_TARGETS = [
    "https://cloudflare-quic.com/b/post",
]

# Download: Native QUIC/HTTP/3 supported servers
VALID_DOWNLOAD_TARGETS = [
    "https://cloudflare-quic.com",
    "https://www.google.com",
    "https://www.facebook.com",
    "https://www.youtube.com",
    "https://www.instagram.com",
    "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css",
]

# ==========================================
# 3. SYSTEM FUNCTIONS (PCAP & UTILS)
# ==========================================

def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def start_tcpdump(filename):
    """Start recording PCAP file, filtering out VNC ports"""
    pcap_path = os.path.join(OUTPUT_DIR, filename)
    print(f"\n[SYSTEM] 1. Starting TCPDUMP -> {pcap_path}")
    
    # Filter out ports 5901/6901 to avoid recording VNC image traffic
    cmd = [
        "sudo", "tcpdump", "-i", INTERFACE,
        "-w", pcap_path,
        "not", "port", "6901", "and", "not", "port", "5901"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc

def stop_tcpdump(proc):
    """Stop tcpdump safely"""
    print("[SYSTEM] 4. Stopping TCPDUMP...")
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        subprocess.run(["sudo", "kill", "-9", str(proc.pid)], stderr=subprocess.DEVNULL)
        proc.wait()
    except Exception as e:
        print(f"  -> Error stopping tcpdump: {e}")

def get_random_string(length=10):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def generate_dummy_file(filename, size_mb):
    """Create dummy file with random content (hard to compress)"""
    actual_size = size_mb + random.uniform(-0.5, 0.5)
    if actual_size < 0.1: actual_size = 0.1
    with open(filename, 'wb') as f:
        f.write(os.urandom(int(actual_size * 1024 * 1024)))

# ==========================================
# 4. TRAFFIC FUNCTIONS (CURL HTTP/3 ONLY)
# ==========================================

def get_random_photo_url():
    """Generate random photo URL from Picsum"""
    width = random.randint(800, 1920)
    height = random.randint(600, 1080)
    seed = get_random_string(5)
    return f"https://picsum.photos/seed/{seed}/{width}/{height}"

def get_random_website_url():
    """Generate random website URL"""
    domain = random.choice(VALID_DOWNLOAD_TARGETS)
    return f"{domain}/?v={get_random_string(8)}"

def run_download_action(target, download_type="file"):
    """Download via HTTP/3 ONLY"""
    type_label = "PHOTO" if download_type == "photo" else "WEB"
    print(f"  [{type_label}] {target}")
    
    cmd = [
        CURL_PATH, 
        "--http3-only",     # CRITICAL: Use HTTP/3 only, fail if not possible
        "--ipv4",           # IPv4 only to avoid IPv6 delays
        "-k",               # Ignore SSL errors
        "-L",               # Follow redirects
        "-s",               # Silent mode
        "-o", "/dev/null",  # Discard output
        "--max-time", str(TIMEOUT_SEC), 
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        target
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_SEC+5)
        if result.returncode != 0:
            print(f"    ⚠ Failed (code {result.returncode})")
        else:
            print(f"    ✓ Success")
    except subprocess.TimeoutExpired:
        print(f"    ✗ Timeout after {TIMEOUT_SEC}s")
    except Exception as e:
        print(f"    ✗ Error: {e}")

def run_upload_action():
    """Upload via HTTP/3 ONLY"""
    target = random.choice(VALID_UPLOAD_TARGETS)
    filename = f"up_{get_random_string(5)}.bin"
    generate_dummy_file(filename, UPLOAD_SIZE_MB)
    
    print(f"  [UP]   {target} ({UPLOAD_SIZE_MB}MB via --http3-only)")
    
    cmd = [
        CURL_PATH, 
        "--http3-only",     # CRITICAL: MANDATORY HTTP/3
        "--ipv4",           # IPv4 only
        "-k",               # Ignore SSL errors
        "-s",               # Silent mode
        "-o", "/dev/null",  # Discard response
        "--max-time", str(TIMEOUT_SEC * 2),
        "-F", f"file=@{filename}",  # Form upload
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        target
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_SEC*2+10)
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='ignore')
            print(f"  ✗ Upload failed (code {result.returncode})")
            # Debug info
            if 'QUIC' in stderr or 'HTTP/3' in stderr:
                print(f"  -> Attempted H3 but failed")
            else:
                print(f"  -> Server may not support H3 upload")
        else:
            print(f"  ✓ Upload success")
    except subprocess.TimeoutExpired:
        print(f"  ✗ Upload timeout after {TIMEOUT_SEC*2}s")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    finally:
        # Clean up dummy file immediately
        if os.path.exists(filename): 
            os.remove(filename)

# ==========================================
# 5. MAIN LOOP
# ==========================================

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    print("=" * 70)
    print("HTTP/3 Traffic Generator (HTTP/3-ONLY Mode)")
    print("=" * 70)
    print(f"Upload target: {VALID_UPLOAD_TARGETS[0]}")
    print(f"Upload size: {UPLOAD_SIZE_MB}MB per cycle")
    print(f"Download: {DOWNLOAD_PHOTOS} photos + {DOWNLOAD_WEBSITES} websites per cycle")
    print("=" * 70)

    # Clean up old processes
    subprocess.run(["sudo", "killall", "tcpdump"], stderr=subprocess.DEVNULL)

    try:
        user_val = input("\nEnter loop count (Enter=Infinite): ").strip()
        max_cycles = int(user_val) if user_val else 0
    except:
        max_cycles = 0

    cycle_count = 1
    
    try:
        while True:
            if max_cycles > 0 and cycle_count > max_cycles:
                break

            print(f"\n{'=' * 70}")
            print(f" CYCLE #{cycle_count}" + (f" / {max_cycles}" if max_cycles > 0 else ""))
            print(f"{'=' * 70}")
            
            # --- STEP 1: CAPTURE PACKETS ---
            pcap_name = f"traffic_session_{get_timestamp()}.pcap"
            tcp_proc = start_tcpdump(pcap_name)
            time.sleep(2) 
            
            # --- STEP 2: DOWNLOAD (Background Noise) ---
            print("[TRAFFIC] 2. Download Phase (HTTP/3)...")
            
            # Download multiple photos
            print(f"  Downloading {DOWNLOAD_PHOTOS} photos...")
            for i in range(DOWNLOAD_PHOTOS):
                photo_url = get_random_photo_url()
                run_download_action(photo_url, "photo")
                time.sleep(0.2)  # Reduce delay to speed up
            
            # Download multiple websites
            num_websites = DOWNLOAD_WEBSITES
            print(f"  Downloading {num_websites} websites...")
            for i in range(num_websites):
                website_url = get_random_website_url()
                run_download_action(website_url, "website")
                time.sleep(0.2)  # Reduce delay to speed up
            
            # --- STEP 3: UPLOAD (Main Data) ---
            print(f"[TRAFFIC] 3. Upload Phase (HTTP/3, {UPLOAD_SIZE_MB}MB)...")
            run_upload_action()
            
            # --- STEP 4: STOP PACKET CAPTURE ---
            time.sleep(2) 
            stop_tcpdump(tcp_proc)
            
            # --- STEP 5: REST ---
            print(f"\n[SYSTEM] Resting {REST_TIME}s...")
            time.sleep(REST_TIME)
            cycle_count += 1
            
    except KeyboardInterrupt:
        print("\n[STOP] Script stopped by user.")
    finally:
        print("\n[CLEANUP] Cleaning up...")
        subprocess.run(["sudo", "killall", "tcpdump"], stderr=subprocess.DEVNULL)
        # Delete temporary upload files if any remain
        for f in os.listdir("."):
            if f.startswith("up_") and f.endswith(".bin"):
                try:
                    os.remove(f)
                except:
                    pass
        print("[DONE] Finished.")

if __name__ == "__main__":
    main()