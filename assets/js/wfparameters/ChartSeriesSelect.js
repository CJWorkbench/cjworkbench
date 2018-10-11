import React from 'react'
import PropTypes from 'prop-types'
import ColumnParam from './ColumnParam'
import ColorPicker from '../ColorPicker'
import InputGroup from 'reactstrap/lib/InputGroup'
import InputGroupAddon from 'reactstrap/lib/InputGroupAddon'
import Input from 'reactstrap/lib/Input'
import { defaultColors, getColor } from './charts/ChartColors'

export default class ChartSeriesSelect extends React.PureComponent {
  static propTypes = {
    index: PropTypes.number.isRequired,
    column: PropTypes.string, // null if not selected
    color: PropTypes.string, // null for auto-chosen based on idx
    prompt: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    availableColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if not loaded
    onChange: PropTypes.func.isRequired, // func({ index, column, color }) => undefined
  }

  state = {
    color: null, // when this.props.column is null, we can't call props.onChange()
  }

  onPickColor = (color) => {
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

  onSelectColumn = (column) => {
    const { index, color } = this.props
    const safeColor = color || this.state.color || getColor(index)

    this.setState({ color: null })

    this.props.onChange({
      index: index,
      column: column,
      color: safeColor
    })
  }

  render() {
    const { availableColumns, column, color, index, prompt, isReadOnly } = this.props
    const safeColor = color || this.state.color || getColor(index)

    return (
      <InputGroup size='lg' className='chart-series-select wf-parameter'>
        <InputGroupAddon addonType='prepend'>
          <ColorPicker
            name='color'
            value={safeColor}
            choices={defaultColors}
            onChange={this.onPickColor}
          />
        </InputGroupAddon>
        <ColumnParam
          name='column'
          value={column}
          prompt={prompt}
          isReadOnly={isReadOnly}
          allColumns={availableColumns}
          onChange={this.onSelectColumn}
        />
      </InputGroup>
    )
  }
}
