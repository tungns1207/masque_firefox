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

# Proxy Configuration (Masque Client)
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 1080
PROXY_URL = f"socks5h://{PROXY_HOST}:{PROXY_PORT}"  # socks5h to resolve DNS via proxy

# Traffic Configuration
UPLOAD_SIZE_MB = 5 
DOWNLOAD_PHOTOS = 8     # Number of photos downloaded per cycle
DOWNLOAD_WEBSITES = 40    # Number of websites downloaded per cycle (8-10)
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
# 3. SYSTEM FUNCTIONS (PCAP & PROXY)
# ==========================================

def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def start_tcpdump(filename):
    """Start recording PCAP file, filter out VNC ports"""
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
    print("[SYSTEM] 6. Stopping TCPDUMP...")
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        subprocess.run(["sudo", "kill", "-9", str(proc.pid)], stderr=subprocess.DEVNULL)
        proc.wait()
    except Exception as e:
        print(f"  -> Error stopping tcpdump: {e}")

def start_proxy():
    """Start Masque Client (Proxy)"""
    print(f"[PROXY]  2. Starting Masque Client...")
    
    # Clean old processes if any
    subprocess.run(["pkill", "-9", "masque-plus"], stderr=subprocess.DEVNULL)
    time.sleep(2)  # Increased wait for cleanup
    
    cmd = [
        "./masque-plus", "--endpoint", "162.159.198.2:443"
    ]
    
    # Capture output for debugging
    proc = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid,
        text=True
    )
    
    # Wait longer for proxy to establish connection
    print("  -> Waiting for proxy to establish QUIC connection...")
    time.sleep(8)  # Increased from 5 to 8 seconds
    
    # Check if process is still running
    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        print("  -> ERROR: masque-plus exited prematurely!")
        print(f"  -> STDOUT: {stdout[:200]}")
        print(f"  -> STDERR: {stderr[:200]}")
        return None
    
    # Test if proxy is actually listening
    for attempt in range(3):
        test_result = subprocess.run(
            ["netstat", "-tuln"], 
            capture_output=True, 
            text=True
        )
        if f":{PROXY_PORT}" in test_result.stdout:
            print(f"  ✓ Masque client started (PID: {proc.pid})")
            print(f"  ✓ Proxy listening on {PROXY_HOST}:{PROXY_PORT}")
            return proc
        else:
            if attempt < 2:
                print(f"  -> Port not ready yet, waiting... (attempt {attempt + 1}/3)")
                time.sleep(2)
    
    print(f"  ✗ WARNING: Proxy may not be fully ready on port {PROXY_PORT}")
    print(f"  -> Continuing anyway, PID: {proc.pid}")
    return proc

def stop_proxy(proc):
    """Stop Masque Client"""
    print("[PROXY]  5. Stopping Masque Client (Closing Flow)...")
    
    if proc:
        try:
            print(f"  -> Killing process group for PID {proc.pid}...")
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception as e:
            print(f"  -> Could not kill process group: {e}")
    
    subprocess.run(["pkill", "-9", "masque-plus"], stderr=subprocess.DEVNULL)
    time.sleep(1)

def get_random_string(length=10):
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def generate_dummy_file(filename, size_mb):
    """Generate dummy file with random content (hard to compress)"""
    actual_size = size_mb + random.uniform(-0.5, 0.5)
    if actual_size < 0.1: actual_size = 0.1
    with open(filename, 'wb') as f:
        f.write(os.urandom(int(actual_size * 1024 * 1024)))

# ==========================================
# 4. TRAFFIC FUNCTIONS (CURL HTTP/3 WITH PROXY)
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
    """Download via MASQUE PROXY (proxy handles HTTP/3)"""
    type_label = "PHOTO" if download_type == "photo" else "WEB"
    print(f"  [{type_label}] {target}")
    
    cmd = [
        CURL_PATH, 
        "--proxy", PROXY_URL,   # Route through Masque - IT handles HTTP/3
        # NOTE: NO --http3-only! Masque proxy converts traffic to HTTP/3
        "--ipv4",               # IPv4 only
        "-k",                   # Ignore SSL errors
        "-L",                   # Follow redirects
        "-s",                   # Silent mode
        "-o", "/dev/null",      # Discard output
        "--max-time", str(TIMEOUT_SEC), 
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        target
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=TIMEOUT_SEC+5)
        if result.returncode != 0:
            stderr = result.stderr.decode('utf-8', errors='ignore')
            stdout = result.stdout.decode('utf-8', errors='ignore')
            print(f"    ✗ Failed (code {result.returncode})")
            
            # Detailed error messages for common issues
            if result.returncode == 3:
                print(f"    -> Error 3: Proxy connection failed")
                print(f"    -> Is masque-plus running? Check: ps aux | grep masque")
            elif result.returncode == 7:
                print(f"    -> Error 7: Failed to connect to host")
            elif result.returncode == 28:
                print(f"    -> Error 28: Timeout")
            
            if stderr:
                print(f"    -> STDERR: {stderr[:150]}")
        else:
            print(f"    ✓ Success")
    except subprocess.TimeoutExpired:
        print(f"    ✗ Timeout after {TIMEOUT_SEC}s")
    except Exception as e:
        print(f"    ✗ Error: {e}")

