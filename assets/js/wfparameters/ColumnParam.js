// Pick a single column
import React from 'react'
import PropTypes from 'prop-types'

export default class ColumnParam extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    value: PropTypes.string, // or null
    prompt: PropTypes.string, // default 'Select'
    isReadOnly: PropTypes.bool.isRequired,
    allColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired // func(colnameOrNull) => undefined
  }

  onChange = (ev) => {
    this.props.onChange(ev.target.value || null)
  }

  render() {
    const { allColumns, prompt, value } = this.props

    let className = 'custom-select module-parameter dropdown-selector'

    const options = (allColumns || []).map(({ name }) => (
      <option key={name}>{name}</option>
    ))

    // Select prompt when no column is selected, _or_ when an invalid
    // column is selected. `value || ''` is the currently-selected value.
    //
    // When a column is selected, set the prompt to '' so it is _not_
    // selected.
    const valueIsSelectable = (allColumns || []).some(({ name }) => name === value)
    const promptValue = valueIsSelectable ? '' : (value || '')
    options.unshift(<option disabled className="prompt" key="prompt" value={promptValue}>{prompt || 'Select'}</option>)

    if (allColumns === null) {
      className += ' loading'
      options.push(<option disabled className="loading" key="loading" value="">Loading columns</option>)
    }

    return (
      <select
        className={className}
        value={value || ''}
        onChange={this.onChange}
        name={this.props.name}
        disabled={this.props.isReadOnly}
      >
        {options}
      </select>
    )
  }
}
