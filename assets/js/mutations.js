import reportMutations from './WorkflowEditor/Report/mutations'

/**
 * Changes to the Workflow ... client-side.
 *
 * The _server_ is responsible for changing the state of a Workflow. But the
 * client needs to predict these changes. So we store `state.pendingMutations`
 * as a list of operations that the server has not yet performed.
 *
 * Mutations aren't Redux "Actions". Actions are dispatched alongside the
 * state. Mutations are _stored in the state_ to predict the future state.
 * (After Alice adds a Step, she wants to edit it even before the server
 * responds.) Mutations are optimistic; they may fail to apply, and that's okay.
 *
 * Mutations aren't "Deltas" (server-sent updates). Deltas are movements from
 * State 1 to State 2. Mutations are _pending_ changes. We don't store deltas
 * in the state because the delta depends on when the action happens. For
 * instance, in a Workflow with steps A, B and C:
 *
 * 1. Alice sends "Delete step A" (but server doesn't see it yet). Mutation is,
 *    "Delete step A." (Delta would be: "set Steps to B, C.")
 * 2. Bob sends "Delete step B" and the server applies it. It sends a delta to
 *    Alice saying, "set Steps to A, C."
 * 3. Server processes Alice's action. It sends a delta to Alice saying,
 *    "set Steps to C."
 *
 * If Alice's state stored a pending Delta ("set Steps to B, C"), she'd see a
 * crash after step 2 because step B will be deleted. Alice stores a _mutation_
 * instead ("Delete step A") because that's safe even when Bob edits.
 *
 * Mutations are closely related to API calls. Each API call can involve a
 * mutation; and if the server reports an error invoking that API call, the
 * mutation should be disabled. (If the server does _not_ report an error, the
 * mutation is in a state of limbo -- there may be a delta the client has yet to
 * receive that will finalize the mutation.)
 *
 * As for ordering: if the client performs one API call at a time and waits
 * for the server to respond between each API call, then the server guarantees
 * updates will apply in order. Since mutations result from API calls, the
 * client can assume mutations will apply in order, too -- the ones that apply
 * successfully, anyway.
 */
export default {
  ...reportMutations
}
