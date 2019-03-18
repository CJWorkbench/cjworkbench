import React from 'react'
import PropTypes from 'prop-types'
import RefineModal from './RefineModal'
import { withFetchedData } from '../FetchedData'

const NumberFormatter = new Intl.NumberFormat()
const ValueCollator = new Intl.Collator() // in the user's locale

export class RefineSpec {
  constructor (renames) {
    this.renames = renames
  }

  toJsonObject () {
    return {
      renames: this.renames
    }
  }

  /**
   * Return "groups": outputs, and their input
   *
   * Each "group" has the following properties:
   *
   * * `name`: a string describing the desired output
   * * `values`: strings describing the desired input; empty if no edits
   */
  buildGroupsForValueCounts (valueCounts) {
    const { renames } = this

    const groupNames = []
    const groupsByName = {}
    const allValues = Object.keys(valueCounts || {})
    for (const value of allValues) {
      const count = valueCounts[value]
      const groupName = value in renames ? renames[value] : value

      if (groupName in groupsByName) {
        const group = groupsByName[groupName]
        group.values.push(value)
        group.count += count
      } else {
        groupNames.push(groupName)
        groupsByName[groupName] = {
          name: groupName,
          values: [ value ],
          count: count
        }
      }
    }

    // Sort groups, highest count to lowest
    groupNames.sort(ValueCollator.compare)
    const groups = groupNames.map(g => groupsByName[g])

    return groups
  }

  rename (fromGroup, toGroup) {
    return this.massRename({ [fromGroup]: toGroup })
  }

  massRename (groupMap) {
    const { renames } = this
    const newRenames = Object.assign({}, renames)

    // Rewrite every value=>fromGroup to be value=>toGroup
    for (const oldValue in renames) {
      const oldGroup = renames[oldValue]
      if (oldGroup in groupMap) {
        const toGroup = groupMap[oldGroup]
        newRenames[oldValue] = toGroup
      }
    }

    // Now do the simple rewrite of fromGroup=>toGroup
    for (const fromGroup in groupMap) {
      if (!(fromGroup in newRenames)) {
        const toGroup = groupMap[fromGroup]
        newRenames[fromGroup] = toGroup
      }
    }

    // And delete duplicates
    for (const fromGroup in groupMap) {
      if (newRenames[fromGroup] === fromGroup) {
        delete newRenames[fromGroup]
      }
    }

    return new RefineSpec(newRenames)
  }

  resetGroup (group) {
    const { renames } = this

    const newRenames = Object.assign({}, renames)

    for (const key in renames) {
      if (renames[key] === group) {
        delete newRenames[key]
      }
    }

    return new RefineSpec(newRenames)
  }

  resetValue (value) {
    const { renames } = this

    const newRenames = Object.assign({}, renames)
    delete newRenames[value]

    // This _might_ remove a group. If it does, we need to remove that from
    const newGroups = {}
    for (const key in newRenames) {
      newGroups[newRenames[key]] = null
    }

    return new RefineSpec(newRenames)
  }
}

/**
 * Displays a <button> prompt that opens a Modal.
 */
class RefineModalPrompt extends React.PureComponent {
  static propTypes = {
    groups: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      count: PropTypes.number.isRequired
    }).isRequired).isRequired,
    massRename: PropTypes.func.isRequired, // func({ oldGroup: newGroup, ... }) => undefined
  }

  get bucket () {
    const groups = this.props.groups
    const ret = {}
    for (const group of groups) {
      ret[group.name] = group.count
    }
    return ret
  }

  state = {
    isModalOpen: false
  }

  openModal = () => {
    this.setState({ isModalOpen: true })
  }

  closeModal = () => {
    this.setState({ isModalOpen: false })
  }

  onSubmit = (renames) => {
    this.closeModal()
    this.props.massRename(renames)
  }

  render () {
    const { isModalOpen } = this.state
    const { groups } = this.props

    // Hide modal when there aren't enough groups
    if (groups.length < 2 && !isModalOpen) return null

    return (
      <div className='refine-modal-prompt'>
        <button type='button' name='cluster' onClick={this.openModal}>Find clusters...</button>
        <span className='instructions'></span>
        { !isModalOpen ? null : (
          <RefineModal
            bucket={this.bucket}
            onClose={this.closeModal}
            onSubmit={this.onSubmit}
          />
        )}
      </div>
    )
  }
}

