import React from 'react'
import PropTypes from 'prop-types'

/**
 * Render an I18nMessage, as defined in cjwkernel.types.
 *
 * This renders as text in a React.Fragment
 */
export default function I18nMessage (props) {
  // TODO change the implementation. Right now, we assume all I18nMessages
  // have id "TODO_i18n". But what we _really_ want is for "TODO_i18n" to be
  // an actual translation key -- i.e., something in the .po files -- that
  // just returns the `text` argument. Once we've done that, make this use
  // real i18n.
  if (props.id === 'TODO_i18n') {
    return <>{props.arguments.text}</>
  } else {
    return <>TODO_i18n: translate {JSON.stringify(props)}</>
  }
}
I18nMessage.propTypes = {
  id: PropTypes.string.isRequired, // message key
  arguments: PropTypes.object.isRequired
}
