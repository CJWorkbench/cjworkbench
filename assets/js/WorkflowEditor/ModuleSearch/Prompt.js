import React from 'react'
import PropTypes from 'prop-types'
import { I18n } from '@lingui/react'
import { Trans,t } from '@lingui/macro'

export default class Prompt extends React.PureComponent {
  static propTypes = {
    value: PropTypes.string.isRequired, // may be empty
    cancel: PropTypes.func.isRequired, // func() => undefined -- should close this prompt
    onChange: PropTypes.func.isRequired // func(value) => undefined
  }

  inputRef = React.createRef()

  componentDidMount () {
    // auto-focus
    this.inputRef.current.focus()
  }

  handleChange = (ev) => {
    this.props.onChange(ev.target.value)
  }

  handleKeyDown = (ev) => {
    if (ev.keyCode === 27) this.props.cancel() // Esc => cancel
  }

  handleSubmit = (ev) => {
    ev.preventDefault()
  }

  render () {
    const { value, cancel } = this.props

    return (
      <form className='module-search-field' onSubmit={this.handleSubmit} onReset={cancel}>
       <I18n>
        {({ i18n }) => (
        <input
          type='search'
          name='moduleQ'
          placeholder={i18n._(t('workflow.placeholder.search')`Search…`)}
          autoComplete='off'
          ref={this.inputRef}
          value={value}
          onChange={this.handleChange}
          onKeyDown={this.handleKeyDown}
        />
        )}
        </I18n>
         <I18n>
        {({ i18n }) => (
        <button type='reset' className='reset' title={i18n._(t('workflow.visibility.closesearch')`Close Search`)}><i className='icon-close' /></button>
        )}
        </I18n>
      </form>
    )
  }
}
