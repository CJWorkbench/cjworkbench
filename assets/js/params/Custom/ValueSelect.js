import React from 'react'
import PropTypes from 'prop-types'
import { withFetchedData } from './FetchedData'
import { withJsonStringValues } from '../util'
import { List } from 'react-virtualized'
import memoize from 'memoize-one'

const NumberFormatter = new Intl.NumberFormat()

// TODO: Change class names to move away from Refine and update CSS

/**
 * Displays a list item of check box, name (of value), and count
 */
class ValueItem extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string, // new value -- may be empty string
    count: PropTypes.number.isRequired, // number, strictly greater than 0
    isSelected: PropTypes.bool.isRequired,
    onChangeIsSelected: PropTypes.func.isRequired // func(name, isSelected) => undefined
  }

  onChangeIsSelected = (ev) => {
    this.props.onChangeIsSelected(this.props.name, ev.target.checked)
  }

  render () {
    const { count, name } = this.props

    return (
      <div className="value">
        <label>
          <input
            name={`include[${name}]`}
            type='checkbox'
            title='Include these rows'
            checked={this.props.isSelected}
            onChange={this.onChangeIsSelected}
          />
          <div className='text'>{name}</div>
        </label>
        <div className='count'>{NumberFormatter.format(count)}</div>
      </div>
    )
  }
}

export class AllNoneButtons extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    clearSelectedValues: PropTypes.func.isRequired, // func() => undefined
    fillSelectedValues: PropTypes.func.isRequired // func() => undefined
  }

  render() {
    const { isReadOnly, clearSelectedValues, fillSelectedValues } = this.props

    return (
      <div className="all-none-buttons">
        <button
          disabled={isReadOnly}
          type='button'
          name='refine-select-all'
          title='Select All'
          onClick={fillSelectedValues}
          className='mc-select-all'
        >
          All
        </button>
        <button
          disabled={isReadOnly}
          type='button'
          name='refine-select-none'
          title='Select None'
          onClick={clearSelectedValues}
          className='mc-select-none'
        >
          None
        </button>
      </div>
    )
  }
}

/**
 * The "value" here is an Array: `["value1", "value2"]`
 *
 * `valueCounts` describes the input: `{ "foo": 1, "bar": 3, ... }`
 */
