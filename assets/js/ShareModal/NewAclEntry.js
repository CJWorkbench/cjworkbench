import React from 'react'
import PropTypes from 'prop-types'
import { Trans } from '@lingui/macro'

export default class NewAclEntry extends React.PureComponent {
  static propTypes = {
    ownerEmail: PropTypes.string.isRequired,
    updateAclEntry: PropTypes.func.isRequired // func(email, canEdit) => undefined
  }

  emailRef = React.createRef()

  // No state: we're using uncontrolled components, because the logic is so
  // simple. If you're adding new features, consider switching to controlled
  // components.
  // https://reactjs.org/docs/uncontrolled-components.html

  handleSubmit = (ev) => {
    // onSubmit() is only called after <form> passes validation -- meaning
    // email address is valid
    const email = this.emailRef.current.value

    if (email !== this.props.ownerEmail) {
      this.props.updateAclEntry(email, false)
    }

    // Reset the input, so the user can enter another email. (It should retain
    // focus.)
    this.emailRef.current.value = ''

    ev.preventDefault() // don't let the browser change URL etc.
    ev.stopPropagation()
  }

  render () {
    // Uncontrolled form -- we'll use HTML5 validation, with its :valid and
    // :invalid classes.
    return (
      <form className='new-acl-entry input-group' onSubmit={this.handleSubmit}>
        <input className='form-control' type='email' name='email' ref={this.emailRef} required placeholder='user@example.org' />
        <div className='input-group-append'>
          <button type='submit' className='btn btn-outline-secondary'>
            <Trans id='js.ShareModal.NewAclEntry.grantAccess'>Grant access</Trans>
          </button>
        </div>
      </form>
    )
  }
}
