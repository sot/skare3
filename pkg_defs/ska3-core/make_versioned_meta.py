import subprocess
import json
result = subprocess.run(['conda', 'list', '--no-pip', '--json'], stdout=subprocess.PIPE)
pkgs = json.loads(result.stdout)
for pkg in pkgs:
    if pkg['channel'] == 'defaults':
        print("   - {name} =={version}".format(**pkg))
