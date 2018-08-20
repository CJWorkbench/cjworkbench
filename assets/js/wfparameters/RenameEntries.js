import React from 'react'
import PropTypes from 'prop-types'
import {store, deleteModuleAction} from "../workflow-reducer"

export class RenameEntry extends React.Component {
  static propTypes = {
    colname: PropTypes.string.isRequired,
    newColname: PropTypes.string.isRequired,
    onColRename: PropTypes.func.isRequired,
    onEntryDelete: PropTypes.func.isRequired,
    isReadOnly: PropTypes.bool.isRequired
  }

  constructor(props) {
    super(props)

    this.state = {
      inputValue: this.props.newColname
    }

    this.handleChange = this.handleChange.bind(this)
    this.handleKeyPress = this.handleKeyPress.bind(this)
    this.handleBlur = this.handleBlur.bind(this)
    this.handleFocus = this.handleFocus.bind(this)
    this.handleDelete = this.handleDelete.bind(this)
  }

  componentWillReceiveProps(nextProps) {
    if (nextProps.newColname != this.state.inputValue) {
      this.setState({inputValue: nextProps.newColname})
    }
  }

  handleChange(event) {
    //this.props.onColRename(this.props.colname, event.target.value)
    this.setState({inputValue: event.target.value})
  }

  handleBlur() {
    if(this.state.inputValue != this.props.newColname) {
      this.props.onColRename(this.props.colname, this.state.inputValue)
    }
  }

  handleKeyPress(event) {
    if((event.key == 'Enter') && (this.state.inputValue != this.props.newColname)) {
      this.props.onColRename(this.props.colname, this.state.inputValue)
    }
  }

  handleFocus(event) {
    event.target.select()
  }

  handleDelete() {
    this.props.onEntryDelete(this.props.colname)
  }

  render() {
    // The class names below are used in testing.
    // Changing them would require updating the tests accordingly.
    return (
      <div className="wf-parameter rename-entry" data-column-name={this.props.colname}>
        <div className={'rename-column'}>{this.props.colname}</div>
        <div className="rename-container">
          <input
            className={'rename-input'}
            type={'text'}
            value={this.state.inputValue}
            onChange={this.handleChange}
            onBlur={this.handleBlur}
            onKeyPress={this.handleKeyPress}
            onFocus={this.handleFocus}
            readOnly={this.props.isReadOnly}
          />
          <button
            className={'rename-delete icon-close'}
            onClick={this.handleDelete}
            disabled={this.props.isReadOnly}
          ></button>
        </div>
      </div>
    )
  }
}

export default class RenameEntries extends React.Component {
  static propTypes = {
    allColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null for unknown list (loading or stalled)
    entriesJsonString: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired, // onChange(JSON.stringify({ old: new, ...})) => undefined
    isReadOnly: PropTypes.bool.isRequired
  }

  get parsedEntries() {
    if (!this.props.entriesJsonString || this.props.entriesJsonString === '{}') {
      // No JSON? Then we probably just created the module manually. Its default
      // value should be _everything_.
      const ret = {}
      for (const column of this.props.allColumns) {
        ret[column.name] = column.name
      }
      return ret
    } else {
      return JSON.parse(this.props.entriesJsonString)
    }
  }

  onColRename = (prevName, nextName) => {
    const oldEntries = this.parsedEntries
    if (oldEntries[prevName] === nextName) return // no-op

    const newEntries = {
      ...oldEntries,
      [prevName]: nextName
    }
    this.props.onChange(JSON.stringify(newEntries))
  }

  onEntryDelete = (prevName) => {
    const oldEntries = { ...this.parsedEntries }
    if (!(prevName in oldEntries)) return // no-op

    const newEntries = { ...oldEntries }
    delete newEntries[prevName]

    if (Object.keys(newEntries).length == 0) {
      // FIXME do not use store here
      store.dispatch(deleteModuleAction(this.props.wfModuleId))
    } else {
      this.props.onChange(JSON.stringify(newEntries))
    }
  }

  renderEntries() {
    const entries = this.parsedEntries

    return (this.props.allColumns || [])
      .filter(({ name }) => name in entries)
      .map(({ name }) => (
        <RenameEntry
          key={name}
          colname={name}
          newColname={entries[name]}
          onColRename={this.onColRename}
          onEntryDelete={this.onEntryDelete}
          isReadOnly={this.props.isReadOnly}
        />
      ))
  }

  render() {
    const entries = this.renderEntries()
    return (
      <div className="RenameEntries--container">{entries}</div>
    )
  }
}
