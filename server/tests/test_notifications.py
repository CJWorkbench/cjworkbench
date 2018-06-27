import unittest
from unittest.mock import patch
from pandas import DataFrame
from server.notifications import \
        OutputDelta, \
        find_output_deltas_to_notify_from_fetched_tables as find_output_deltas


class WfModuleList():
    def __init__(self):
        self.items = []

    def all(self):
        return self.items

    def extend(self, items):
        return self.items.extend(items)

    def __getitem__(self, key):
        return self.items[key]

    def __iter__(self):
        for item in self.items:
            yield item


class MockUser:
    def __init__(self, email):
        self.email = email


class MockWorkflow:
    def __init__(self):
        self.wf_modules = WfModuleList()
        self.name = 'A Workflow'
        self.owner = MockUser('owner@example.org')

    def get_absolute_url(self):
        return f'https://example.org/a-workflow'


class MockWfModule:
    def __init__(self, workflow, id, notifications):
        self.workflow = workflow
        self.id = id
        self.notifications = notifications

    def get_module_name(self):
        return f'Module {self.id}'


def build_workflow(param_lists):
    workflow = MockWorkflow()
    wf_modules = [MockWfModule(workflow, *params) for params in param_lists]
    workflow.wf_modules.extend(wf_modules)
    return workflow


class TestFindOutputDeltas(unittest.TestCase):
    @patch('server.dispatch.module_dispatch_render')
    def test_noop_when_no_notifications(self, mock_render):
        workflow = build_workflow([
            (1, False),
            (2, False),
        ])
        deltas = find_output_deltas(workflow.wf_modules[0],
                                    DataFrame({'a': ['b']}),
                                    DataFrame({'b': ['c']}))
        self.assertListEqual(deltas, [])
        mock_render.assert_not_called()

    @patch('server.dispatch.module_dispatch_render')
    def test_notify_when_child_outputs_differ(self, mock_render):
        workflow = build_workflow([
            (1, False),
            (2, True),
        ])

        def render(wf_module, table):
            if table.equals(DataFrame({'a': ['b']})):
                return DataFrame({'a': ['1']})
            elif table.equals(DataFrame({'b': ['c']})):
                return DataFrame({'a': ['2']})
            else:
                raise Exception("???")
        mock_render.side_effect = render

        deltas = find_output_deltas(workflow.wf_modules[0],
                                    DataFrame({'a': ['b']}),
                                    DataFrame({'b': ['c']}))
        self.assertEqual(len(deltas), 1)
        self.assertEqual(
            deltas[0],
            OutputDelta(workflow.wf_modules[1], DataFrame({'a': ['1']}),
                        DataFrame({'a': ['2']}))
        )

    @patch('server.dispatch.module_dispatch_render')
    def test_noop_when_parent_outputs_equal(self, mock_render):
        # Output of module 1 is equal, so we never run module 2 and thus never
        # notify.
        workflow = build_workflow([
            (1, False),
            (2, True),
        ])

        def render(wf_module, table):
            if table.equals(DataFrame({'a': ['b']})):
                return DataFrame({'a': ['c']})
            elif table.equals(DataFrame({'b': ['c']})):
                return DataFrame({'a': ['c']})
            else:
                raise Exception("???")
        mock_render.side_effect = render

        deltas = find_output_deltas(workflow.wf_modules[0],
                                    DataFrame({'a': ['b']}),
                                    DataFrame({'b': ['c']}))
        self.assertListEqual(deltas, [])

    def test_notify_when_fetch_output_differs(self):
        workflow = build_workflow([
            (1, True),
        ])
        deltas = find_output_deltas(workflow.wf_modules[0],
                                    DataFrame({'a': ['b']}),
                                    DataFrame({'b': ['c']}))
        self.assertListEqual(deltas, [
            OutputDelta(workflow.wf_modules[0],
                        DataFrame({'a': ['b']}), DataFrame({'b': ['c']})),
        ])

    def test_notify_when_fetch_output_becomes_non_none(self):
        workflow = build_workflow([
            (1, True),
        ])
        deltas = find_output_deltas(workflow.wf_modules[0], None,
                                    DataFrame({'b': ['c']}))
        self.assertListEqual(deltas, [
            OutputDelta(workflow.wf_modules[0], None,
                        DataFrame({'b': ['c']})),
        ])

    @patch('server.dispatch.module_dispatch_render')
    def test_notify_child_when_fetch_output_becomes_non_none(self,
                                                             mock_render):
        workflow = build_workflow([
            (1, False),
            (2, True),
        ])

        def render(wf_module, table):
            if table is None:
                return None
            if table.equals(DataFrame({'a': ['b']})):
                return DataFrame({'a': ['1']})
            else:
                raise Exception("???")
        mock_render.side_effect = render

        deltas = find_output_deltas(workflow.wf_modules[0], None,
                                    DataFrame({'a': ['b']}))
        self.assertListEqual(deltas, [
            OutputDelta(workflow.wf_modules[1], None,
                        DataFrame({'a': ['1']})),
        ])
