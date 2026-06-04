with open(r'D:\work\research\agents-nexus\packages\ui\src\pages\TaskDetail.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the errors in the Tabs section
content = content.replace("value={selectedTaskId}", "value={selectedSubTask}")
content = content.replace("t.id !== taskId", "t.id !== task.id")
content = content.replace("onClick={addSubTask}", "onClick={addSubIssue}")
content = content.replace("disabled={!selectedTaskId}", "disabled={!selectedSubTask}")
content = content.replace("setSelectedTaskId(e.target.value)", "setSelectedSubTask(e.target.value)")

with open(r'D:\work\research\agents-nexus\packages\ui\src\pages\TaskDetail.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
print("Done")
