import datetime

import dateutil.parser
from django.db import models

from ..delta import Delta
from ..step import Step
from .util import ChangesStepOutputs


class ChangeDataVersionCommand(ChangesStepOutputs, Delta):
    class Meta:
        app_label = "server"
        proxy = True

    def forward(self):
        self.step.stored_data_version = dateutil.parser.isoparse(
            self.values_for_forward["version"]
        )
        self.step.save(update_fields=["stored_data_version"])
        self.forward_affected_delta_ids()

    def backward(self):
        old_version_str = self.values_for_backward["version"]
        if old_version_str is None:
            old_version = None
        else:
            old_version = dateutil.parser.isoparse(old_version_str)
        self.step.stored_data_version = old_version
        self.step.save(update_fields=["stored_data_version"])
        self.backward_affected_delta_ids()

    # override
    def get_modifies_render_output(self) -> bool:
        """Tell renderers to render the new workflow, _maybe_."""
        return True

    @classmethod
    def amend_create_kwargs(cls, *, step, new_version, **kwargs):
        old_version = step.stored_data_version
        if old_version is None:
            old_version_str = None
        else:
            old_version_str = (
                old_version.astimezone(datetime.timezone.utc)
                .isoformat()
                .replace("+00:00", "Z")
            )

        new_version_str = (
            new_version.astimezone(datetime.timezone.utc)
            .isoformat()
            .replace("+00:00", "Z")
        )

        return {
            **kwargs,
            "step": step,
            "values_for_backward": {"version": old_version_str},
            "values_for_forward": {"version": new_version_str},
            "step_delta_ids": cls.affected_step_delta_ids(step),
        }
