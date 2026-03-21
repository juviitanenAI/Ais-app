import os
import re
import subprocess
import pytest

CONFIG_PATH = 'frontend/src/lib/config.js'

def get_versions():
    with open(CONFIG_PATH, 'r') as f:
        content = f.read()
    app_v = re.search(r"export const APP_VERSION = '(\d+)\.(\d+)';", content)
    mob_v = re.search(r"export const MOBILE_VERSION = '(\d+)\.(\d+)';", content)
    return (app_v.group(1), app_v.group(2)) if app_v else None, \
           (mob_v.group(1), mob_v.group(2)) if mob_v else None

def test_make_bump_version():
    # 1. Backup original config
    with open(CONFIG_PATH, 'r') as f:
        original_content = f.read()
    
    try:
        # 2. Get current versions
        old_app, old_mob = get_versions()
        assert old_app is not None
        assert old_mob is not None
        
        # 3. Run make bump_version
        result = subprocess.run(['make', 'bump_version'], capture_output=True, text=True)
        assert result.returncode == 0
        assert "Bumped version to" in result.stdout
        
        # 4. Get new versions
        new_app, new_mob = get_versions()
        
        # 5. Verify increment (simple check for minor bump)
        # Handle overflow 9 -> 0
        expected_mi = (int(old_app[1]) + 1) % 10
        expected_ma = int(old_app[0]) + (1 if int(old_app[1]) == 9 else 0)
        
        assert int(new_app[0]) == expected_ma
        assert int(new_app[1]) == expected_mi
        assert new_app == new_mob

    finally:
        # 6. Restore original config
        with open(CONFIG_PATH, 'w') as f:
            f.write(original_content)

if __name__ == "__main__":
    test_make_bump_version()
    print("Test passed!")
