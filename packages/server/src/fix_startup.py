import sys, os
sys.path.insert(0, 'D:/work/research/agents-nexus/packages/server/src')
os.chdir('D:/work/research/agents-nexus/packages/server/src')
with open('reins/api/workflows.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Replace lines 198-208 with fixed version
new_lines = lines[:198]
new_lines.append('    try:\n')
new_lines.append('        bus_manager = get_event_bus_manager()\n')
new_lines.append('        bus = bus_manager.get_adapter(None)\n')
new_lines.append('        \n')
new_lines.append('        if bus:\n')
new_lines.append('            # Register event listeners with individual try/except\n')
new_lines.append('            try:\n')
new_lines.append('                bus.subscribe("task_completed", _on_task_completed)\n')
new_lines.append('            except Exception as e:\n')
new_lines.append('                print(f"[MA-K233-2] subscribe task_completed error: {e}")\n')
new_lines.append('            try:\n')
new_lines.append('                bus.subscribe("task_failed", _on_task_failed)\n')
new_lines.append('            except Exception as e:\n')
new_lines.append('                print(f"[MA-K233-2] subscribe task_failed error: {e}")\n')
new_lines.append('            print("[MA-K233-2] Workflow event listeners registered")\n')
new_lines.append('    except Exception as e:\n')
new_lines.append('        print(f"[MA-K233-2] Event listener registration error: {e}")\n')
new_lines.extend(lines[208:])

with open('reins/api/workflows.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'Fixed workflows.py, total lines: {len(new_lines)}')

# Also remove the debug code from server.py heartbeat_agent
with open('reins/api/server.py', 'r', encoding='utf-8') as f:
    server_lines = f.readlines()

# Remove lines 1203-1205 (the with open and raise)
new_server_lines = []
skip_next = 0
for i, line in enumerate(server_lines):
    if skip_next > 0:
        skip_next -= 1
        continue
    if 'with open' in line and 'hb_debug' in line:
        skip_next = 1  # skip next line too
        continue
    if 'raise Exception' in line and 'HB-FORCE-BREAK' in line:
        continue  # skip this line
    new_server_lines.append(line)

with open('reins/api/server.py', 'w', encoding='utf-8') as f:
    f.writelines(new_server_lines)

print(f'Fixed server.py, total lines: {len(new_server_lines)}')
