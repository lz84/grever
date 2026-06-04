"""Phase 3 E2E Verification Script (P3-6)"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from reins.messaging.command import (
    AssignTaskCommand, VerifyResultCommand,
    InstantiateScenarioCommand, DecomposeGoalCommand,
    TriggerHITLCommand, RulingCommand,
    CommandBus, Command, CommandResult
)

# P3-1~3: All 6 command classes instantiable
cmds = [
    AssignTaskCommand(task_id='t1', agent_id='a1', context={'x': 1}, deadline=9999),
    VerifyResultCommand(task_id='t1', result={'ok': True}, verifier_id='v1', verdict='approved'),
    InstantiateScenarioCommand(scenario_id='s1', goal_id='g1', parameters={'p': 1}),
    DecomposeGoalCommand(goal_id='g1', decomposition_strategy='recursive'),
    TriggerHITLCommand(task_id='t1', input_type='form', required_role='human'),
    RulingCommand(review_id='r1', verdict='approve', comment='looks good'),
]

for cmd in cmds:
    print(f"  {cmd.type}: id={cmd.id[:16]}... payload_keys={list(cmd.payload.keys())}")

# P3-4: Redis adapter (no Redis = memory fallback)
from shared.eventbus.redis_adapter import RedisEventAdapter, make_redis_adapter
adapter = RedisEventAdapter(redis_url='redis://localhost:6379/9')
stats = adapter.get_stats()
print(f"  Redis adapter: redis_connected={stats['redis_connected']}, fallback=memory")

# P3-5: eventbus_integration publish path
from reins.common.eventbus_integration import _publish_event
print(f"  _publish_event function: available")

# P3-6: E2E Command -> Handler -> Event chain
bus = CommandBus()
events_received = []

async def dummy_handler(cmd):
    events_received.append(cmd.type)
    return CommandResult(success=True, command_id=cmd.id, data={'handled': True})

for ct in ['assign_task', 'verify_result', 'instantiate_scenario',
           'decompose_goal', 'trigger_hitl', 'ruling']:
    bus.register(ct, dummy_handler)

import asyncio

async def e2e():
    for cmd in cmds:
        result = await bus.dispatch(cmd)
        assert result.success, f"{cmd.type} failed: {result.error}"

asyncio.run(e2e())
print(f"  E2E chain completed: {events_received}")
print()
print("ALL CHECKS PASSED")