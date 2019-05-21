export const UNHANDLED_ERROR = 'UNHANDLED_ERROR'

/**
 * Action indicating a bug in our code.
 *
 * This is a last-ditch error. It indicates an error in Workbench's code, and
 * Workbench developers should fix it.
 *
 * Don't attempt to "repair" the store when processing this action. It's too
 * late. Instead, fix your reducers so they never throw errors or return
 * rejected promises.
 */
export function fluxStandardErrorAction (error, sourceAction) {
  return {
    type: sourceAction.type,
    error: true,
    payload: error
  }
}

/**
 * Calls `dispatch(errorActionFactory(err, action))` instead of throwing `err`.
 *
 * Catches sync and async errors.
 *
 * Use this if all of the following apply:
 *
 * * You never rely on "_REJECTED" actions in redux-promise-middleware.
 * * You never rely on `dispatch()` throwing or returning a rejected Promise.
 *
 * To be absolutely clear: you must handle errors _elsewhere_. This middleware
 * is designed to _report bugs_, not handle exceptions.
 */
export default function errorMiddleware (errorActionFactory) {
  if (!errorActionFactory) errorActionFactory = fluxStandardErrorAction

  return ({ dispatch }) => next => action => {
    if (action.error === true && action.type.endsWith('_REJECTED')) {
      // Ignore react-promise-middleware REJECTED actions. This middleware
      // _replaces_ them. (react-promise-middleware will both dispatch a
      // `_REJECTED` action and throw the error; so don't worry, we'll catch
      // the error.
      return null
    }

    let done
    try {
      done = next(action)
    } catch (err) {
      // Synchronous error
      return dispatch(errorActionFactory(err, action))
    }
    if (done instanceof Promise) {
      // Asynchronous -- may be an error later
      done = done.catch(err => dispatch(errorActionFactory(err, action)))
    }

    return done
  }
}
