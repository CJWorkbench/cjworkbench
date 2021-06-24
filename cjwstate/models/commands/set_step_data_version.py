import datetime

import dateutil.parser

from .base import BaseCommand
from .util import ChangesStepOutputs


class SetStepDataVersion(ChangesStepOutputs, BaseCommand):
    def forward(self, delta):
        delta.step.stored_data_version = dateutil.parser.isoparse(
            delta.values_for_forward["version"]
        ).replace(tzinfo=None)
        delta.step.save(update_fields=["stored_data_version"])
        self.forward_affected_delta_ids(delta)

    def backward(self, delta):
        old_version_str = delta.values_for_backward["version"]
        if old_version_str is None:
            old_version = None
        else:
            old_version = dateutil.parser.isoparse(old_version_str).replace(tzinfo=None)
        delta.step.stored_data_version = old_version
        delta.step.save(update_fields=["stored_data_version"])
        self.backward_affected_delta_ids(delta)

    # override
    def get_modifies_render_output(self, delta) -> bool:
        """Tell renderers to render the new workflow, _maybe_."""
        return True

    def amend_create_kwargs(self, *, step, new_version, **kwargs):
        old_version = step.stored_data_version
        if old_version is None:
            old_version_str = None
        else:
            old_version_str = old_version.isoformat()

        new_version_str = new_version.isoformat()

        return {
            **kwargs,
            "step": step,
            "values_for_backward": {"version": old_version_str},
            "values_for_forward": {"version": new_version_str},
            "step_delta_ids": self.affected_step_delta_ids(step),
        }
