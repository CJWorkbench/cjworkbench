import datetime
from typing import List, Optional
from allauth.account.utils import user_display
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from pandas import DataFrame
from django.conf import settings
from server.utils import get_absolute_url
from server.pandas_util import are_tables_equal


class OutputDelta:
    """Description of changes between two versions of WfModule output."""
    def __init__(self, fetched_table_version: datetime.datetime,
                 wf_module: 'WfModule', old_table: Optional[DataFrame],
                 new_table: Optional[DataFrame]):
        workflow = wf_module.workflow

        self.fetched_table_version = fetched_table_version
        self.user = workflow.owner
        self.workflow_name = workflow.name
        self.module_name = wf_module.get_module_name()
        self.workflow_url = get_absolute_url(workflow.get_absolute_url())
        self.old_table = old_table
        self.new_table = new_table


def find_output_deltas_to_notify_from_fetched_tables(
        wf_module: 'WfModule', old_table: Optional[DataFrame],
        new_table: Optional[DataFrame]) -> List[OutputDelta]:
    """Compute a list of OutputDeltas to email to the owner.

    `wf_module` is the fetch module whose data just changed from `old_table` to
    `new_table`. (Either may be `None` or empty.)

    Assumes `old_table` and `new_table` are different.

    Must be called within a workflow.cooperative_lock().

    TODO make this easier to unit-test, and then unit-test it.
    """
    # Import here, to prevent recursive import
    from server.dispatch import module_dispatch_render

    output_deltas = []

    all_modules = list(wf_module.workflow.wf_modules.all())

    # Truncate all_modules: nix all after the last `.notifications` module
    while all_modules and not all_modules[-1].notifications:
        all_modules.pop()

    # Advance in the list up until one _after_ `wf_module`
    while all_modules and all_modules[0].id != wf_module.id:
        all_modules.pop(0)
    if all_modules:
        # remove wf_module itself
        all_modules.pop(0)

    fetched_version = wf_module.stored_data_version

    if wf_module.notifications:
        # Notify on wf_module itself
        output_deltas.append(OutputDelta(fetched_version, wf_module,
                                         old_table.copy(), new_table.copy()))

    # Now iterate through dependent modules: calculate tables and compare
    for wf_module in all_modules:
        old_table = module_dispatch_render(wf_module, old_table)
        new_table = module_dispatch_render(wf_module, new_table)

        if are_tables_equal(old_table, new_table):
            # From this point forward, tables will never diverge so we should
            # never notify the user.
            return output_deltas

        if wf_module.notifications:
            output_deltas.append(OutputDelta(fetched_version, wf_module,
                                             old_table.copy(),
                                             new_table.copy()))

    return output_deltas

def email_output_delta(output_delta: OutputDelta):
    user = output_delta.user

    ctx = {
        'user_name': user_display(user),
        'module_name': output_delta.module_name,
        'workflow_name': output_delta.workflow_name,
        'workflow_url': output_delta.workflow_url,
        'date': output_delta.fetched_table_version.strftime('%b %-d, %Y at %-I:%M %p')
    }
    subject = render_to_string("notifications/new_data_version_subject.txt", ctx)
    subject = "".join(subject.splitlines())
    message = render_to_string("notifications/new_data_version.txt", ctx)
    mail = EmailMultiAlternatives(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    mail.attach_alternative(message, "text/html")
    mail.send()