class RefineGroup extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
    isVisible: PropTypes.bool.isRequired,
    isFocused: PropTypes.bool.isRequired, // update from false=>true will cause DOM focus+select()
    name: PropTypes.string, // new value -- may be empty string because a '' group is valid
    values: PropTypes.arrayOf(PropTypes.string).isRequired, // sorted by count, descending -- may be empty
    count: PropTypes.number.isRequired, // number, strictly greater than 0
    isSelected: PropTypes.bool.isRequired,
    onChangeName: PropTypes.func.isRequired, // func(oldName, newName) => undefined
    setIsSelected: PropTypes.func.isRequired, // func(value, isChecked) => undefined
    onResetGroup: PropTypes.func.isRequired, // func(name) => undefined
    onResetValue: PropTypes.func.isRequired // func(value) => undefined
  }

  textInput = React.createRef()

  state = {
    name: this.props.name,
    isExpanded: false
  }

  onChangeName = (ev) => {
    this.setState({ name: ev.target.value })
  }

  onBlurName = () => {
    if (this.props.name !== this.state.name) {
      this.props.onChangeName(this.props.name, this.state.name)
    }
  }

  getSnapshotBeforeUpdate (prevProps) {
    if (!prevProps.isFocused && this.props.isFocused) {
      // From the user's point of view, the user clicking "Merge facets" is an
      // event that should cause focus to happen. We don't want to call focus()
      // after _any_ render(): only after the first render() that happens after
      // "Merge facets" is clicked. getSnapshotBeforeUpdate() helps here.
      //
      // Set snapshot.needFocus === true; we'll focus in componentDidUpdate().
      return { needFocus: true }
    } else {
      return null
    }
  }

  // Set focus ... only after clicking the "Merge facets" button.
  componentDidUpdate (_, __, snapshot) {
    if (snapshot !== null && snapshot.needFocus) {
      this.textInput.current.focus()
      this.textInput.current.select()
    }
  }

  onChangeIsSelected = (ev) => {
    this.props.setIsSelected(this.props.name, ev.target.checked)
  }

  onChangeIsExpanded = (ev) => {
    this.setState({ isExpanded: ev.target.checked })
  }

  onKeyDown = (ev) => {
    switch (ev.keyCode) {
      case 27: // Escape
        // We need to do two things: blur the <input> and reset self.state.
        // Beware: if we naively call this.textInput.current.blur(), we'll
        // submit the edit in our blur handler.
        this.setState(
          { name: this.props.name },
          () => this.textInput.current ? this.textInput.current.blur() : null
        )
        return
      case 13: // Enter
        // We need to do two things: blur the <input> and submit the change.
        // DOM blur event does both.
        this.textInput.current.blur()
        return
      // else do nothing special
    }
  }

  onClickRemove = (ev) => {
    this.props.onResetValue(ev.target.getAttribute('data-value'))
  }

  onClickReset = (ev) => {
    this.props.onResetGroup(this.props.name)
  }

  render () {
    const { name, isExpanded } = this.state
    const { count, values, valueCounts, isVisible } = this.props

    // isOriginal uses this._props_.name, not this._state_. The group the
    // buttons would modify is this.props.name.
    const isOriginal = values.length === 1 && values[0] === this.props.name
    const className=`${isVisible ? 'visible' : 'not-visible'} ${isOriginal ? 'original' : 'edited'}`

    const maybeExpandCheckbox = isOriginal ? null : (
      <label className='expand'>
        <input
          type='checkbox'
          name='expand'
          title={isExpanded ? 'Hide original values' : 'Show original values'}
          checked={isExpanded}
          onChange={this.onChangeIsExpanded}
        />
        <i className={isExpanded ? 'icon-caret-down' : 'icon-caret-right'} />
      </label>
    )

    const maybeResetButton = isOriginal ? null : (
      <button
        name='reset'
        type='button'
        title='Cancel edits of these values'
        onClick={this.onClickReset}
      >
        <i className='icon-undo' />
      </button>
    )

    const maybeValues = (isOriginal || !isExpanded) ? null : (
      <ul className='values'>
        {values.sort(ValueCollator.compare).map(value => (
          <li key={value}>
            <span className='value'>{value}</span>
            <span className='count-and-remove'>
              { this.props.name === value ? null : (
                <button
                  type='button'
                  name={`remove[${this.props.name}]`}
                  data-value={value}
                  onClick={this.onClickRemove}
                  className='icon-close'
                >
                </button>
              )}
              <span className='count'>{valueCounts[value]}</span>
            </span>
          </li>
        ))}
      </ul>
    )

    return (
      <li className={className}>
        <div className='summary'>
          <input
            name={`include[${this.props.name}]`}
            type='checkbox'
            title='Include these rows'
            checked={this.props.isSelected}
            onChange={this.onChangeIsSelected}
          />
          {maybeExpandCheckbox}
          <span className='count-and-reset'>
            {maybeResetButton}
            <span className='count'>{NumberFormatter.format(count)}</span>
          </span>
          <div className='growing'>
            <input
              type='text'
              name={`rename[${this.props.name}]`}
              value={this.state.name}
              ref={this.textInput}
              onChange={this.onChangeName}
              onBlur={this.onBlurName}
              onKeyDown={this.onKeyDown}
            />
          </div>
        </div>
        {maybeValues}
      </li>
    )
  }
}