def run_upload_action():
    """Upload via MASQUE PROXY (proxy handles HTTP/3)"""
    target = random.choice(VALID_UPLOAD_TARGETS)
    filename = f"up_{get_random_string(5)}.bin"
    generate_dummy_file(filename, UPLOAD_SIZE_MB)
    
    print(f"  [UP]   {target} ({UPLOAD_SIZE_MB}MB via Masque Proxy)")
    
    cmd = [
        CURL_PATH, 
        "--proxy", PROXY_URL,   # Route through Masque - IT handles HTTP/3
        # NOTE: NO --http3-only! Masque proxy converts traffic to HTTP/3
        "--ipv4",               # IPv4 only
        "-k",                   # Ignore SSL errors
        "-s",                   # Silent mode
        "-o", "/dev/null",      # Discard response
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
            if 'proxy' in stderr.lower():
                print(f"  -> Proxy error - check masque-plus")
            if stderr:
                print(f"  -> STDERR: {stderr[:150]}")
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
    print("HTTP/3 Traffic Generator WITH MASQUE PROXY")
    print("=" * 70)
    print(f"Proxy: {PROXY_URL}")
    print(f"Note: Masque proxy handles HTTP/3 conversion")
    print(f"Upload size: {UPLOAD_SIZE_MB}MB per cycle")
    print(f"Download: {DOWNLOAD_PHOTOS} photos + {DOWNLOAD_WEBSITES}-{DOWNLOAD_WEBSITES+2} websites per cycle")
    print("=" * 70)

    # Clean up old processes
    subprocess.run(["sudo", "killall", "tcpdump"], stderr=subprocess.DEVNULL)
    subprocess.run(["pkill", "-9", "masque-plus"], stderr=subprocess.DEVNULL)

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
            pcap_name = f"proxy_traffic_{get_timestamp()}.pcap"
            tcp_proc = start_tcpdump(pcap_name)
            time.sleep(2) 
            
            # --- STEP 2: START PROXY ---
            masque_proc = start_proxy()
            
            if masque_proc is None:
                print("[ERROR] Failed to start masque-plus. Skipping traffic.")
                stop_tcpdump(tcp_proc)
                time.sleep(REST_TIME)
                cycle_count += 1
                continue
            
            # CRITICAL: Wait longer for proxy to be fully ready
            print("  -> Waiting for proxy to be fully ready...")
            time.sleep(3)
            
            # Verify proxy is still running
            if masque_proc.poll() is not None:
                print("[ERROR] Proxy died after starting. Skipping traffic.")
                stop_tcpdump(tcp_proc)
                time.sleep(REST_TIME)
                cycle_count += 1
                continue
            
            # --- STEP 3: DOWNLOAD (Traffic via Proxy) ---
            print("[TRAFFIC] 3. Download Phase (HTTP/3 via Proxy)...")
            
            # Download multiple photos
            print(f"  Downloading {DOWNLOAD_PHOTOS} photos...")
            for i in range(DOWNLOAD_PHOTOS):
                photo_url = get_random_photo_url()
                run_download_action(photo_url, "photo")
                time.sleep(0.2)  # Reduce delay to speed up
            
            # Download multiple websites
            num_websites = random.randint(DOWNLOAD_WEBSITES, DOWNLOAD_WEBSITES + 2)
            print(f"  Downloading {num_websites} websites...")
            for i in range(num_websites):
                website_url = get_random_website_url()
                run_download_action(website_url, "website")
                time.sleep(0.2)  # Reduce delay to speed up
            
            # --- STEP 4: UPLOAD (Traffic via Proxy) ---
            print(f"[TRAFFIC] 4. Upload Phase (HTTP/3 via Proxy, {UPLOAD_SIZE_MB}MB)...")
            run_upload_action()
            
            # --- STEP 5: STOP PROXY ---
            stop_proxy(masque_proc)
            time.sleep(2)
            
            # --- STEP 6: STOP TCPDUMP ---
            stop_tcpdump(tcp_proc)
            
            # --- STEP 7: REST ---
            print(f"\n[SYSTEM] Resting {REST_TIME}s...")
            time.sleep(REST_TIME)
            cycle_count += 1
            
    except KeyboardInterrupt:
        print("\n[STOP] Script stopped by user.")
    finally:
        print("\n[CLEANUP] Cleaning up...")
        subprocess.run(["sudo", "killall", "tcpdump"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-9", "masque-plus"], stderr=subprocess.DEVNULL)
        
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