export class ValueSelect extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
    loading: PropTypes.bool.isRequired, // true iff loading from server
    value: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // `["value1", "value2"]}`
    onChange: PropTypes.func.isRequired // fn(JSON.stringify(['value1', 'value2', 'value5']))
  }
  /** searchInput is the textbox string input from the user **/
  state = {
    searchInput: ''
  }
  /** references virtualized valueList to force re-render in 'onChange()' when an item is checked/unchecked **/
  valueListRef = React.createRef()
  matchingValuesRef = React.createRef()

  /**
   * Return "selectedValues" in object form for fast lookup:
   *
   * {value1: null, value2: null, value5: null}
   */
  get selectedValues () {
    if (this.props.value) return this.selectedValuesObject(this.props.value)
    return {}
  }

  get sortedValues () {
    if (this.props.valueCounts) return this.getSortedValues(this.props.valueCounts)
    return []
  }

  /** takes JSON encoded `[value1, value2]` and maps to {value1: null, value2: null} **/
  selectedValuesObject = memoize(values => {
    const selectedValues = {}
    for (const index in values) {
      selectedValues[values[index]] = null
    }
    return selectedValues
  })

  getSortedValues = memoize(valueCounts => {
    return Object.keys(valueCounts).sort((a, b) => a.localeCompare(b))
  })

  onReset = () => {
    this.setState({ searchInput: '' })
  }

  onKeyDown = (ev) => {
    if (ev.keyCode === 27) this.onReset() // Esc => reset
  }

  onInputChange = (ev) => {
    const searchInput = ev.target.value
    this.setState({ searchInput })
  }

  /** convert {value1: null, value2: null} to JSON encoded ['value1', 'value2'] to return **/
  onChange = (selectedValues) => {
    this.props.onChange(Object.keys(selectedValues))
  }

  valueMatching = (searchInput) => {
    const searchKey = searchInput.toLowerCase()
    return this.sortedValues.filter(v => v.toLowerCase().includes(searchKey))
  }

  /** Add/Remove from selectedValues and return when checked/unchecked **/
  onChangeIsSelected = (value, isSelected) => {
    let selectedValues = this.selectedValues
    if (isSelected) {
      selectedValues[value] = null
    } else {
      delete selectedValues[value] // FIXME [adamhooper, 2018-11-22] this modifies an immutable variable
    }
    this.onChange(selectedValues)
  }

  clearSelectedValues = () => {
    this.onChange({})
  }

  fillSelectedValues = () => {
    const valueCounts = this.props.valueCounts || {}
    let selectedValues = {}
    for (const value in valueCounts) {
      selectedValues[value] = null
    }
    this.onChange(selectedValues)
  }

  /** Used by react-virtualized to only render rows in module viewport **/
  renderRow = ({ key, index, isScrolling, isVisible, style }) => {
    const value = this.matchingValuesRef[index]
    const item = (
      <div key={key} style={style}>
        <ValueItem
          key={value}
          name={value}
          count={this.props.valueCounts[value]}
          onChangeIsSelected={this.onChangeIsSelected}
          isSelected={(value in this.selectedValues)}
        />
      </div>
    )
    return item
  }
  /** Force react-virtualized render when props change **/
  componentDidUpdate (prevProps) {
    if (this.props.valueCounts !== null) {
      if ((this.props.valueCounts !== prevProps.valueCounts || this.props.value !== prevProps.value) &&
        (Object.keys(this.props.valueCounts).length > 0)) {
        this.valueListRef.forceUpdateGrid()
      }
    }
  }
  render () {
    const { searchInput } = this.state
    const { valueCounts } = this.props
    const canSearch = this.sortedValues.length > 1
    const isSearching = (searchInput !== '')
    const matchingValues = isSearching ? this.valueMatching(searchInput) : this.sortedValues

    this.matchingValuesRef = matchingValues

    /** TODO: Hardcoded row heights and width for now for simplicity, in the future we'll need to implement:
     *  https://github.com/bvaughn/react-virtualized/blob/master/docs/CellMeasurer.md
     *
     *  Viewport capped at 10 items, if less than 10 height is adjusted accordingly
     */
    const rowHeight = 27.78
    const valueList = matchingValues.length > 0 ? (
      <List
        className={'react-list'}
        height={
          rowHeight * matchingValues.length > 300 ? 300 : rowHeight * matchingValues.length
        }
        width={246}
        rowCount={matchingValues.length}
        rowHeight={rowHeight}
        rowRenderer={this.renderRow}
        ref={(ref) => { this.valueListRef = ref }}
      />) : null

    return (
      <div className='value-parameter'>
        { !canSearch ? null : (
          <React.Fragment>
            <form className="in-module--search" onSubmit={this.onSubmit} onReset={this.onReset}>
              <input
                type='search'
                placeholder='Search values...'
                autoComplete='off'
                value={searchInput}
                onChange={this.onInputChange}
                onKeyDown={this.onKeyDown}
              />
              <button type="reset" className="close" title="Clear Search"><i className="icon-close"></i></button>
            </form>
            <AllNoneButtons
              isReadOnly={isSearching}
              clearSelectedValues={this.clearSelectedValues}
              fillSelectedValues={this.fillSelectedValues}
            />
          </React.Fragment>
        )}
        <div className='value-list'>
          {valueList}
        </div>
        { (isSearching && canSearch && matchingValues.length === 0) ? (
          <div className='wf-module-error-msg'>No values</div>
        ) : null}
      </div>
    )
  }
}

export default withFetchedData(
  withJsonStringValues(ValueSelect, []),
  'valueCounts',
  ({ api, inputWfModuleId, selectedColumn }) => api.valueCounts(inputWfModuleId, selectedColumn),
  ({ inputDeltaId, selectedColumn }) => `${inputDeltaId}-${selectedColumn}`
)
