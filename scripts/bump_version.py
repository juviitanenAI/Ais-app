import re
import sys

def bump(match):
    ma, mi = int(match.group(1)), int(match.group(2))
    return f"{ma + (mi >= 9)}.{(mi + 1) % 10}"

def main():
    fp = 'frontend/src/lib/config.js'
    try:
        with open(fp, 'r') as f:
            content = f.read()
            
        v_app = re.search(r"export const APP_VERSION = '(\d+)\.(\d+)';", content)
        if not v_app:
            print("APP_VERSION string not found")
            sys.exit(1)
            
        new_v = bump(v_app)
            
        content = re.sub(r"export const APP_VERSION = '(\d+)\.(\d+)';", f"export const APP_VERSION = '{new_v}';", content)
        content = re.sub(r"export const MOBILE_VERSION = '(\d+)\.(\d+)';", f"export const MOBILE_VERSION = '{new_v}';", content)
        
        with open(fp, 'w') as f:
            f.write(content)
            
        print(f"Bumped version to {new_v}")
    except Exception as e:
        print(f"Error bumping version: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
