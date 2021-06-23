import datetime
from typing import Optional

from django.contrib.auth import get_user_model
from freezegun import freeze_time

from cjworkbench.models.price import Price
from cjworkbench.models.product import Product
from cjworkbench.models.subscription import Subscription
from cjworkbench.models.userlimits import UserLimits
from cjworkbench.models.userprofile import UserProfile
from cjwstate import commands
from cjwstate.models.delta import Delta
from cjwstate.models.workflow import Workflow

# Use SetWorkflowTitle and AddStep as "canonical" deltas -- one
# requiring Step, one not.
from cjwstate.models.commands import SetWorkflowTitle, AddStep
from cjwstate.tests.utils import (
    DbTestCaseWithModuleRegistryAndMockKernel,
    create_module_zipfile,
)
from cjworkbench.tests.utils import DbTestCase

from cron.deltadeleter import (
    delete_workflow_stale_deltas,
    find_workflows_with_stale_deltas,
)

User = get_user_model()

# sync functions to build undo history in the database without RabbitMQ
#
# do(), redo() and undo() work the same way as the real ones
def do(cls, workflow_id: int, **kwargs) -> Optional[Delta]:
    (
        delta,
        _,
        __,
        ___,
    ) = commands._first_forward_and_save_returning_clientside_updates.func(
        cls, workflow_id, **kwargs
    )
    return delta


redo = commands._call_forward_and_load_clientside_update.func
undo = commands._call_backward_and_load_clientside_update.func


def create_user(
    email="user@example.org", first_name="Name", last_name="Lastname", **kwargs
):
    user = User.objects.create(email=email, first_name=first_name, last_name=last_name)
    UserProfile.objects.create(user=user, **kwargs)
    return user


def create_product(
    *, stripe_product_id="prod_1", stripe_product_name="name", max_delta_age_in_days=3
):
    return Product.objects.create(
        stripe_product_id=stripe_product_id,
        stripe_product_name=stripe_product_name,
        max_delta_age_in_days=max_delta_age_in_days,
    )


def create_price(*, product, **kwargs):
    kwargs = {
        "stripe_price_id": "price_1",
        "stripe_active": True,
        "stripe_amount": 100,
        "stripe_currency": "usd",
        **kwargs,
    }
    return product.prices.create(**kwargs)


def create_subscription(user: User, price: Price, **kwargs):
    return Subscription.objects.create(
        user=user,
        price=price,
        created_at=datetime.datetime.now(),
        renewed_at=datetime.datetime.now(),
        **kwargs,
    )


def be_paranoid_and_assert_commands_apply(workflow: Workflow) -> None:
    """Run some excessive tests.

    This made sense [2021-02-02] when we first implemented this feature. But has
    it ever caught an error? It didn't on 2021-02-02 when it was added to every
    test.
    """
    workflow.refresh_from_db()
    name1 = workflow.name
    delta = do(SetWorkflowTitle, workflow.id, new_value="paranoid")
    workflow.refresh_from_db()
    assert workflow.last_delta_id == delta.id
    assert workflow.name == "paranoid"
    undo(workflow.id)
    workflow.refresh_from_db()
    assert workflow.name == name1


