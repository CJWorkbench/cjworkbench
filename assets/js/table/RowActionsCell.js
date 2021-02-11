import { PureComponent } from 'react'
import PropTypes from 'prop-types'

// Custom Formatter component, to render row number in a different style
export default class RowActionsCell extends PureComponent {
  static propTypes = {
    rowIdx: PropTypes.number,
    value: PropTypes.bool,
    column: PropTypes.shape({
      key: PropTypes.string.isRequired,
      onCellChange: PropTypes.func.isRequired
    }),
    dependentValues: PropTypes.object
  }

  handleChange = ev => {
    this.props.column.onCellChange(
      this.props.rowIdx,
      this.props.column.key,
      this.props.dependentValues,
      ev
    )
  }

  render () {
    const text = String(this.props.rowIdx + 1) // no commas -- horizontal space is at a premium
    const checked = this.props.value === true
    const checkboxName = `row-selected-${this.props.rowIdx}`

    return (
      <label className='is-row-selected'>
        <input
          type='checkbox'
          name={checkboxName}
          checked={checked}
          onChange={this.handleChange}
        />
        <span className={`row-number row-number-${text.length}`}>{text}</span>
      </label>
    )
  }
}