const buildSpecModifier = (_this, helperName, shouldSubmit=false) => {
  const func = RefineSpec.prototype[helperName]

  return (...args) => {
    const oldSpec = _this.parsedSpec
    const newSpec = func.apply(oldSpec, args)
    _this.props.onChange(newSpec.toJsonObject())
    if (shouldSubmit) _this.props.onSubmit()
  }
}

export class AllNoneButtons extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    clearSelectedSearchValues: PropTypes.func.isRequired, // func() => undefined
    fillSelectedSearchValues: PropTypes.func.isRequired // func() => undefined
  }

  render() {
    const { isReadOnly, clearSelectedSearchValues, fillSelectedSearchValues } = this.props

    return (
      <div className="all-none-buttons">
        <button
          disabled={isReadOnly}
          type='button'
          name='refine-select-all'
          title='Select All'
          onClick={fillSelectedSearchValues}
        >
          All
        </button>
        <button
          disabled={isReadOnly}
          type='button'
          name='refine-select-none'
          title='Select None'
          onClick={clearSelectedSearchValues}
        >
          None
        </button>
      </div>
    )
  }
}

/**
 * Edit a column's values to become "groups"
 *
 * The "value" here is a JSON-encoded String. Its format:
 *
 *     {
 *         "renames": {
 *             "foo": "bar", // "edit every 'foo' value to become 'bar'"
 *             //      ^^^ from the user's point of view, "bar" is the "group"
 *             ...
 *         }
 *     }
 *
 * `valueCounts` describes the input: `{ "foo": 1, "bar": 3, ... }`
 */
