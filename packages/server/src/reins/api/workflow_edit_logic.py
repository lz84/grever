"""Sprint 26: Workflow DAG 编辑 — Facade

Composes logic from split modules via mixin inheritance.
"""

from reins.api.workflow_edit_db import WorkflowEditDbMixin
from reins.api.workflow_edit_nodes import WorkflowEditNodeMixin
from reins.api.workflow_edit_edges import WorkflowEditEdgeMixin

class WorkflowEditLogic(WorkflowEditNodeMixin, WorkflowEditEdgeMixin):
    """Workflow DAG 编辑业务逻辑 — composed from mixins."""

    def __init__(self):
        # WorkflowEditDbMixin sets up _engine via property, no explicit init needed
        pass
