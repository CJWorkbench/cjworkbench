from django.db import models
from server.models import Delta


class ChangeWorkflowTitleCommand(Delta):
    new_value = models.TextField('new_value')
    old_value = models.TextField('old_value')

    def forward_impl(self):
        self.workflow.name = self.new_value
        self.workflow.save(update_fields=['name'])

    def backward_impl(self):
        self.workflow.name = self.old_value
        self.workflow.save(update_fields=['name'])

    @classmethod
    async def create(cls, workflow, name):
        old_name = workflow.name

        delta = await cls.create_impl(
            workflow=workflow,
            new_value=name,
            old_value=old_name
        )

        return delta

    @property
    def command_description(self):
        return f'Change workflow name to {self.new_value}'
