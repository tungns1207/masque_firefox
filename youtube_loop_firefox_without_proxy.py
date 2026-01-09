import subprocess
import time
import os
import signal
import datetime
import random
import undetected_geckodriver as uc
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- CONFIGURATION ---
INTERFACE = "eth0"
OUTPUT_DIR = "/home/headless/Documents"
PROXY_HOST = "127.0.0.1"
PROXY_PORT = 1080
WATCH_TIME = 80   # Video watch duration (seconds)
REST_TIME = 10    # Rest duration between cycles (seconds)

# IMPORTANT: Set this to YOUR actual Firefox profile path
# Leave empty to auto-detect, or set manually
FIREFOX_PROFILE_PATH = ""  # Will be auto-detected if empty

# Combined & deduplicated YouTube search keywords
SEARCH_KEYWORDS = [
    "asmr",
    "where winds meet",
    "music",
    "arc raiders",
    "song",
    "coryxkenshin",
    "mrbeast",
    "asmongold",
    "karaoke",
    "minecraft",
    "we are charlie kirk",
    "songs",
    "wwe",
    "dispatch",
    "lofi",
    "game awards 2025",
    "fortnite",
    "dhurandhar song",
    "phonk",
    "f1",
    "nba",
    "markiplier",
    "sourav joshi vlogs",
    "penguinz0",
    "sml",
    "ufc",
    "stranger things",
    "caseoh",
    "sidemen",
    "christmas music",
    "christmas songs",
    "dhurandhar movie trailer",
    "golden",
    "marvel rivals",
    "movies",
    "michael jackson",
    "youtube",
    "game awards",
    "stranger things season 5",
    "nfl",
    "ishowspeed",
    "jynxzi",
    "mr beast",
    "4k",
    "my mix",
    "tmkoc",
    "podcast",
    "candace owens",
    "roblox",
    "news",
    "hazbin hotel",
    "type beat",
    "musica",
    "cocomelon",
    "eminem",
    "nba youngboy",
    "movie",
    "ducky bhai",
    "moist critical",
    "dhurandhar",
    "movie reaction",
    "nick fuentes",
    "4k video",
    "taylor swift",
    "battlefield 6",
    "drake",
    "ign",
    "plaqueboymax",
    "bad bunny",
    "react to",
    "ashish chanchlani",
    "last christmas",
    "wemmbu",
    "the game awards 2025",
    "expedition 33",
    "techno gamerz",
    "아이온2",
    "katseye",
    "pal pal",
    "snl",
    "trailer",
    "trump",
    "linkin park",
    "valorant",
    "ekaki",
    "where winds meet gameplay",
    "sanwal yaar piya",
    "kpop demon hunters",
    "study music",
    "supergirl trailer",
    "real madrid",
    "wuthering waves",
    "r",
    "c",
    "hytale",
    "joe bartolozzi",
    "ludwig",
    "smiling friends",
    "white noise",
    "steam machine",

    # --- Add new keywords ---
    "bts",
    "pewdiepie",
    "billie eilish",
    "baby shark",
    "old town road",
    "badabun",
    "blackpink",
    "peliculas completas en español",
    "senorita",
    "ariana grande",
    "alan walker",
    "tik tok",
    "calma",
    "queen",
    "peppa pig",
    "despacito",
    "la rosa de guadalupe",
    "taki taki",
    "enes batur",
    "t series",
    "maluma",
    "bad guy",
    "ozuna",
    "nightcore",
    "paulo londra",
    "james charles",
    "imagine dragons",
    "dance monkey",
    "twice",
    "free fire",
    "gacha life",
    "post malone",
    "justin bieber",
    "felipe neto",
    "bruno mars",
    "7 rings",
    "china",
    "doraemon",
    "anuel",
    "kill this love",
    "jacksepticeye",
    "maroon 5",
    "joe rogan",
    "game of thrones",
    "marshmello",
    "david dobrik",
    "bohemian rhapsody",
    "lady gaga",
    "aaj tak live",
    "5 minute crafts",
    "cardi b",
    "geo news live",
    "selena gomez",
    "coldplay",
    "dantdm",
    "anuel aa",
    "rihanna",
    "dross",
    "los polinesios",
    "rap",
    "shawn mendes",
    "dua lipa",
    "funny videos",
    "mikecrack",
    "vegetta777",
    "pubg",
    "avengers endgame",
    "soolking",
    "believer",
    "gta 5",
    "romeo santos",
    "katy perry"
]


