import React from 'react'
import PropTypes from 'prop-types'
import InputGroup from 'reactstrap/lib/InputGroup'
import InputGroupAddon from 'reactstrap/lib/InputGroupAddon'
import Input from 'reactstrap/lib/Input'
import Button from 'reactstrap/lib/Button'
import BlockPicker from 'react-color/lib/Block'
import { defaultColors, getColor } from './charts/ChartColors'

export default class ChartSeriesSelect extends React.PureComponent {
  static propTypes = {
    index: PropTypes.number.isRequired,
    column: PropTypes.string, // null if not selected
    color: PropTypes.string, // null for auto-chosen based on idx
    availableColumns: PropTypes.arrayOf(PropTypes.string).isRequired,
    onChange: PropTypes.func.isRequired, // func(index, column) => undefined
  }

  state = {
    colorPickerOpen: false,
    color: null, // when this.props.column is null, we can't call props.onChange()
  }

  openColorPicker = () => {
    this.setState({ colorPickerOpen: true })
  }

  closeColorPicker = () => {
    this.setState({ colorPickerOpen: false })
  }

  onPickColor = (color) => {
    this.setState({ colorPickerOpen: false })
    if (this.props.column) {
      this.props.onChange({
        index: this.props.index,
        column: this.props.column,
        color: color.hex
      })
    } else {
      this.setState({ color: color.hex })
    }
  }

  onSelectColumn = (ev) => {
    const column = ev.target.value
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
    const { availableColumns, column, color, index } = this.props
    const safeColor = color || getColor(index)

    return (
      <React.Fragment>
        <InputGroup size='lg' className='chart-series-select'>
          <InputGroupAddon addonType='prepend'>
            <Button title='Pick color' onClick={this.openColorPicker} className='color-picker button color' style={{background: safeColor}}>
              <i className="color-picker"/>
            </Button>
          </InputGroupAddon>
          <select className='form-control' name='column' value={column || ''} onChange={this.onSelectColumn}>
            {availableColumns.map(availableColumn => {
              return (
                <option key={availableColumn}>{availableColumn}</option>
              )
            })}
          </select>
        </InputGroup>
        { this.state.colorPickerOpen ? <div className="color-picker pop-over">
          <div className="color-picker cover" onClick={this.closeColorPicker} />
            <BlockPicker
              color={safeColor}
              colors={defaultColors}
              onChangeComplete={this.onPickColor}
              triangle="hide"
            />
          </div>
        : null }
      </React.Fragment>
    )
  }
}
