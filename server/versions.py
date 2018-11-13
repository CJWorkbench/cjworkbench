async def WorkflowUndo(workflow):
    """Run workflow.last_delta, backwards."""
    # TODO avoid race undoing the same delta twice (or make it a no-op)
    delta = workflow.last_delta

    # Undo, if not at the very beginning of undo chain
    if delta:
        # Make sure delta.backward() edits the passed `workflow` argument.
        delta.workflow = workflow
        await delta.backward()  # uses cooperative lock


async def WorkflowRedo(workflow):
    """Run workflow.last_delta.next_delta, forward."""
    # TODO avoid race undoing the same delta twice (or make it a no-op)
    if workflow.last_delta:
        delta = workflow.last_delta.next_delta
    else:
        # we are at very beginning of delta chain; find first delta
        delta = workflow.deltas.filter(prev_delta__isnull=True).first()

    # Redo, if not at very end of undo chain
    if delta:
        # Make sure delta.forward() edits the passed `workflow` argument.
        delta.workflow = workflow
        await delta.forward()