def get_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def find_firefox_profile():
    """Find the default Firefox profile automatically"""
    print("[PROFILE] Looking for Firefox profile...")
    
    # Common Firefox profile locations
    possible_paths = [
        os.path.expanduser("~/.mozilla/firefox"),
        "/home/headless/.mozilla/firefox",
    ]
    
    for base_path in possible_paths:
        if os.path.exists(base_path):
            # Look for profiles.ini
            profiles_ini = os.path.join(base_path, "profiles.ini")
            if os.path.exists(profiles_ini):
                print(f"  -> Found profiles.ini at: {profiles_ini}")
                
                # Parse profiles.ini to find default profile
                with open(profiles_ini, 'r') as f:
                    content = f.read()
                    
                # Look for default profile or any profile
                for line in content.split('\n'):
                    if line.startswith('Path='):
                        profile_name = line.split('=')[1].strip()
                        profile_path = os.path.join(base_path, profile_name)
                        if os.path.exists(profile_path):
                            print(f"  -> Found profile: {profile_path}")
                            return profile_path
            
            # If no profiles.ini, look for .default or .default-release folders
            try:
                for item in os.listdir(base_path):
                    if '.default' in item and os.path.isdir(os.path.join(base_path, item)):
                        profile_path = os.path.join(base_path, item)
                        print(f"  -> Found default profile: {profile_path}")
                        return profile_path
            except:
                pass
    
    print("  -> [WARNING] Could not auto-detect Firefox profile!")
    print("  -> You may need to set FIREFOX_PROFILE_PATH manually")
    return None

def start_tcpdump(filename):
    pcap_path = os.path.join(OUTPUT_DIR, filename)
    print(f"\n[SYSTEM] 1.Starting TCPDUMP -> {pcap_path}")
    
    cmd = [
        "sudo", "tcpdump", "-i", INTERFACE,
        "-w", pcap_path,
        "not", "port", "6901", "and", "not", "port", "5901"
    ]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc

def stop_tcpdump(proc):
    print("[SYSTEM] 5.Stopping TCPDUMP...")
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        subprocess.run(["sudo", "kill", "-9", str(proc.pid)], stderr=subprocess.DEVNULL)
        proc.wait()
    except Exception as e:
        print(f"  -> Error stopping tcpdump: {e}")

def start_proxy():
    print(f"[PROXY]  2. Starting Masque Client...")
    
    print("  -> Cleaning any existing masque-plus processes...")
    subprocess.run(["pkill", "-9", "masque-plus"], stderr=subprocess.DEVNULL)
    time.sleep(1)
    
    cmd = [
        "./masque-plus", "--endpoint", "162.159.198.2:443"
    ]
    
    proc = subprocess.Popen(
        cmd, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.DEVNULL,
        preexec_fn=os.setsid
    )
    
    time.sleep(3)
    
    if proc.poll() is not None:
        print("  -> WARNING: masque-plus exited prematurely!")
        return None
    
    print(f"  -> Masque client started (PID: {proc.pid})")
    return proc

def stop_proxy(proc):
    print("[PROXY]  4. Stopping Masque Client (Closing Flow)...")
    
    if proc:
        try:
            print(f"  -> Killing process group for PID {proc.pid}...")
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except Exception as e:
            print(f"  -> Could not kill process group: {e}")
    
    print("  -> Force killing all masque-plus processes...")
    subprocess.run(["pkill", "-9", "masque-plus"], stderr=subprocess.DEVNULL)
    time.sleep(1)

