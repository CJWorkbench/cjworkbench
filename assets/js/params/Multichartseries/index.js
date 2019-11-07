import React from 'react'
import PropTypes from 'prop-types'
import ChartSeriesSelect from './ChartSeriesSelect'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export class Multichartseries extends React.PureComponent {
  static propTypes = {
    value: PropTypes.arrayOf(PropTypes.shape({
      column: PropTypes.string.isRequired,
      color: PropTypes.string.isRequired
    })).isRequired,
    placeholder: PropTypes.string.isRequired,
    fieldId: PropTypes.string.isRequired,
    inputColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if not loaded
    onChange: PropTypes.func.isRequired, // func([{column, color}, ...]) => undefined
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired
  }

  state = {
    isAddingPlaceholder: this.props.value.length === 0
  }

  handleChange = ({ index, column, color }) => {
    const value = this.props.value.slice() // shallow copy

    if (index === value.length) {
      // We just overwrote the placeholder
      this.setState({ isAddingPlaceholder: false })
    }

    value[index] = { column, color }
    this.props.onChange(value)
  }

  handleClickAddPlaceholder = () => {
    this.setState({ isAddingPlaceholder: true })
  }

  handleClickRemoveLast = () => {
    if (this.state.isAddingPlaceholder) {
      this.setState({ isAddingPlaceholder: false })
    } else {
      const value = this.props.value.slice() // shallow copy
      value.pop()
      this.props.onChange(value)
    }
  }

  renderButtons () {
    const { isAddingPlaceholder } = this.state
    const { inputColumns, value, isReadOnly, i18n } = this.props

    const showAddButton = !isReadOnly && !isAddingPlaceholder && value.length < (inputColumns || []).length
    const showRemoveButton = !isReadOnly && (value.length > 1 || (value.length === 1 && isAddingPlaceholder))

    if (!showAddButton && !showRemoveButton) {
      return null
    } else {
      const addButton = !showAddButton ? null : (
        <button type='button' title={i18n._(t('js.params.Multichartseries.addColumn.hoverText')`add another column`)} onClick={this.handleClickAddPlaceholder}>
          <i className='icon-addc' />
        </button>
      )

      const removeButton = !showRemoveButton ? null : (
        <button type='button' title={i18n._(t('js.params.Multichartseries.removeLastColumn.hoverText')`remove last column`)} onClick={this.handleClickRemoveLast}>
          <i className='icon-removec' />
        </button>
      )

      return (
        <div className='buttons'>
          {removeButton}
          {addButton}
        </div>
      )
    }
  }

  render () {
    const { inputColumns, value, placeholder, isReadOnly, name, fieldId } = this.props

    if (inputColumns === null) {
      return <p className='loading'><Trans id='js.params.Multichartseries.loading'>Loading…</Trans></p>
    }

    const pickedColumns = value.map(x => x.column)
    const pickers = value.map(({ column, color }, index) => {
      // Don't allow picking a column that's already picked
      const availableColumns = (inputColumns || [])
        .filter(({ name }) => pickedColumns.indexOf(name) === -1 || name === column)

      return (
        <ChartSeriesSelect
          key={index}
          index={index}
          name={`${name}[${index}]`}
          fieldId={`${fieldId}_${index}`}
          placeholder={placeholder}
          isReadOnly={isReadOnly}
          column={column}
          color={color}
          availableColumns={availableColumns}
          onChange={this.handleChange}
        />
      )
    })

    if (this.state.isAddingPlaceholder) {
      const availableColumns = (inputColumns || [])
        .filter(({ name }) => pickedColumns.indexOf(name) === -1)

      pickers.push(
        <ChartSeriesSelect
          key={value.length}
          index={value.length}
          name={`${name}[${value.length}]`}
          fieldId={`${fieldId}_${value.length}`}
          placeholder={placeholder}
          isReadOnly={isReadOnly}
          column={null}
          color={null}
          availableColumns={availableColumns}
          onChange={this.handleChange}
        />
      )
    }

    const buttons = this.renderButtons()

    return (
      <div className='chart-series-multi-select'>
        {pickers}
        {buttons}
      </div>
    )
  }
}

export default withI18n()(Multichartseries)
