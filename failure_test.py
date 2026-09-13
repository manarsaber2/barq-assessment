import sys
import time
import urllib.request
import subprocess

BASE_URL = "http://localhost:8080"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def check_endpoint(path):
    try:
        req = urllib.request.Request(f"{BASE_URL}{path}", headers={"User-Agent": "BarqFailureTest/1.0", "Connection": "close"})
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.getcode(), response.read().decode('utf-8')
    except Exception as e:
        return 0, str(e)

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.returncode == 0, result.stdout.strip()

def main():
    log("Starting failure & recovery resilience test...")
    
    # 1. Ensure app-01 is running before test
    run_cmd("docker start app-01")
    time.sleep(2)

    code, _ = check_endpoint("/")
    if code != 200:
        log("System is not healthy initially. Aborting test.", "FAIL")
        sys.exit(1)
    
    log("Initial state healthy. Stopping container 'app-01'...", "INFO")
    
    # 2. Kill app-01 to simulate instant container failure
    success, _ = run_cmd("docker kill app-01")
    if not success:
        log("Failed to kill container app-01.", "FAIL")
        sys.exit(1)
    
    log("Container app-01 killed. Waiting 3 seconds for Nginx passive check...", "INFO")
    time.sleep(3)
    
    # 3. Measure traffic during failure (Nginx should route seamlessly to app-02)
    success_count = 0
    failure_count = 0
    instances_hit = set()
    
    for i in range(10):
        code, body = check_endpoint("/instance")
        if code == 200:
            success_count += 1
            if "app-02" in body:
                instances_hit.add("app-02")
            elif "app-01" in body:
                instances_hit.add("app-01")
        else:
            failure_count += 1
        time.sleep(0.3)
        
    log(f"During failure - Success: {success_count}, Failures: {failure_count}, Instances seen: {instances_hit}", "INFO")
    
    if failure_count > 0 or "app-01" in instances_hit or "app-02" not in instances_hit:
        log("Resilience check failed: downtime or invalid instance detected.", "FAIL")
        run_cmd("docker start app-01")
        sys.exit(1)
    else:
        log("Resilience verified: 100% uptime with Nginx routing seamlessly to surviving backend (app-02).", "PASS")

    # 4. Restore the stopped container
    log("Restoring container 'app-01'...", "INFO")
    success, _ = run_cmd("docker start app-01")
    if not success:
        log("Failed to restart container app-01.", "FAIL")
        sys.exit(1)
        
    time.sleep(4)
    
    # 5. Verify recovery (both instances should be reachable again)
    recovered_instances = set()
    for i in range(12):
        code, body = check_endpoint("/instance")
        if code == 200 and "app-01" in body:
            recovered_instances.add("app-01")
        time.sleep(0.3)
        
    if "app-01" in recovered_instances:
        log("Recovery verified: app-01 successfully restored and serving requests.", "PASS")
        sys.exit(0)
    else:
        log("Recovery check failed: app-01 not serving requests after restart.", "FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()