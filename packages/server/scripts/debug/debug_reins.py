"""Debug reins and agents inside API context"""
import sys
sys.path.insert(0, 'src')

# Import reins like the API does
from reins.api.server import reins

print(f"reins: {reins}")
print(f"reins type: {type(reins)}")

if reins:
    agents = reins.get_registered_agents()
    print(f"Agents: {len(agents)}")
    for a in agents:
        print(f"  Agent: {a.id}, {a.name}")
        print(f"    capabilities: {a.capabilities}")
        print(f"    type: {type(a)}")
else:
    print("reins is None!")