def run_firefox_session(profile_path):
    print("[BROWSER] 3. Starting Firefox session with YOUR profile...")
    print(f"  -> Using profile: {profile_path}")
    
    options = Options()
    
    # ========== USE YOUR REAL PROFILE (WHERE YOU'RE LOGGED IN) ==========
    options.add_argument("-profile")
    options.add_argument(profile_path)
    
    # Proxy settings
    #options.set_preference("network.proxy.type", 1)
    #options.set_preference("network.proxy.socks", PROXY_HOST)
    #options.set_preference("network.proxy.socks_port", PROXY_PORT)
    #options.set_preference("network.proxy.socks_version", 5)
    #options.set_preference("network.proxy.socks_remote_dns", True)
    
    # Media autoplay
    options.set_preference("media.autoplay.default", 0)
    options.set_preference("media.autoplay.allow-muted", True)
    options.set_preference("media.autoplay.blocking_enabled", False)
    
    # Minimal anti-detection (since we're using real profile, less needed)
    options.set_preference("dom.webdriver.enabled", False)
    
    driver = uc.Firefox(options=options)
    
    try:
        # Go to YouTube - you should already be logged in!
        print("  -> Loading YouTube (you should be logged in already)...")
        driver.get("https://www.youtube.com")
        time.sleep(4)
        
        # Check if logged in
        try:
            sign_in_button = driver.find_elements(By.XPATH, "//a[contains(@href, 'accounts.google.com')]")
            if sign_in_button and "Sign in" in sign_in_button[0].text:
                print("  -> [WARNING] Not logged in! You may need to sign in manually first.")
            else:
                print("  -> ✓ Appears to be logged in!")
        except:
            pass
        
        # Search for video
        keyword = random.choice(SEARCH_KEYWORDS)
        print(f"  -> Searching for: '{keyword}'")
        driver.get(f"https://www.youtube.com/results?search_query={keyword.replace(' ', '+')}")
        
        print("  -> Waiting for search results...")
        time.sleep(3)
        
        # Get video list
        videos = driver.find_elements(By.CSS_SELECTOR, "ytd-video-renderer a#thumbnail")
        
        if len(videos) > 0:
            limit = min(len(videos), 20)
            target = random.choice(videos[:limit])
            print(f"  -> Found {len(videos)} videos. Selected random one from top {limit}...")
            
            video_url = target.get_attribute("href")
            if video_url:
                print(f"  -> Navigating to video...")
                driver.get(video_url)
                time.sleep(6)
                
                # Check for VPN detection
                page_text = driver.page_source
                if "VPN/Proxy Detected" in page_text or "turn off your VPN" in page_text:
                    print("  -> [WARNING] YouTube still detected VPN/Proxy!")
                    print("  -> This means the proxy IP is blocked, not bot detection")
                    print("  -> Traffic is still being captured...")
                else:
                    print("  -> ✓ No VPN detection! Video should play normally")
                    
                    # Force play video
                    print("  -> Playing video...")
                    driver.execute_script("""
                        let video = document.querySelector('video');
                        if (video) {
                            video.muted = false;
                            video.play().then(() => {
                                console.log('Video playing');
                            }).catch(err => {
                                video.muted = true;
                                video.play();
                            });
                        }
                    """)
                    
                    # Scroll naturally
                    time.sleep(2)
                    driver.execute_script("window.scrollTo(0, 300);")
                    time.sleep(1)
                    driver.execute_script("window.scrollTo(0, 150);")
        else:
            print("  -> No videos found!")
        
        # Watch video
        print(f"  -> Watching for {WATCH_TIME}s...")
        time.sleep(WATCH_TIME)
        
    except Exception as e:
        print(f"  -> Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[BROWSER] Closing Firefox...")
        driver.quit()

def main():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print("=" * 70)
    print("YouTube Automation Script v8 - Using YOUR Real Firefox Profile")
    print("=" * 70)
    
    # Find Firefox profile
    if FIREFOX_PROFILE_PATH:
        profile_path = FIREFOX_PROFILE_PATH
        print(f"Using manually set profile: {profile_path}")
    else:
        profile_path = find_firefox_profile()
        
        if not profile_path:
            print("\n" + "=" * 70)
            print("ERROR: Could not find Firefox profile automatically!")
            print("=" * 70)
            print("\nTo find your profile manually:")
            print("1. Open Firefox normally")
            print("2. Type in address bar: about:profiles")
            print("3. Look for 'Root Directory' of your default profile")
            print("4. Copy that path and set it at the top of this script:")
            print("   FIREFOX_PROFILE_PATH = '/path/to/your/profile'")
            print("=" * 70)
            return
    
    if not os.path.exists(profile_path):
        print(f"\n[ERROR] Profile path does not exist: {profile_path}")
        print("Please check the path and try again.")
        return
    
    print(f"Profile found: {profile_path}")
    print("=" * 70)
    print("\nIMPORTANT: Make sure you're logged into YouTube in Firefox!")
    print("If not, open Firefox normally and sign in first, then run this script.")
    print("=" * 70)

    print("\n[INIT] Cleaning old processes...")
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
            
            pcap_name = f"youtube_session_{get_timestamp()}.pcap"
            
            tcp_proc = start_tcpdump(pcap_name)
            time.sleep(3) 
            
            #masque_proc = start_proxy()
            
            #if masque_proc is None:
            #    print("[ERROR] Failed to start masque-plus. Skipping this cycle.")
            #    stop_tcpdump(tcp_proc)
            #    time.sleep(REST_TIME)
            #    continue
            
            run_firefox_session(profile_path)
            
            #stop_proxy(masque_proc)
            time.sleep(2)
            
            stop_tcpdump(tcp_proc)
            
            print(f"\n[SYSTEM] Resting for {REST_TIME}s...")
            time.sleep(REST_TIME)
            cycle_count += 1
            
    except KeyboardInterrupt:
        print("\n[STOP] Script stopped by user.")
    finally:
        print("\n[CLEANUP] Final cleanup...")
        subprocess.run(["sudo", "killall", "tcpdump"], stderr=subprocess.DEVNULL)
        subprocess.run(["pkill", "-9", "masque-plus"], stderr=subprocess.DEVNULL)
        print("[DONE] All processes cleaned up.")

if __name__ == "__main__":
    main()