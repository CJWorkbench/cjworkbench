from django.test.utils import override_settings

from cjwkernel.tests.util import tempfile_context
from cjwstate.models import Workflow
from cjwstate.storedobjects.io import (
    create_stored_object,
    delete_old_files_to_enforce_storage_limits,
)
from cjwstate.tests.utils import DbTestCase


class EnforceStorageLimitsTests(DbTestCase):
    @override_settings(MAX_BYTES_FETCHES_PER_STEP=99999999)
    def test_common_case_no_op(self):
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(order=1, module_id_name="x")

        with tempfile_context() as path:
            # Write two storedobjects
            path.write_text("abc123")
            create_stored_object(workflow.id, step.id, path)
            path.write_text("def456")
            create_stored_object(workflow.id, step.id, path)

        delete_old_files_to_enforce_storage_limits(step=step)
        self.assertEqual(step.stored_objects.count(), 2)

    @override_settings(MAX_BYTES_FETCHES_PER_STEP=70)
    def test_too_many_bytes_delete_oldest(self):
        # ... and we also test that we can delete _multiple_ objects to make
        # way for a single one
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(order=1, module_id_name="x")

        with tempfile_context() as path:
            # Write four storedobjects
            path.write_text("10 bytes..")
            create_stored_object(workflow.id, step.id, path)
            path.write_text("20 bytes............")
            create_stored_object(workflow.id, step.id, path)
            path.write_text("40 bytes................................")
            so3 = create_stored_object(workflow.id, step.id, path)
            path.write_text("30 bytes......................")
            so4 = create_stored_object(workflow.id, step.id, path)  # newest

        delete_old_files_to_enforce_storage_limits(step=step)
        self.assertEqual(
            list(
                step.stored_objects.order_by("-stored_at").values_list("id", flat=True)
            ),
            [so4.id, so3.id],
        )

    @override_settings(MAX_BYTES_FETCHES_PER_STEP=20)
    def test_always_leave_one(self):
        # ... and we also test that we can delete _multiple_ objects to make
        # way for a single one
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(order=1, module_id_name="x")

        with tempfile_context() as path:
            # Write four storedobjects
            path.write_text("10 bytes..")
            create_stored_object(workflow.id, step.id, path)
            path.write_text("30 bytes......................")
            so2 = create_stored_object(workflow.id, step.id, path)  # newest

        delete_old_files_to_enforce_storage_limits(step=step)
        self.assertEqual(
            list(step.stored_objects.values_list("id", flat=True)), [so2.id]
        )

    @override_settings(MAX_N_FETCHES_PER_STEP=2)
    def test_too_many_files_delete_oldest(self):
        # ... and we also test that we can delete _multiple_ objects to make
        # way for a single one
        workflow = Workflow.create_and_init()
        step = workflow.tabs.first().steps.create(order=1, module_id_name="x")

        with tempfile_context() as path:
            # Write four storedobjects
            path.write_text("10 bytes..")
            create_stored_object(workflow.id, step.id, path)
            path.write_text("10 bytes..")
            create_stored_object(workflow.id, step.id, path)
            path.write_text("10 bytes..")
            so3 = create_stored_object(workflow.id, step.id, path)
            path.write_text("10 bytes..")
            so4 = create_stored_object(workflow.id, step.id, path)  # newest

        delete_old_files_to_enforce_storage_limits(step=step)
        self.assertEqual(
            list(
                step.stored_objects.order_by("-stored_at").values_list("id", flat=True)
            ),
            [so4.id, so3.id],
        )