class DeleteWorkflowStaleDeltasTest(DbTestCaseWithModuleRegistryAndMockKernel):
    def test_keep_recent_done_deltas(self):
        workflow = Workflow.create_and_init()
        with freeze_time("2020-02-02"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))
        self.assertEqual(workflow.deltas.count(), 2)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_stale_done_deltas_before_fresh(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
        with freeze_time("2020-02-02"):
            delta3 = do(SetWorkflowTitle, workflow.id, new_value="baz")

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        # We delete up to the latest fresh one....
        self.assertEqual(workflow.deltas.first().id, delta3.id)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_stale_done_deltas_until_no_deltas_remain(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        self.assertEqual(workflow.deltas.count(), 0)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_fresh_done_delta_before_stale_done_delta(self):
        # In case clocks are out of sync or there's corrupt data
        #
        # We don't care whether we delete both or keep both; just that we never
        # delete from the middle.
        workflow = Workflow.create_and_init()
        with freeze_time("2020-02-02"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
        with freeze_time("1970-01-01"):
            # second Delta happened "before" the first!
            do(SetWorkflowTitle, workflow.id, new_value="bar")
        with freeze_time("2020-02-02"):
            delta3 = do(SetWorkflowTitle, workflow.id, new_value="baz")

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        # We delete up to the latest fresh one....
        self.assertEqual(workflow.deltas.first().id, delta3.id)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_keep_recent_undone_deltas(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
        with freeze_time("2020-02-02"):
            # Updates their last_applied_at
            undo(workflow.id)
            undo(workflow.id)
        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))
        self.assertEqual(workflow.deltas.count(), 2)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_stale_undone_deltas(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
            undo(workflow.id)
            undo(workflow.id)
        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))
        self.assertEqual(workflow.deltas.count(), 0)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_stale_undone_deltas_after_fresh(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            delta1 = do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
            undo(workflow.id)
        with freeze_time("2020-02-02"):
            undo(workflow.id)  # undo delta1 recently
        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))
        self.assertEqual(
            list(workflow.deltas.values_list("id", flat=True)), [delta1.id]
        )

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_fresh_undone_delta_after_stale(self):
        # In case clocks are out of sync or there's corrupt data
        #
        # We don't care whether we delete both or keep both; just that we never
        # delete from the middle.
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            delta1 = do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
            do(SetWorkflowTitle, workflow.id, new_value="baz")
        with freeze_time("2020-02-02"):
            undo(workflow.id)  # undone recently
        with freeze_time("1970-01-01"):
            undo(workflow.id)  # corrupt! undone long ago
        with freeze_time("2020-02-02"):
            undo(workflow.id)  # undone recently

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        # We delete up to the first stale one
        self.assertEqual(workflow.deltas.first().id, delta1.id)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_all_done_and_undone_deltas(self):
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            delta1 = do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(SetWorkflowTitle, workflow.id, new_value="bar")
            do(SetWorkflowTitle, workflow.id, new_value="baz")
            do(SetWorkflowTitle, workflow.id, new_value="moo")
            undo(workflow.id)
            undo(workflow.id)

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        self.assertEqual(workflow.deltas.count(), 0)

        be_paranoid_and_assert_commands_apply(workflow)

    def test_keep_done_and_undone_deltas_between_stale_ones(self):
        workflow = Workflow.create_and_init()
        # delta1 and delta4 are from long ago. delta2 and delta3 have been
        # used recently.
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            delta2 = do(SetWorkflowTitle, workflow.id, new_value="bar")
            delta3 = do(SetWorkflowTitle, workflow.id, new_value="baz")
            do(SetWorkflowTitle, workflow.id, new_value="moo")
            undo(workflow.id)
        with freeze_time("2020-02-02"):
            undo(workflow.id)
            undo(workflow.id)
            redo(workflow.id)

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        self.assertEqual(
            list(workflow.deltas.values_list("id", flat=True)), [delta2.id, delta3.id]
        )

        be_paranoid_and_assert_commands_apply(workflow)

    def test_delete_orphan_soft_deleted_steps(self):
        mod = create_module_zipfile("mod")
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="foo")
            do(
                AddStep,
                workflow.id,
                tab=workflow.tabs.first(),
                slug="step-2",
                module_id_name="mod",
                position=0,
                param_values={},
            )
            undo(workflow.id)
        self.assertEqual(workflow.tabs.first().steps.count(), 1)  # soft-deleted

        delete_workflow_stale_deltas(workflow.id, datetime.datetime(2020, 1, 1))

        self.assertEqual(workflow.tabs.first().steps.count(), 0)  # hard-deleted


class FindWorkflowsWithStaleDeltasTest(DbTestCase):
    def test_find_workflow_using_default_max_age(self):
        default_max_age = datetime.timedelta(days=UserLimits().max_delta_age_in_days)
        workflow = Workflow.create_and_init()
        with freeze_time("1970-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="1")
        with freeze_time("2021-02-04"):
            do(SetWorkflowTitle, workflow.id, new_value="2")

        now = datetime.datetime(2021, 2, 5)
        result = find_workflows_with_stale_deltas(now)

        self.assertEqual(result, [(workflow.id, now - default_max_age)])

    def test_find_workflow_using_plan_max_age(self):
        plan_max_age = datetime.timedelta(days=30)
        owner = create_user()
        price = create_price(product=create_product(max_delta_age_in_days=30))
        create_subscription(owner, price)
        workflow = Workflow.create_and_init(owner=owner)
        with freeze_time("2020-01-01"):
            do(SetWorkflowTitle, workflow.id, new_value="1")

        now = datetime.datetime(2020, 2, 2)
        result = find_workflows_with_stale_deltas(now)

        self.assertEqual(result, [(workflow.id, now - plan_max_age)])

    def test_find_workflow_pick_max_plan(self):
        plan_max_age = datetime.timedelta(days=30)
        owner = create_user()
        price1 = create_price(
            product=create_product(max_delta_age_in_days=1),
            stripe_price_id="price_plan1",
        )
        price2 = create_price(
            product=create_product(max_delta_age_in_days=30),
            stripe_price_id="price_plan2",
        )
        create_subscription(owner, price1, stripe_subscription_id="sub_1")
        create_subscription(owner, price2, stripe_subscription_id="sub_2")

        with freeze_time("2020-01-01"):
            workflow1 = Workflow.create_and_init(owner=owner)
            do(SetWorkflowTitle, workflow1.id, new_value="1")
        with freeze_time("2020-01-15"):
            workflow2 = Workflow.create_and_init(owner=owner)
            do(SetWorkflowTitle, workflow2.id, new_value="1")

        now = datetime.datetime(2020, 2, 2)
        result = find_workflows_with_stale_deltas(now)

        self.assertEqual(result, [(workflow1.id, now - plan_max_age)])

    def test_find_empty_list(self):
        now = datetime.datetime(2021, 2, 3)
        self.assertEqual(find_workflows_with_stale_deltas(now), [])
