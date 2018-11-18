import React from 'react'
import PropTypes from 'prop-types'
import { withFetchedData } from './Refine'
import { List } from 'react-virtualized'

const NumberFormatter = new Intl.NumberFormat()

// TODO: fix CSS for checkmark icon change when selected

class ValueList extends React.PureComponent {
  static propTypes = {
    list: PropTypes.array.isRequired
  }

  // https://github.com/bvaughn/react-virtualized/blob/master/docs/List.md
  renderRow = ({ key, index, isScrolling, isVisible, style }) => {
    const item = (
      <div
        key={key}
        style={style}
      >
        {this.props.list[index]}
        </div>
    )
    return item
  }
  render() {
    // TODO: set dynamic height
    // https://bvaughn.github.io/react-virtualized/#/components/List
    return (
      <List
        className={'react-list'}
        height={300}
        width={246}
        rowCount={this.props.list.length}
        rowHeight={27.78}
        rowRenderer={this.renderRow}
      />
    )
  }
}

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
    const className = 'visible original'

    return (
      <li className={className}>
        <div className='summary'>
          <input
            name={`include[${name}]`}
            type='checkbox'
            title='Include these rows'
            checked={this.props.isSelected}
            onChange={this.onChangeIsSelected}
          />
          <span className='count-and-reset'>
            <span className='count'>{NumberFormatter.format(count)}</span>
          </span>
          <div className='growing'>
            <span>{name}</span>
          </div>
        </div>
      </li>
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
          name='refine-select-all'
          title='Select All'
          onClick={fillSelectedValues}
          className='mc-select-all'
        >
          All
        </button>
        <button
          disabled={isReadOnly}
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
 * Edit a column's values to become "groups", then blacklist unwanted groups.
 *
 * The "value" here is a JSON-encoded String. Its format:
 *
 *     {
 *         "renames": {
 *             "foo": "bar", // "edit every 'foo' value to become 'bar'"
 *             //      ^^^ from the user's point of view, "bar" is the "group"
 *             ...
 *         },
 *         "blacklist": [
 *             "bar", // "Filter out every row where the post-rename value is "bar"
 *         ]
 *     }
 *
 * `valueCounts` describes the input: `{ "foo": 1, "bar": 3, ... }`
 */
export class ValueSelect extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
    loading: PropTypes.bool.isRequired, // true iff loading from server
    value: PropTypes.string.isRequired, // JSON-encoded ['value1', 'value2']}
    onChange: PropTypes.func.isRequired // fn(['newvalue1', 'newvalue2']}) => undefined
  }

  // selectedValues = { value1: null } for fast lookup when removing or adding values
  state = {
    searchInput: '',
    selectedValues: this.mapPropValues()
  }

  /**
   * Return "groups": outputs, and their input
   *
   * Each "group" has the following properties:
   *
   * * `name`: a string describing the desired output
   * * `values`: strings describing the desired input; empty if no edits
   * * `isBlacklisted`: true if we are omitting this group from output
   */

  // faster way of determining if there are more than 1 values
  // without copying entire list into memory
  get canSearch () {
    let count = 0
    for (const value in this.props.valueCounts) {
      count++
      if (count > 1) return true
    }
    return false
  }

  // takes JSON encoded array and maps to {value1: null, value2: null}
  mapPropValues () {
    if (this.props.value) {
      const selectedList = JSON.parse(this.props.value)
      let selectedValues = {}
      for (const value in selectedList) {
        selectedValues[selectedList[value]] = null
      }
      return selectedValues
    }
    return {}
  }

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

  // convert blacklist = {value1: null, value2: null} to ['value1', 'value2']
  onChange = () => {
    const selectedList = this.toJsonString()
    this.props.onChange(selectedList)
  }

  toJsonString = () => {
    let selectedValues = Object.assign({}, this.state.selectedValues)
    const json = JSON.stringify(Object.keys(selectedValues))
    return json
  }

  /**
   * Find { name: null } Object enumerating matching group names
   */
  valueMatching = (searchInput) => {
    let valueCounts = Object.assign({}, this.props.valueCounts)

    const searchKey = searchInput.toLowerCase()
    for (const value in valueCounts) {
      if (!value.toLowerCase().includes(searchKey)) {
        delete valueCounts[value]
      }
    }
    return valueCounts
  }

  onChangeIsSelected = (value, isSelected) => {
    let selectedValues = Object.assign({}, this.state.selectedValues)
    if (isSelected) {
      selectedValues[value] = null
    } else {
      delete selectedValues[value]
    }
    this.setState({ selectedValues: selectedValues }, () => { this.onChange() })
  }

  clearSelectedValues = () => {
    this.setState({ selectedValues: {} }, () => { this.onChange() })
  }

  fillSelectedValues = () => {
    const valueCounts = this.props.valueCounts || {}
    let selectedValues = {}
    for (const value in valueCounts) {
      selectedValues[value] = null
    }
    this.setState({ selectedValues: selectedValues }, () => { this.onChange() })
  }

  render () {
    const { searchInput, selectedValues } = this.state
    const valueCounts = this.props.valueCounts ? this.props.valueCounts : {}
    const canSearch = Object.keys(valueCounts).length > 1
    const isSearching = (searchInput !== '')
    const matchingValues = isSearching ? this.valueMatching(searchInput) : valueCounts

    // render only matching values
    const valueComponents = Object.keys(matchingValues).map(value => (
      <ValueItem
        key={value}
        name={value}
        count={matchingValues[value]}
        onChangeIsSelected={this.onChangeIsSelected}
        isSelected={(value in selectedValues)}
      />
    ))

    const valueList = valueComponents.length > 0 ? (
      <ValueList list={valueComponents} />
    ) : []

    return (
      <div className='refine-parameter'>
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
        <ul className='refine-groups'>
          {valueList}
        </ul>
        { (isSearching && canSearch && valueComponents.length === 0) ? (
          <div className='wf-module-error-msg'>No values</div>
        ) : null}
      </div>
    )
  }
}

//TODO: Change
export default withFetchedData(ValueSelect, 'valueCounts')
