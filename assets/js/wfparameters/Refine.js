import React from 'react'
import PropTypes from 'prop-types'

const NumberFormatter = new Intl.NumberFormat()

class RefineGroup extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
    name: PropTypes.string, // new value -- may be empty string
    values: PropTypes.arrayOf(PropTypes.string).isRequired, // sorted by count, descending -- may be empty
    count: PropTypes.number.isRequired, // number, strictly greater than 0
    isBlacklisted: PropTypes.bool.isRequired,
    onChangeName: PropTypes.func.isRequired, // func(oldName, newName) => undefined
    onChangeIsBlacklisted: PropTypes.func.isRequired, // func(name, isBlacklisted) => undefined
  }

  state = {
    name: this.props.name,
  }

  onChangeName = (ev) => {
    this.setState({ name: ev.target.value })
  }

  onBlurName = () => {
    if (this.props.name !== this.state.value) {
      this.props.onChangeName(this.props.name, this.state.name)
    }
  }

  onChangeIsBlacklisted = (ev) => {
    this.props.onChangeIsBlacklisted(this.props.name, !ev.target.checked)
  }

  onKeyDown = (ev) => {
    switch (ev.keyCode) {
      case 27: // Escape
        return this.setState({ value: this.props.name })
      case 13: // Enter
        return this.props.onChangeName(this.props.name, this.state.name)
      // else do nothing special
    }
  }

  render () {
    const { name } = this.state
    const { count, values, valueCounts } = this.props

    const isOriginal = values.length === 1 && values[0] === name
    const className = isOriginal ? '' : 'edited'

    return (
      <React.Fragment>
        <dt className={className}>
          <label className="checkbox">
            <input
              type="checkbox"
              title="Include these rows"
              checked={!this.props.isBlacklisted}
              onChange={this.onChangeIsBlacklisted}
            />
          </label>
          <input
            type="text"
            name="name"
            value={this.state.name}
            onChange={this.onChangeName}
            onBlur={this.onBlurName}
            onKeyDown={this.onKeyDown}
          />
          <span className="count">{NumberFormatter.format(count)}</span>
        </dt>
        <dd>
        </dd>
      </React.Fragment>
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
export class Refine extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
    loading: PropTypes.bool.isRequired, // true iff loading from server
    value: PropTypes.string.isRequired, // JSON-encoded {renames: {value1: 'newvalue1', ...}, blacklist: ['newvalue1']}
    onChange: PropTypes.func.isRequired, // fn(newValue) => undefined
  }

  get parsedValue () {
    const { renames, blacklist } = JSON.parse(this.props.value || '{"renames": {}, "blacklist": []}')

    return { renames, blacklist }
  }

  /**
   * Return "groups": outputs, and their input
   *
   * Each "group" has the following properties:
   *
   * * `value`: a string describing the desired output
   * * `values`: strings describing the desired input; empty if no edits
   * * `isBlacklisted`: true if we are omitting this group from output
   */
  get groups () {
    const { valueCounts } = this.props
    const { renames, blacklist } = this.parsedValue

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
          count: count,
          isBlacklisted: false // for now
        }
      }
    }

    // Blacklist groups
    for (const groupName of blacklist) {
      groupsByName[groupName].isBlacklisted = true
    }

    // Sort groups, highest count to lowest
    groupNames.sort((a, b) => (groupsByName[b].count - groupsByName[a].count) || a.localeCompare(b))

    const groups = groupNames.map(g => groupsByName[g])

    // Sort values within each group, highest count to lowest
    for (const group of groups) {
      group.values.sort((a, b) => (valueCounts[b] - valueCounts[a]) || a.localeCompare(b))
    }

    return groups
  }

  rename = (fromGroup, toGroup) => {
    const { renames, blacklist } = this.parsedValue
    const newRenames = Object.assign({}, renames)

    // Start with blacklist as a "Set": { groupA: null, groupB: null, ... }
    const blacklistSet = {}
    for (const group of blacklist) {
      blacklistSet[group] = null
    }

    // Rewrite every value=>fromGroup to be value=>toGroup
    for (const oldValue in renames) {
      const oldGroup = renames[oldValue]
      if (oldGroup === fromGroup) {
        newRenames[oldValue] = toGroup

        // Rename a blacklist entry if we need to
        if (oldGroup in blacklistSet) {
          delete blacklistSet[oldGroup]
          blacklistSet[toGroup] = null
        }
      }
    }

    newRenames[fromGroup] = toGroup

    const newValue = JSON.stringify({
      renames: newRenames,
      blacklist: Object.keys(blacklistSet)
    })

    this.props.onChange(newValue)
  }

  setBlacklisted = (group, isBlacklisted) => {
    const { renames, blacklist } = this.parsedValue

    const newBlacklist = blacklist.slice()

    const index = blacklist.indexOf(group)
    if (index === -1) {
      // Add to blacklist
      newBlacklist.push(group)
    } else {
      // Remove from blacklist
      newBlacklist.splice(index, 1)
    }

    this.props.onChange(JSON.stringify({
      renames: renames,
      blacklist: newBlacklist
    }))
  }

  render () {
    const { valueCounts } = this.props
    const groupComponents = this.groups.map(group => (
      <RefineGroup
        key={group.name}
        valueCounts={valueCounts}
        onChangeName={this.rename}
        onChangeIsBlacklisted={this.setBlacklisted}
        {...group}
      />
    ))

    return (
      <div className="refine-groups">
        <dl>
          {groupComponents}
        </dl>
      </div>
    )
  }
}