export class Refine extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
    loading: PropTypes.bool.isRequired, // true iff loading from server
    value: PropTypes.shape({
      renames: PropTypes.object.isRequired
    }).isRequired,
    onChange: PropTypes.func.isRequired, // fn(newValue) => undefined
  }

  state = {
    searchInput: '',
    selectedGroupNames: new Set(), // object for quick lookup
    lastMergedGroupName: null
  }

  get parsedSpec () {
    const { value } = this.props

    if (this._parsedSpec && this._parsedSpec.value === value) {
      // Memoized
      return this._parsedSpec.retval
    } else {
      const { renames } = value
      const retval = new RefineSpec(renames)
      this._parsedSpec = { value, retval }
      return retval
    }
  }

  /**
   * Return "groups": outputs, and their input
   *
   * Each "group" has the following properties:
   *
   * * `name`: a string describing the desired output
   * * `values`: strings describing the desired input; empty if no edits
   */
  get groups () {
    const valueCounts = this.props.valueCounts
    const parsedSpec = this.parsedSpec

    if (this._groups && this._groups.valueCounts === valueCounts && this._groups.parsedSpec === parsedSpec) {
      // memoize retval
      return this._groups.retval
    } else {
      if (valueCounts === null) return []
      const retval = parsedSpec.buildGroupsForValueCounts(valueCounts)
      this._groups = { valueCounts, parsedSpec, retval }
      return retval
    }
  }

  onReset = () => {
    this.setState({ searchInput: '', lastMergedGroupName: null })
  }

  onKeyDown = (ev) => {
    switch (ev.key) {
      case 'Escape':
        return this.onReset()
      case 'Enter':
        ev.preventDefault() // prevent form submit
    }
  }

  onInputChange = (ev) => {
    const searchInput = ev.target.value
    this.setState({ searchInput, lastMergedGroupName: null })
  }

  setIsGroupSelected = (group, isChecked) => {
    const { selectedGroupNames } = this.state
    if (isChecked === selectedGroupNames.has(group)) return

    const newSelectedGroups = new Set(selectedGroupNames)
    if (isChecked) {
      newSelectedGroups.add(group)
    } else {
      newSelectedGroups.delete(group)
    }

    this.setState({ selectedGroupNames: newSelectedGroups, lastMergedGroupName: null })
  }

  clearSelectedSearchValues = () => {
    const selectedGroupNames = new Set(this.state.selectedGroupNames)

    for (const groupName of this.groupNamesMatching(this.state.searchInput)) {
      selectedGroupNames.delete(groupName)
    }

    if (selectedGroupNames.size !== this.state.selectedGroupNames.size) {
      this.setState({ selectedGroupNames, lastMergedGroupName: null })
    }
  }

  fillSelectedSearchValues = () => {
    const selectedGroupNames = new Set(this.state.selectedGroupNames)

    for (const groupName of this.groupNamesMatching(this.state.searchInput)) {
      selectedGroupNames.add(groupName)
    }

    if (selectedGroupNames.size !== this.state.selectedGroupNames.size) {
      this.setState({ selectedGroupNames, lastMergedGroupName: null })
    }
  }

  /**
   * Find Set enumerating matching group names
   */
  groupNamesMatching (searchInput) {
    const groupNames = new Set()

    const valueCounts = this.props.valueCounts || {}
    const renames = this.parsedSpec.renames

    const searchKey = searchInput.toLowerCase()
    for (const value in valueCounts) {
      if (value.toLowerCase().includes(searchKey)) {
        if (value in renames) {
          groupNames.add(renames[value])
        } else {
          groupNames.add(value)
        }
      }
    }

    return groupNames
  }

  mergeSelectedValues = () => {
    const { selectedGroupNames } = this.state
    const selectedGroups = this.groups.filter(g => selectedGroupNames.has(g.name))

    // Determine the name value to default to for new group.
    //
    // Preference:
    //
    // 1. Group with largest 'values' count (number of records)
    // 2. if tied, Group with largest 'count' (number of unique values)
    // 3. if tied, Group with earliest alphabetical name
    function comparePriority(a, b) {
      if (b.count !== a.count) return b.count - a.count
      if (b.values.length !== a.values.length) return b.values.length - a.values.length
      return a.name.localeCompare(b.name)
    }
    selectedGroups.sort(comparePriority)

    const toGroup = selectedGroups[0]
    const groupMap = {}
    selectedGroups.slice(1).forEach((fromGroup) => groupMap[fromGroup.name] = toGroup.name)
    this.massRename(groupMap)
    this.setState({ selectedGroupNames: new Set(), lastMergedGroupName: toGroup.name })
  }

  rename = buildSpecModifier(this, 'rename')
  massRename = buildSpecModifier(this, 'massRename')
  resetGroup = buildSpecModifier(this, 'resetGroup')
  resetValue = buildSpecModifier(this, 'resetValue')

  render () {
    const { valueCounts } = this.props
    const { searchInput, selectedGroupNames, lastMergedGroupName } = this.state
    const groups = this.groups
    const isSearching = (searchInput !== '')
    const matchingGroupNames = isSearching ? this.groupNamesMatching(searchInput) : null

    const groupComponents = groups.map(group => (
      <RefineGroup
        key={group.name}
        isFocused={group.name === this.state.lastMergedGroupName}
        isSelected={selectedGroupNames.has(group.name)}
        isVisible={matchingGroupNames === null || matchingGroupNames.has(group.name)}
        valueCounts={valueCounts}
        onChangeName={this.rename}
        setIsSelected={this.setIsGroupSelected}
        onResetGroup={this.resetGroup}
        onResetValue={this.resetValue}
        {...group}
      />
    ))

    const canSearch = this.groups.length > 1

    const maybeMergeButton = groups.length > 0 ? (
      <button type='button' name='merge' onClick={this.mergeSelectedValues} disabled={selectedGroupNames.size < 2}>Merge facets</button>
    ) : null

    return (
      <div className='refine-parameter'>
        { !canSearch ? null : (
          <React.Fragment>
            <fieldset className="in-module--search" onSubmit={this.onSubmit} onReset={this.onReset}>
              <input
                type='search'
                placeholder='Search facets...'
                autoComplete='off'
                value={searchInput}
                onChange={this.onInputChange}
                onKeyDown={this.onKeyDown}
              />
              <button type="button" onClick={this.onReset} className="close" title="Clear Search"><i className="icon-close"></i></button>
            </fieldset>
            <AllNoneButtons
              isReadOnly={false}
              clearSelectedSearchValues={this.clearSelectedSearchValues}
              fillSelectedSearchValues={this.fillSelectedSearchValues}
            />
          </React.Fragment>
        )}
        <ul className='refine-groups'>
          {groupComponents}
        </ul>
        <div className="refine-actions">
          {maybeMergeButton}
          <RefineModalPrompt groups={this.groups} massRename={this.massRename} />
          { (isSearching && matchingGroupNames !== null && matchingGroupNames.size === 0) ? (
            <div className='wf-module-error-msg'>No values</div>
          ) : null}
        </div>
      </div>
    )
  }
}

export default withFetchedData(
  Refine,
  'valueCounts',
  ({ api, inputWfModuleId, selectedColumn }) => api.valueCounts(inputWfModuleId, selectedColumn),
  ({ inputDeltaId, selectedColumn }) => `${inputDeltaId}-${selectedColumn}`
)
