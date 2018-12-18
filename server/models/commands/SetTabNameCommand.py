from django.db import models
from server.models import Delta, Tab


class SetTabNameCommand(Delta):
    """Set a tab name."""
    tab = models.ForeignKey(Tab, on_delete=models.PROTECT)
    old_name = models.TextField()
    new_name = models.TextField()

    def load_ws_data(self):
        data = super().load_ws_data()
        data['updateTabs'] = {
            str(self.tab_id): {'name': self.tab.name}
        }
        return data

    def forward_impl(self):
        self.tab.name = self.new_name
        self.tab.save(update_fields=['name'])

    def backward_impl(self):
        self.tab.name = self.old_name
        self.tab.save(update_fields=['name'])

    @classmethod
    def amend_create_kwargs(cls, *, workflow, tab, new_name):
        if tab.name == new_name:
            return None

        return {
            'workflow': workflow,
            'tab': tab,
            'new_name': new_name,
            'old_name': tab.name,
        }

    async def schedule_execute(self):
        pass