// https://reactjs.org/docs/higher-order-components.html
//
// Let's keep this generic and maybe make it into a reusable util later.
function withFetchedData(WrappedComponent, dataName) {
  return class extends React.PureComponent {
    static propTypes = {
      fetchData: PropTypes.func.isRequired, // fn() => Promise[data]
      workflowRevision: PropTypes.number.isRequired,
    }

    state = {
      data: null,
      loading: false
    }

    _reload () {
      const workflowRevision = this.props.workflowRevision

      // Keep state.data unchanged, until we solve
      // https://www.pivotaltracker.com/story/show/158034731. After that, we
      // should probably change this to setState({data: null})
      this.setState({ loading: true })

      this.props.fetchData()
        .then(data => {
          if (this.unmounted) return
          if (this.props.workflowRevision !== workflowRevision) return // ignore wrong response in race

          this.setState({
            loading: false,
            data
          })
        })
    }

    componentDidMount () {
      this._reload()
    }

    componentWillUnmount () {
      this.unmounted = true
    }

    componentDidUpdate (prevProps) {
      if (prevProps.workflowRevision !== this.props.workflowRevision) {
        this._reload()
      }
    }

    render () {
      const props = Object.assign({
        [dataName]: this.state.data,
        loading: this.state.loading
      }, this.props)
      delete props.fetchData
      delete props.workflowRevision

      return <WrappedComponent {...props} />
    }
  }
}

export default withFetchedData(Refine, 'valueCounts')

