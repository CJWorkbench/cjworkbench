from django.test.utils import override_settings
from cjwstate.models import Workflow
from cjwstate.storedobjects.io import create_stored_object, enforce_storage_limits
from cjwstate.tests.utils import DbTestCase
from cjwkernel.tests.util import tempfile_context


class EnforceStorageLimitsTests(DbTestCase):
    @override_settings(MAX_STORAGE_PER_MODULE=99999999)
    def test_common_case_no_op(self):
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=1, module_id_name="x")

        with tempfile_context() as path:
            # Write two storedobjects
            path.write_text("abc123")
            create_stored_object(workflow.id, wf_module.id, path)
            path.write_text("def456")
            create_stored_object(workflow.id, wf_module.id, path)

        enforce_storage_limits(wf_module)
        self.assertEqual(wf_module.stored_objects.count(), 2)

    @override_settings(MAX_STORAGE_PER_MODULE=70)
    def test_delete_oldest(self):
        # ... and we also test that we can delete _multiple_ objects to make
        # way for a single one
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=1, module_id_name="x")

        with tempfile_context() as path:
            # Write four storedobjects
            path.write_text("10 bytes..")
            create_stored_object(workflow.id, wf_module.id, path)
            path.write_text("20 bytes............")
            create_stored_object(workflow.id, wf_module.id, path)
            path.write_text("40 bytes................................")
            so3 = create_stored_object(workflow.id, wf_module.id, path)
            path.write_text("30 bytes......................")
            so4 = create_stored_object(workflow.id, wf_module.id, path)  # newest

        enforce_storage_limits(wf_module)
        self.assertEqual(
            list(
                wf_module.stored_objects.order_by("-stored_at").values_list(
                    "id", flat=True
                )
            ),
            [so4.id, so3.id],
        )

    @override_settings(MAX_STORAGE_PER_MODULE=20)
    def test_always_leave_one(self):
        # ... and we also test that we can delete _multiple_ objects to make
        # way for a single one
        workflow = Workflow.create_and_init()
        wf_module = workflow.tabs.first().wf_modules.create(order=1, module_id_name="x")

        with tempfile_context() as path:
            # Write four storedobjects
            path.write_text("10 bytes..")
            create_stored_object(workflow.id, wf_module.id, path)
            path.write_text("30 bytes......................")
            so2 = create_stored_object(workflow.id, wf_module.id, path)  # newest

        enforce_storage_limits(wf_module)
        self.assertEqual(
            list(wf_module.stored_objects.values_list("id", flat=True)), [so2.id]
        )
