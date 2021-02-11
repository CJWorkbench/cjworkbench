import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import Column from '../Column'
import ColorPicker from './ColorPicker'
import { defaultColors, getColor } from './ChartColors'

export default class ChartSeriesSelect extends PureComponent {
  static propTypes = {
    index: PropTypes.number.isRequired,
    column: PropTypes.string, // null if not selected
    color: PropTypes.string, // null for auto-chosen based on idx
    name: PropTypes.string.isRequired, // <input name="...">
    fieldId: PropTypes.string.isRequired, // <input id="...">
    placeholder: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    availableColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if not loaded
    onChange: PropTypes.func.isRequired // func({ index, column, color }) => undefined
  }

  state = {
    color: null // when this.props.column is null, we can't call props.onChange()
  }

  handlePickColor = (color) => {
    if (this.props.column) {
      this.props.onChange({
        index: this.props.index,
        column: this.props.column,
        color: color
      })
    } else {
      this.setState({ color })
    }
  }

  handleSelectColumn = (column) => {
    const { index, color } = this.props
    const safeColor = color || this.state.color || getColor(index)

    this.setState({ color: null })

    this.props.onChange({
      index: index,
      column: column,
      color: safeColor
    })
  }

  render () {
    const { availableColumns, column, color, index, placeholder, isReadOnly, name, fieldId } = this.props
    const safeColor = color || this.state.color || getColor(index)

    return (
      <div className='chart-series-select'>
        <ColorPicker
          name={`${name}[color]`}
          fieldId={`${fieldId}_color`}
          value={safeColor}
          choices={defaultColors}
          onChange={this.handlePickColor}
        />
        <Column
          name={`${name}[column]`}
          fieldId={`${fieldId}_column`}
          value={column}
          placeholder={placeholder}
          isReadOnly={isReadOnly}
          inputColumns={availableColumns}
          onChange={this.handleSelectColumn}
        />
      </div>
    )
  }
}