//class EditRow extends React.Component {
//
//    // Component for each row in the histogram
//
//    constructor(props) {
//        super(props);
//        this.state = {
//            initValue: this.props.dataValue,
//            dataValue: this.props.dataValue,
//            dataCount: this.props.dataCount,
//            selected: this.props.valueSelected,
//        }
//        this.handleValueChange = this.handleValueChange.bind(this);
//        this.handleBlur = this.handleBlur.bind(this);
//        this.handleFocus = this.handleFocus.bind(this);
//        this.handleKeyPress = this.handleKeyPress.bind(this);
//
//        this.handleSelectionChange = this.handleSelectionChange.bind(this);
//    }
//
//    componentWillReceiveProps(nextProps) {
//        var nextState = Object.assign({}, this.state);
//        nextState.initValue = nextProps.dataValue;
//        nextState.dataValue = nextProps.dataValue;
//        nextState.dataCount = nextProps.dataCount;
//        nextState.selected = nextProps.valueSelected;
//        this.setState(nextState);
//    }
//
//    handleValueChange(event) {
//        var nextState = Object.assign({}, this.state);
//        nextState.dataValue = event.target.value;
//        this.setState(nextState);
//    }
//
//    handleKeyPress(event) {
//        if(event.key == 'Enter') {
//            event.preventDefault();
//            if(this.state.initValue != this.state.dataValue) {
//                this.sendValueChange();
//            }
//        }
//    }
//
//    handleBlur() {
//        if(this.state.initValue != this.state.dataValue) {
//            this.sendValueChange();
//        }
//    }
//
//    sendValueChange() {
//        this.props.onValueChange({
//            fromVal: this.state.initValue,
//            toVal: this.state.dataValue
//        });
//    }
//
//    handleFocus(event) {
//        event.target.select();
//    }
//
//    handleSelectionChange(event) {
//        var nextState = Object.assign({}, this.state);
//        nextState.selected = (!nextState.selected);
//        this.setState(nextState);
//        this.props.onSelectionChange({
//            value: this.state.initValue
//        });
//    }
//
//    render() {
//        return (
//            <div
//                className={'checkbox-container facet-checkbox-container ' + (this.props.valueEdited ? 'facet-edited' : '')}
//                style={{'whiteSpace': 'nowrap'}}>
//                <div className="d-flex align-items-center">
//                  <input
//                      name={`selected[${this.state.initValue}]`}
//                      type='checkbox'
//                      onChange={this.handleSelectionChange}
//                      checked={this.state.selected}
//                      className={'facet-checkbox'}
//                  />
//                  <input
//                      type='text'
//                      name={`rename[${this.state.initValue}]`}
//                      value={this.state.dataValue}
//                      onChange={this.handleValueChange}
//                      onFocus={this.handleFocus}
//                      onBlur={this.handleBlur}
//                      onKeyPress={this.handleKeyPress}
//                      className={'facet-value t-d-gray content-3' + (this.props.valueEdited ? ' facet-value--edited' : '')}
//                  />
//                </div>
//                <div className='facet-count t-m-gray content-4'>{this.state.dataCount}</div>
//            </div>
//        )
//    }
//};
//
//EditRow.propTypes = {
//    dataValue: PropTypes.string.isRequired,
//    dataCount: PropTypes.number.isRequired,
//    onValueChange: PropTypes.func.isRequired,
//    onSelectionChange: PropTypes.func.isRequired,
//    valueSelected: PropTypes.bool.isRequired,
//    valueEdited: PropTypes.bool.isRequired
//}
//
//export default class Refine extends React.Component {
//    static propTypes = {
//        api: PropTypes.shape({
//          histogram: PropTypes.func.isRequired,
//        }).isRequired,
//        wfModuleId: PropTypes.number.isRequired,
//        selectedColumn: PropTypes.string.isRequired,
//        existingEdits: PropTypes.string.isRequired,
//        saveEdits: PropTypes.func.isRequired,
//        revision: PropTypes.number.isRequired
//    }
//
//    /*
//    Format of edits:
//    {
//        type: 'select' or 'change',
//        column: target column
//        content: {
//            fromVal: ...(for 'change')
//            toVal: ...(for 'change')
//            value: ...(for 'select')
//        },
//        timestamp: ...
//    }
//     */
//
//    constructor(props) {
//        super(props);
//        this.state = {
//            selectedColumn: this.props.selectedColumn,
//            histogramLoaded: false,
//            histogramData: [],
//            histogramNumRows: 0,
//            showWarning: false,
//            showColError: false,
//            edits: JSON.parse(props.existingEdits.length > 0 ? props.existingEdits : '[]'),
//        }
//
//        this.handleValueChange = this.handleValueChange.bind(this);
//        this.handleSelectionChange = this.handleSelectionChange.bind(this);
//    }
//
//    componentDidMount() {
//        if(this.state.selectedColumn.length > 0) {
//            this.loadHistogram(this.state.selectedColumn, this.state);
//        }
//    }
//
//    propsAreEqual(props1, props2) {
//        if(props1.revision != props2.revision)
//            return false;
//        if(props1.selectedColumn != props2.selectedColumn)
//            return false;
//        if(props1.existingEdits != props2.existingEdits)
//            return false;
//        return true;
//    }
//
//    componentDidUpdate(prevProps) {
//        const nextProps = this.props
//        // Handles revision changes and column changes
//
//        var nextColumn = nextProps.selectedColumn;
//        var nextRevision = nextProps.revision;
//        if(nextProps.revision != prevProps.revision) {
//            if(nextColumn != this.state.selectedColumn) {
//                // If the column changes, check if this is a undo; if not, clear the edits
//                // The empty edits will be saved to the server on the next edit
//                var nextState = Object.assign({}, this.state);
//                // Warning is shown if previous column has edits,
//                // previous column isn't empty and action is not an undo.
//                nextState.showWarning = (this.state.selectedColumn.length > 0) && (this.state.edits.length > 0) && (nextRevision > prevProps.revision);
//                nextState.edits = (nextRevision >= prevProps.revision) ? [] : JSON.parse(nextProps.existingEdits);
//                nextState.selectedColumn = nextColumn;
//                //console.log(nextState.edits);
//                this.loadHistogram(nextColumn, nextState);
//            } else {
//                // Otherwise, load everything as usual
//                var nextState = Object.assign({}, this.state);
//                nextState.edits = JSON.parse(nextProps.existingEdits.length > 0 ? nextProps.existingEdits : '[]');
//                if(this.state.edits.length != nextState.edits.length) {
//                    // The column switching warning should be hidden if new edits are added
//                    nextState.showWarning = (nextState.edits.length == 0);
//                    // The histogram should be reloaded only if edits are added/removed
//                }
//                this.loadHistogram(nextColumn, nextState);
//            }
//        }
//    }
//
//    shouldComponentUpdate(nextProps, nextState) {
//        // Prevent extra renders when props are the same
//        if(this.propsAreEqual(this.props, nextProps)) {
//            return this.state != nextState;
//        }
//        return true;
//    }
//
//    loadHistogram(targetCol, baseState, clearEdits=false) {
//        // Loads a histogram from the server and sets the state with the result
//
//        // clearEdits controls whether we clear the edit on the server immediately upon load
//        // This is unused for now.
//        if(targetCol.length == 0) {
//            var nextState = Object.assign(baseState);
//            nextState.histogramLoaded = false;
//            nextState.histogramData = [];
//            this.setState(nextState);
//            return;
//        }
//        this.props.api.histogram(this.props.wfModuleId, targetCol)
//            .then(histogram => {
//                if(histogram != 'request error') {
//                    //console.log(histogram);
//                    var nextState = Object.assign({}, baseState);
//                    var editedHistogram = histogram.rows.map(function (entry) {
//                        var newEntry = Object.assign({}, entry);
//                        newEntry.selected = true;
//                        newEntry.edited = false;
//                        return newEntry;
//                    });
//                    // Apply all relevant edits we have to the original histogram
//                    for (var i = 0; i < nextState.edits.length; i++) {
//                        //console.log('applying edit');
//                        if (nextState.edits[i].column == nextState.selectedColumn) {
//                            editedHistogram = this.applySingleEdit(editedHistogram, nextState.edits[i]);
//                        }
//                    }
//                    editedHistogram.sort((item1, item2) => {
//                        return item1[INTERNAL_COUNT_COLNAME] < item2[INTERNAL_COUNT_COLNAME] ? 1 : -1;
//                    })
//                    nextState.histogramData = editedHistogram;
//                    nextState.histogramNumRows = editedHistogram.length;
//                    nextState.histogramLoaded = true;
//                    nextState.showColError = false;
//                    this.setState(nextState);
//                } else {
//                    var nextState = Object.assign({}, baseState);
//                    nextState.histogramLoaded = false;
//                    nextState.histogramData = [];
//                    nextState.histogramNumRows = nextState.histogramData.length;
//                    nextState.showColError = true;
//                    this.setState(nextState);
//                }
//                //this.forceUpdate();
//            })
//            .then(() => {
//                if(clearEdits) {
//                    this.props.saveEdits('[]');
//                }
//            });
//    }
//
//    applySingleEdit(hist, edit) {
//        // Applies edits on the client side
//
//        var newHist = hist.slice();
//        if(edit.type == 'change') {
//            var fromIdx = newHist.findIndex(function(element) {
//               return (element[edit.column] == edit.content.fromVal);
//            });
//            var fromEntry = Object.assign({}, newHist[fromIdx]);
//            newHist.splice(fromIdx, 1);
//            var toIdx = newHist.findIndex(function(element) {
//                return (element[edit.column] == edit.content.toVal);
//            });
//            if (toIdx == -1) {
//                // If no "to" entry was found, create a new entry
//                var newEntry = Object.assign({}, fromEntry);
//                newEntry[edit.column] = edit.content.toVal;
//                newEntry.edited = true;
//                newHist.unshift(newEntry);
//            } else {
//                // Otherwise, we merge the "from" entry to the "to" entry
//                // The new cluster always appears on top
//                var toEntry = Object.assign({}, newHist[toIdx]);
//                newHist.splice(toIdx, 1);
//                toEntry[INTERNAL_COUNT_COLNAME] += fromEntry[INTERNAL_COUNT_COLNAME];
//                toEntry.edited = true;
//                newHist.unshift(toEntry);
//            }
//        } else if(edit.type == 'select') {
//            var targetIdx = newHist.findIndex(function(element) {
//               return (element[edit.column] == edit.content.value);
//            });
//            newHist[targetIdx].selected = (!newHist[targetIdx].selected);
//        }
//        return newHist;
//    }
//
//    handleValueChange(changeData) {
//        // Handles edits to values; pushes changes to the server by setting the parameter
//
//        var nextEdits = this.state.edits.slice();
//        nextEdits.push({
//            type: 'change',
//            column: this.state.selectedColumn,
//            content: {
//                fromVal: changeData.fromVal,
//                toVal: changeData.toVal
//            },
//            timestamp: Date.now()
//        });
//        this.props.saveEdits(JSON.stringify(nextEdits));
//    }
//
//    handleSelectionChange(changeData) {
//        // Handles selection/deselection of facets; pushes changes to server
//
//        var nextEdits = this.state.edits.slice();
//        nextEdits.push({
//            type: 'select',
//            column: this.state.selectedColumn,
//            content: {
//                value: changeData.value,
//            },
//            timestamp: Date.now(),
//        });
//        this.props.saveEdits(JSON.stringify(nextEdits));
//    }
//
//    renderHistogram() {
//        if(this.state.histogramLoaded) {
//            const checkboxes = this.state.histogramData.map(item => {
//                return (
//                    <EditRow
//                        dataValue={item[this.state.selectedColumn].toString()}
//                        dataCount={item[INTERNAL_COUNT_COLNAME]}
//                        key={item[this.state.selectedColumn]}
//                        onValueChange={this.handleValueChange}
//                        onSelectionChange={this.handleSelectionChange}
//                        valueSelected={item.selected}
//                        valueEdited={item.edited}
//                    />
//                );
//            });
//
//            return (
//                <div className="wf-parameter">
//                    {this.state.showWarning ?
//                        (
//                            <div>
//                                <br />
//                                <UncontrolledAlert color={'warning'}>
//                                    Switching columns will clear your previous work. If you did it by accident, use "undo" from the top-right menu to go back,
//                                </UncontrolledAlert>
//                            </div>
//                        ) : ''
//                    }
//                    <div className='t-d-gray content-3 mt-2 label-margin'>Select and edit values</div>
//                    <div className='container list-wrapper'>
//                        <div className='row list-scroll'>
//                            { checkboxes }
//                        </div>
//                    </div>
//                </div>
//            )
//        }
//        if(this.state.showColError) {
//            return (
//                <div>
//                    <UncontrolledAlert color={'danger'} className='content-3'>
//                        Previously selected column was deleted. Please select a new one.
//                    </UncontrolledAlert>
//                </div>
//            )
//        }
//    }
//
//    render() {
//        const componentContent = this.renderHistogram();
//        return (
//            <div className="">
//                {componentContent}
//            </div>
//        )
//    }
//};
