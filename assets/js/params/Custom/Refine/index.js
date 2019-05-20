import React from 'react'
import PropTypes from 'prop-types'
import { VariableSizeList, shouldComponentUpdate } from 'react-window'
import memoize from 'memoize-one'
import RefineModal from './RefineModal'
import { withFetchedData } from '../FetchedData'
import AllNoneButtons from '../../common/AllNoneButtons'
import FacetSearch from '../../common/FacetSearch'

const NumberFormatter = new Intl.NumberFormat()
const ValueCollator = new Intl.Collator() // in the user's locale

function isObjectEmpty (obj) {
  for (const v in obj) return false
  return true
}

function immutableToggleInSet(set, value, isSet) {
  const ret = new Set(set)
  if (isSet) {
    ret.add(value)
  } else {
    ret.delete(value)
  }
  return ret
}

/**
 * A collection of values the user can see and manipulate.
 *
 * It has the following properties:
 *
 * * `name`: (string) the value the Refine module will output
 * * `values`: (Array[string]) input values to rename (length >= 1)
 * * `count`: number of records with a value in `values`
 */
export class Group {
  constructor (name, values, count) {
    this.name = name
    this.values = values
    this.count = count
  }

  get isEdited () {
    if (!this.values) return undefined // React dev tools
    return this.values.length > 1 || this.values[0] !== this.name
  }
}

/**
 * A Group, plus how the user wants it to appear in a list.
 *
 * Properties:
 *
 * * `group`: the Group
 * * `isSelected`: if the "Merge" button action will include this Group
 * * `isFocused`: if we want to focus this Group's text input as we render it
 * * `wantExpand`: if the user expanded this Group. (It's `wantExpand`, not
 *                 `isExpanded`, because the user can expand a group and then
 *                 delete all edits from it, and it won't appear expanded in
 *                 that case.)
 */
export class GroupForRender {
  constructor (group, isSelected, isFocused, wantExpand) {
    this.group = group
    this.isSelected = isSelected
    this.isFocused = isFocused
    this.wantExpand = wantExpand
  }

  get name () { return this.group ? this.group.name : undefined }
  get values () { return this.group ? this.group.values : undefined }
  get count () { return this.group ? this.group.count : undefined }
  get isEdited () { return this.group ? this.group.isEdited : undefined }

  /**
   * Should this Group appear expanded?
   *
   * It should be expanded if the user expanded it _and_ it's edited. (A
   * Group without edits can't expand.)
   */
  get isExpanded () {
    return this.wantExpand && this.isEdited
  }
}

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
   * Return `Group`s: outputs, and their input
   */
  buildGroupsForValueCounts (valueCounts) {
    if (!valueCounts) return []

    const { renames } = this

    const groups = []
    const groupsByName = {}
    for (const value in valueCounts) {
      const count = valueCounts[value]
      const groupName = value in renames ? renames[value] : value

      if (groupName in groupsByName) {
        const group = groupsByName[groupName]
        group.values.push(value)
        group.count += count
      } else {
        const group = new Group(groupName, [ value ], count)
        groups.push(group)
        groupsByName[groupName] = group
      }
    }

    // Sort groups alphabetically
    groups.sort((a, b) => ValueCollator.compare(a.name, b.name))

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

    const newRenames = { ...renames }

    for (const key in renames) {
      if (renames[key] === group) {
        delete newRenames[key]
      }
    }

    return new RefineSpec(newRenames)
  }

  resetValue (value) {
    const newRenames = { ...this.renames }
    delete newRenames[value]
    return new RefineSpec(newRenames)
  }
}

/**
 * Displays a <button> prompt that opens a Modal.
 */
