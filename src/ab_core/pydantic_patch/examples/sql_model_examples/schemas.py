from ab_core.pydantic_patch.patch import Patch, PatchConfig

from ab_core.pydantic_patch.examples.sql_model_examples.models import (
    Project,
    ProjectMilestone,
    ProjectTask,
    TaskComment,
)


ProjectPatch = Patch[Project](
    pick={"id", "name", "milestones"},
    required={"id"},
    child_models={
        ProjectMilestone: PatchConfig(
            pick={"id", "name", "tasks"},
            required={"id"},
        ),
        ProjectTask: PatchConfig(
            pick={"id", "title", "comments"},
            required={"id"},
        ),
        TaskComment: PatchConfig(
            pick={"id", "body"},
            required={"id"},
        ),
    },
)