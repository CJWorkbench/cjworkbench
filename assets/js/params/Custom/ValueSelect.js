import React from 'react'
import PropTypes from 'prop-types'
import { withFetchedData } from './FetchedData'
import { FixedSizeList } from 'react-window'
import memoize from 'memoize-one'

const NumberFormatter = new Intl.NumberFormat()

// TODO: Change class names to move away from Refine and update CSS

/**
 * Displays a list item of check box, name (of item), and count
 */
class ValueItem extends React.PureComponent {
  static propTypes = {
    item: PropTypes.string, // new value -- may be empty string
    count: PropTypes.number.isRequired, // number, strictly greater than 0
    isSelected: PropTypes.bool.isRequired,
    onChangeIsSelected: PropTypes.func.isRequired // func(item, isSelected) => undefined
  }

  onChangeIsSelected = (ev) => {
    this.props.onChangeIsSelected(this.props.item, ev.target.checked)
  }

  render () {
    const { count, item } = this.props

    return (
      <div className="value">
        <label>
          <input
            name={`include[${item}]`}
            type='checkbox'
            title='Include these rows'
            checked={this.props.isSelected}
            onChange={this.onChangeIsSelected}
          />
          <div className='text'>{item}</div>
        </label>
        <div className='count'>{NumberFormatter.format(count)}</div>
      </div>
    )
  }
}

class ListRow extends React.PureComponent {
  // extend PureComponent so we get a shouldComponentUpdate() function

  // PropTypes all supplied by FixedSizeList
  static propTypes = {
    data: PropTypes.shape({
      valueCounts: PropTypes.object.isRequired, // { 'item': <Number> count, ... }
      items: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired,
      selection: PropTypes.instanceOf(Set).isRequired,
      onChangeIsSelected: PropTypes.func.isRequired, // func(item, isSelected) => undefined
    }),
    style: PropTypes.object.isRequired,
    index: PropTypes.number.isRequired
  }

  render () {
    const { data: { valueCounts, items, selection, onChangeIsSelected }, style, index } = this.props
    const item = items[index]
    const count = valueCounts[item]
    const isSelected = selection.has(item)

    return (
      <div style={style}>
        <ValueItem
          item={item}
          count={count}
          isSelected={isSelected}
          onChangeIsSelected={onChangeIsSelected}
        />
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

const ItemCollator = new Intl.Collator() // in the user's locale

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
    onChange: PropTypes.func.isRequired // fn(['value1', 'value2', 'value5'])
  }

  state = {
    // searchInput is the textbox string input from the user
    searchInput: ''
  }

  /**
   * Return "selectedValues", a Set[String].
   *
   * this.selectedValues.has('A') => true|false
   */
  get selectedValues () {
    return this._buildSelectedValues(this.props.value)
  }

  get sortedValues () {
    return this._buildSortedValues(this.props.valueCounts)
  }

  get matchingSortedValues () {
    return this._buildMatchingSortedValues(this.sortedValues, this.state.searchInput)
  }

  get listRowData () {
    return this._buildListRowData(this.props.valueCounts, this.selectedValues, this.matchingSortedValues)
  }

  _buildSelectedValues = memoize(values => new Set(values))

  _buildSortedValues = memoize(valueCounts => {
    if (!valueCounts) return []
    return [ ...Object.keys(valueCounts).sort(ItemCollator.compare) ]
  })

  _buildMatchingSortedValues = memoize((sortedValues, searchInput) => {
    if (searchInput) {
      const searchKey = searchInput.toLowerCase()
      return sortedValues.filter(v => v.toLowerCase().includes(searchKey))
    } else {
      return sortedValues
    }
  })

  _buildListRowData = memoize((valueCounts, selectedValues, matchingSortedValues) => ({
    valueCounts: valueCounts || {},
    selection: selectedValues,
    items: matchingSortedValues,
    onChangeIsSelected: this.onChangeIsSelected
  }))

  onResetSearch = () => {
    this.setState({ searchInput: '' })
  }

  onKeyDown = (ev) => {
    if (ev.keyCode === 27) this.onResetSearch() // Esc => reset
  }

  onInputChange = (ev) => {
    const searchInput = ev.target.value
    this.setState({ searchInput })
  }

  /** Add/Remove from selectedValues and return when checked/unchecked **/
  onChangeIsSelected = (item, isSelected) => {
    const { value, onChange } = this.props
    if (isSelected) {
      if (!value.includes(item)) {
        onChange([ ...value, item ])
      } else {
        // no-op: adding an already-present element
      }
    } else {
      const index = value.indexOf(item)
      if (index !== -1) {
        onChange([
          ...(value.slice(0, index)),
          ...(value.slice(index + 1))
        ])
      } else {
        // no-op: deleting an already-missing element
      }
    }
  }

  clearSelectedValues = () => {
    this.props.onChange([])
  }

  fillSelectedValues = () => {
    const { onChange, valueCounts } = this.props
    if (!valueCounts) return // surely the user didn't mean to clear selection?
    onChange([ ...Object.keys(valueCounts) ])
  }

  render () {
    const { searchInput } = this.state
    const canSearch = this.sortedValues.length > 1
    const isSearching = (searchInput !== '')
    const matchingSortedValues = this.matchingSortedValues

    /** TODO: Hardcoded row heights and width for now for simplicity, in the future we'll need to implement:
     *  https://github.com/bvaughn/react-virtualized/blob/master/docs/CellMeasurer.md
     *
     *  Viewport capped at 10 items, if less than 10 height is adjusted accordingly
     */
    const rowHeight = 27.78

    return (
      <>
        { !canSearch ? null : (
          <>
            <div className="in-module--search" onSubmit={this.onSubmit} onReset={this.onReset}>
              <input
                type='search'
                placeholder='Search values...'
                autoComplete='off'
                value={searchInput}
                onChange={this.onInputChange}
                onKeyDown={this.onKeyDown}
              />
              <button
                type="button"
                onClick={this.onResetSearch}
                className="close"
                title="Clear Search"
              ><i className="icon-close" /></button>
            </div>
            <AllNoneButtons
              isReadOnly={isSearching}
              clearSelectedValues={this.clearSelectedValues}
              fillSelectedValues={this.fillSelectedValues}
            />
          </>
        )}
        <div className='value-list'>
          { matchingSortedValues.length > 0 ? (
            <FixedSizeList
              className='react-list'
              height={
                rowHeight * matchingSortedValues.length > 300 ? 300 : rowHeight * matchingSortedValues.length
              }
              itemCount={matchingSortedValues.length}
              itemSize={rowHeight}
              itemData={this.listRowData}
            >
              {ListRow}
            </FixedSizeList>
          ) : null}
        </div>
        { (isSearching && canSearch && matchingSortedValues.length === 0) ? (
          <div className='wf-module-error-msg'>No values</div>
        ) : null}
      </>
    )
  }
}

export default withFetchedData(
  ValueSelect,
  'valueCounts',
  ({ api, inputWfModuleId, selectedColumn }) => api.valueCounts(inputWfModuleId, selectedColumn),
  ({ inputDeltaId, selectedColumn }) => `${inputDeltaId}-${selectedColumn}`
)