class RefineModalPrompt extends React.PureComponent {
  static propTypes = {
    groups: PropTypes.arrayOf(PropTypes.instanceOf(Group).isRequired).isRequired,
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

class RefineGroup extends React.Component { // uses react-window's shouldComponentUpdate, not PureComponent
  static propTypes = {
    style: PropTypes.object.isRequired, // CSS styles
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
    group: PropTypes.instanceOf(GroupForRender).isRequired,
    changeGroupName: PropTypes.func.isRequired, // func(oldName, newName) => undefined
    setIsGroupSelected: PropTypes.func.isRequired, // func(value, isSelected) => undefined
    setIsGroupExpanded: PropTypes.func.isRequired, // func(value, isExpanded) => undefined
    resetGroup: PropTypes.func.isRequired, // func(name) => undefined
    resetValue: PropTypes.func.isRequired // func(value) => undefined
  }

  // https://react-window.now.sh/#/api/shouldComponentUpdate -- big speedup
  // over React.PureComponent because we don't re-render when scrolling
  shouldComponentUpdate = shouldComponentUpdate.bind(this)

  textInput = React.createRef()

  state = {
    name: this.props.group.name
  }

  onChangeName = (ev) => {
    this.setState({ name: ev.target.value })
  }

  onBlurName = () => {
    const { group, changeGroupName } = this.props

    if (group.name !== this.state.name) {
      changeGroupName(group.name, this.state.name)
    }
  }

  getSnapshotBeforeUpdate (prevProps) {
    if (!prevProps.group.isFocused && this.props.group.isFocused) {
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

  // Set focus ... after newly rendering
  //
  // This handles the case:
  //
  // 1. Load lots and lots of data
  // 2. Rename an item ... changing its position in the list by lots and lots
  // 3. Scroll to render that item (previously it wasn't rendered)
  componentDidMount () {
    if (this.props.group.isFocused) {
      this.textInput.current.focus()
      this.textInput.current.select()
    }
  }

  onChangeIsSelected = (ev) => {
    this.props.setIsGroupSelected(this.props.group.name, ev.target.checked)
  }

  onChangeIsExpanded = (ev) => {
    this.props.setIsGroupExpanded(this.props.group.name, ev.target.checked)
  }

  onKeyDown = (ev) => {
    switch (ev.keyCode) {
      case 27: // Escape
        // We need to do two things: blur the <input> and reset self.state.
        // Beware: if we naively call this.textInput.current.blur(), we'll
        // submit the edit in our blur handler.
        this.setState(
          { name: this.props.group.name },
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
    this.props.resetValue(ev.target.getAttribute('data-value'))
  }

  onClickReset = (ev) => {
    this.props.resetGroup(this.props.group.name)
  }

  render () {
    const { name } = this.state
    const { style, group, valueCounts } = this.props
    // isEdited is from _props_, not state.
    // If user is _editing_, that doesn't mean the group is _edited_.
    const className=`refine-group ${group.isEdited ? 'edited' : 'original'}`

    const maybeExpandCheckbox = group.isEdited ? (
      <label className='expand'>
        <input
          type='checkbox'
          name='expand'
          title={group.isExpanded ? 'Hide original values' : 'Show original values'}
          checked={group.isExpanded}
          onChange={this.onChangeIsExpanded}
        />
        <i className={group.isExpanded ? 'icon-caret-down' : 'icon-caret-right'} />
      </label>
    ) : null

    const maybeResetButton = group.isEdited ? (
      <button
        name='reset'
        type='button'
        title='Cancel edits of these values'
        onClick={this.onClickReset}
      >
        <i className='icon-undo' />
      </button>
    ) : null

    const maybeValues = group.isExpanded ? (
      <ul className='values'>
        {group.values.sort(ValueCollator.compare).map(value => (
          <li key={value}>
            <span className='value'>{value}</span>
            <span className='count-and-remove'>
              { group.name === value ? null : (
                <button
                  type='button'
                  name={`remove[${group.name}]`}
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
    ) : null

    return (
      <div className={className} style={style}>
        <div className='summary'>
          <input
            className='select'
            name={`select[${group.name}]`}
            type='checkbox'
            title='Select these rows'
            checked={group.isSelected}
            onChange={this.onChangeIsSelected}
          />
          {maybeExpandCheckbox}
          <div className='rename-sizer'>
            <input
              className='rename'
              type='text'
              name={`rename[${group.name}]`}
              value={this.state.name}
              ref={this.textInput}
              onChange={this.onChangeName}
              onBlur={this.onBlurName}
              onKeyDown={this.onKeyDown}
            />
          </div>
          <span className='count-and-reset'>
            {maybeResetButton}
            <span className='count'>{NumberFormatter.format(group.count)}</span>
          </span>
        </div>
        {maybeValues}
      </div>
    )
  }
}

const buildSpecModifier = (_this, helperName, shouldSubmit=false) => {
  const func = RefineSpec.prototype[helperName]

  return (...args) => {
    const oldSpec = new RefineSpec(_this.props.value.renames)
    const newSpec = func.apply(oldSpec, args)
    _this.props.onChange(newSpec.toJsonObject())
    if (shouldSubmit) _this.props.onSubmit()
  }
}

class GroupList extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.objectOf(PropTypes.number.isRequired), // value => count, or null if loading or no column selected -- passed to <ListRow>
    loading: PropTypes.bool.isRequired,
    groups: PropTypes.arrayOf(PropTypes.instanceOf(GroupForRender).isRequired).isRequired,
    changeGroupName: PropTypes.func.isRequired, // func(groupName, newGroupName) => undefined
    setIsGroupSelected: PropTypes.func.isRequired, // func(groupName, isSelected) => undefined
    setIsGroupExpanded: PropTypes.func.isRequired, // func(groupName, isExpanded) => undefined
    resetGroup: PropTypes.func.isRequired, // func(groupName) => undefined
    resetValue: PropTypes.func.isRequired, // func(value) => undefined
    groupHeight: PropTypes.number.isRequired, // height of a closed group
    valueHeight: PropTypes.number.isRequired, // height of a single value within an open group
    expandedGroupHeight: PropTypes.number.isRequired, // height of an open group (minus all its values)
    maxHeight: PropTypes.number.isRequired
  }

  state = {
    sort: { key: 'name', ascending: true } // options: 'name' or 'count'.
  }

  listRef = React.createRef()

  groupHeight (group) {
    const { groupHeight, valueHeight, expandedGroupHeight } = this.props
    if (group.isExpanded) {
      return expandedGroupHeight + valueHeight * group.values.length
    } else {
      return groupHeight
    }
  }

  _itemKey = (index, data) => data.groups[index].name

  _itemSize = (index) => {
    const { groups, groupHeight, valueHeight, expandedGroupHeight } = this.props
    const group = groups[index]
    return this.groupHeight(group)
  }

  /**
   * Return data that requires re-render on change.
   */
  get _itemData () {
    return this._buildItemData(this.props.valueCounts, this.props.groups, this.state.sort)
  }

  _buildItemData = memoize((valueCounts, groups, sort) => {
    let sortedGroups = groups // default case: no need to sort
    if (sort.key !== 'name' || !sort.ascending) {
      if (sort.key === 'count') {
        sortedGroups.sort((a, b) => b.count - a.count || ValueCollator.compare(a.name, b.name))
      }
      if (!sort.ascending) {
        sortedGroups.reverse()
      }
    }
    return { valueCounts, groups: sortedGroups }
  })

  _renderRow = ({ index, style, data }) => {
    const { valueCounts, groups } = data
    const { changeGroupName, setIsGroupSelected, setIsGroupExpanded, resetGroup, resetValue } = this.props

    return (
      <RefineGroup
        style={style}
        valueCounts={valueCounts}
        group={groups[index]}
        changeGroupName={changeGroupName}
        setIsGroupSelected={setIsGroupSelected}
        setIsGroupExpanded={setIsGroupExpanded}
        resetGroup={resetGroup}
        resetValue={resetValue}
      />
    )
  }

  get height () {
    const { maxHeight, groups } = this.props

    let height = 0
    for (const group of groups) {
      height += this.groupHeight(group)
      if (height >= maxHeight) return maxHeight
    }

    return height
  }

  getSnapshotBeforeUpdate (prevProps) {
    return { focusIndex: prevProps.groups.findIndex(g => g.isFocused) }
  }

  componentDidUpdate (_, __, snapshot) {
    const focusIndex = this.props.groups.findIndex(g => g.isFocused)
    if (focusIndex !== -1 && snapshot && focusIndex !== snapshot.focusIndex && this.listRef.current) {
      // From the user's point of view, the user clicking "Merge facets" is an
      // event that should scroll to the new group. We don't want to scroll
      // after _any_ render(): only after the first render() that happens after
      // "Merge facets" is clicked. getSnapshotBeforeUpdate() helps here.
      //
      // See also RefineGroup.componentDidMount() and componentDidUpdate():
      // they'll focus the element after we scroll to it (and in the case of
      // scrolling, after we mount it for the first time).
      this.listRef.current.scrollToItem(focusIndex)
    }
  }

  innerRender () {
    const { valueCounts, loading, groups, groupHeight, changeGroupName, setIsGroupSelected, resetGroup, resetValue } = this.props

    if (!valueCounts && !loading) {
      // Waiting for user to select a column
      return null
    } else if (loading) {
      return 'Loading values…'
    } else if (isObjectEmpty(valueCounts)) {
      return 'This column does not have any values'
    } else if (groups.length === 0) {
      return 'No values match your search'
    } else {
      if (this.listRef.current) {
        // If we're re-rendering this component, then it's likely a list item
        // has changed height. Clear react-window's style cache.
        //
        // [adamhooper, 2019-03-19] I haven't found a tidier way to do this.
        // We can't merely clear the cache when handling user events, because
        // groups can change without any user events occurring.
        this.listRef.current.resetAfterIndex(0, false)
      }

      return (
        <fieldset className='group-list'>
          <VariableSizeList
            ref={this.listRef}
            className='react-list'
            height={this.height}
            estimatedItemSize={groupHeight /* most items aren't expanded */}
            itemSize={this._itemSize}
            itemKey={this._itemKey}
            itemCount={groups.length}
            itemData={this._itemData}
          >
            {this._renderRow}
          </VariableSizeList>
        </fieldset>
      )
    }
  }

  render () {
    const { outerRef } = this.props

    return (
      <div className='refine-groups' ref={outerRef}>{this.innerRender()}</div>
    )
  }
}

/**
 * GroupList, with maxHeight, groupHeight, valueHeight and expandedGroupHeight calculated automatically.
 *
 * The trick is: first we render a dummy list and calculate heights using  that.
 * Then we delete the dummy list and use the calculated heights in an _actual_ list.
 * This lets us read data from CSS.
 */
class DynamicallySizedGroupList extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.objectOf(PropTypes.number.isRequired), // value => count, or null if loading or no column selected -- passed to <ListRow>
    loading: PropTypes.bool.isRequired,
    groups: PropTypes.arrayOf(PropTypes.instanceOf(GroupForRender)),
    changeGroupName: PropTypes.func.isRequired, // func(groupName, newGroupName) => undefined
    setIsGroupSelected: PropTypes.func.isRequired, // func(groupName, isSelected) => undefined
    setIsGroupExpanded: PropTypes.func.isRequired, // func(groupName, isExpanded) => undefined
    resetGroup: PropTypes.func.isRequired, // func(groupName) => undefined
    resetValue: PropTypes.func.isRequired // func(value) => undefined
  }

  sizerRef = React.createRef()

  state = {
    groupHeight: null,
    valueHeight: null,
    expandedGroupHeight: null,
    maxHeight: null
  }

  componentDidMount () {
    // This is _always_ called with phony, measurement-only data.
    const sizer = this.sizerRef.current

    const sizerStyle = window.getComputedStyle(sizer)
    let maxHeight
    if (!sizerStyle.maxHeight || sizerStyle.maxHeight === 'none') {
      maxHeight = Infinity
    } else {
      maxHeight = parseFloat(sizerStyle.maxHeight) // parseFloat: convert e.g. "300px" to 300
    }

    const closedGroup = sizer.querySelector('.refine-group:nth-child(1)')
    const expandedGroup1Value = sizer.querySelector('.refine-group:nth-child(2)')
    const expandedGroup2Values = sizer.querySelector('.refine-group:nth-child(3)')

    const groupHeight = closedGroup.scrollHeight
    const valueHeight = expandedGroup2Values.scrollHeight - expandedGroup1Value.scrollHeight
    const expandedGroupHeight = expandedGroup1Value.scrollHeight - valueHeight

    this.setState({
      maxHeight,
      // Set default heights for unit tests, where scrollHeight is always 0
      groupHeight: groupHeight || 1,
      valueHeight: valueHeight || 1,
      expandedGroupHeight: expandedGroupHeight || 1
    })

    // Resize when user turns Zen Mode on and off; and in Zen Mode, resize
    // when resizing the browser window.
    window.addEventListener('resize', this.onResize)
  }

  onResize = () => {
    const sizer = this.sizerRef.current

    const sizerStyle = window.getComputedStyle(sizer)
    let maxHeight
    if (!sizerStyle.maxHeight || sizerStyle.maxHeight === 'none') {
      maxHeight = Infinity
    } else {
      maxHeight = parseFloat(sizerStyle.maxHeight) // parseFloat: convert e.g. "300px" to 300
    }

    this.setState({ maxHeight })
  }

  componentWillUnmount () {
    window.removeEventListener('resize', this.onResize)
  }

  componentDidUpdate () {
    this.onResize()
  }

  render () {
    if (this.state.maxHeight === null) {
      // Render placeholder list; we'll use it for measuring in this.componentDidMount()
      return (
        <GroupList
          key='placeholder'
          valueCounts={{a: 1, b1: 1, c: 1, c2: 1}}
          loading={false}
          groups={[
            new GroupForRender(new Group('a', ['a'], 1), false, false, false),
            new GroupForRender(new Group('b', ['b1'], 1), false, false, true),
            new GroupForRender(new Group('c', ['c', 'c2'], 1), false, false, true)
          ]}
          changeGroupName={() => {}}
          setIsGroupSelected={() => {}}
          setIsGroupExpanded={() => {}}
          resetGroup={() => {}}
          resetValue={() => {}}
          maxHeight={99}
          groupHeight={1}
          valueHeight={1}
          expandedGroupHeight={1}
          outerRef={this.sizerRef}
        />
      )
    } else {
      return (
        <GroupList
          key='sized'
          outerRef={this.sizerRef}
          {...this.state}
          {...this.props}
        />
      )
    }
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
    selectedGroupNames: new Set(),
    expandedGroupNames: new Set(),
    focusGroupName: null
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
    const { valueCounts, value: { renames } } = this.props
    return this._buildGroups(valueCounts, renames)
  }

  _buildGroups = memoize((valueCounts, renames) => {
    if (!valueCounts) return []
    return new RefineSpec(renames).buildGroupsForValueCounts(valueCounts)
  })

  onChangeSearch = (searchInput) => {
    this.setState({ searchInput, focusGroupName: null })
  }

  onReset = () => {
    this.setState({ searchInput: '', focusGroupName: null })
  }

  setIsGroupExpanded = (groupName, isExpanded) => {
    const { expandedGroupNames } = this.state
    if (isExpanded === expandedGroupNames.has(groupName)) return
    const newExpandedGroupNames = immutableToggleInSet(expandedGroupNames, groupName, isExpanded)
    this.setState({ expandedGroupNames: newExpandedGroupNames, focusGroupName: null })
  }

  setIsGroupSelected = (groupName, isSelected) => {
    const { selectedGroupNames } = this.state
    if (isSelected === selectedGroupNames.has(groupName)) return
    const newSelectedGroupNames = immutableToggleInSet(selectedGroupNames, groupName, isSelected)
    this.setState({ selectedGroupNames: newSelectedGroupNames, focusGroupName: null })
  }

  deselectMatchingGroups = () => {
    const selectedGroupNames = new Set(this.state.selectedGroupNames)

    for (const group of this.matchingGroups) {
      selectedGroupNames.delete(group.name)
    }

    if (selectedGroupNames.size !== this.state.selectedGroupNames.size) {
      this.setState({ selectedGroupNames, focusGroupName: null })
    }
  }

  selectMatchingGroups = () => {
    const selectedGroupNames = new Set(this.state.selectedGroupNames)

    for (const group of this.matchingGroups) {
      selectedGroupNames.add(group.name)
    }

    if (selectedGroupNames.size !== this.state.selectedGroupNames.size) {
      this.setState({ selectedGroupNames, focusGroupName: null })
    }
  }

  /**
   * Iterate over search results.
   *
   * If this.state.searchInput === null, return `this.groups`.
   */
  get matchingGroups () {
    const { searchInput } = this.state
    return this._buildMatchingGroups(this.groups, searchInput)
  }

  _buildMatchingGroups = memoize((groups, searchInput) => {
    if (!searchInput) return groups

    const searchKey = searchInput.toLowerCase()

    return groups.filter(group => {
      if (group.name.toLowerCase().includes(searchKey)) return true
      for (const value of group.values) {
        if (value.toLowerCase().includes(searchKey)) return true
      }
      return false
    })
  })

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
    this.setState({ selectedGroupNames: new Set(), focusGroupName: toGroup.name })
  }

  setGroupName = (groupName, newGroupName) => {
    buildSpecModifier(this, 'rename')(groupName, newGroupName)
    // The user just renamed a group or value. Scroll+focus the new group.
    //
    // This handles the case:
    //
    // 1. User opens big list
    // 2. User edits "aaa"
    // 3. User sets value to "zzz"
    //
    // Expected results: "zzz" is in view
    // ... a side-effect is that we select() the "zzz" so user's keypresses
    // overwrite it. Workaround: the user can hit Escape to undo those
    // keypresses or Tab to unfocus the "zzz".
    this.setState({ focusGroupName: newGroupName })
  }

  massRename = buildSpecModifier(this, 'massRename')
  resetGroup = buildSpecModifier(this, 'resetGroup')
  resetValue = buildSpecModifier(this, 'resetValue')

  render () {
    const { valueCounts, loading } = this.props
    const { searchInput, selectedGroupNames, expandedGroupNames, focusGroupName } = this.state
    const isSearching = (searchInput !== '')
    const groups = this.matchingGroups
      .map(g => new GroupForRender(
        g,
        selectedGroupNames.has(g.name),
        focusGroupName === g.name,
        expandedGroupNames.has(g.name)
      ))

    const canSearch = this.groups.length > 1

    const maybeMergeButton = groups.length > 0 ? (
      <button type='button' name='merge' onClick={this.mergeSelectedValues} disabled={selectedGroupNames.size < 2}>Merge facets</button>
    ) : null

    return (
      <div className='refine-parameter'>
        { !canSearch ? null : (
          <React.Fragment>
            <FacetSearch
              value={searchInput}
              onChange={this.onChangeSearch}
              onReset={this.onReset}
            />
            <AllNoneButtons
              isReadOnly={false}
              onClickNone={this.deselectMatchingGroups}
              onClickAll={this.selectMatchingGroups}
            />
          </React.Fragment>
        )}
        <DynamicallySizedGroupList
          valueCounts={valueCounts}
          loading={loading}
          groups={groups}
          changeGroupName={this.setGroupName}
          setIsGroupSelected={this.setIsGroupSelected}
          setIsGroupExpanded={this.setIsGroupExpanded}
          resetGroup={this.resetGroup}
          resetValue={this.resetValue}
        />
        <div className='refine-actions'>
          {maybeMergeButton}
          <RefineModalPrompt groups={this.groups} massRename={this.massRename} />
        </div>
      </div>
    )
  }
}

export default withFetchedData(
  Refine,
  'valueCounts',
  ({ api, inputWfModuleId, selectedColumn }) => selectedColumn === null ? Promise.resolve(null) : api.valueCounts(inputWfModuleId, selectedColumn),
  ({ inputDeltaId, selectedColumn }) => selectedColumn === null ? null : `${inputDeltaId}-${selectedColumn}`
)
