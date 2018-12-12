import React from 'react'
import PropTypes from 'prop-types'

export class RenameEntry extends React.PureComponent {
  static propTypes = {
    colname: PropTypes.string.isRequired,
    defaultValue: PropTypes.string.isRequired,
    onEntryRename: PropTypes.func.isRequired,
    onEntryDelete: PropTypes.func.isRequired,
    isReadOnly: PropTypes.bool.isRequired
  }

  state = {
    value: this.props.defaultValue
  }

  handleChange = (ev) => {
    //this.props.onEntryRename(this.props.colname, event.target.value)
    this.setState({ value: ev.target.value })
  }

  handleBlur = () => {
    if (this.state.value != this.props.defaultValue) {
      this.props.onEntryRename(this.props.colname, this.state.value)
    }
  }

  handleKeyPress = (ev) => {
    if (ev.key == 'Enter' && this.state.value != this.props.defaultValue) {
      this.props.onEntryRename(this.props.colname, this.state.value)
    }
  }

  handleDelete = () => {
    this.props.onEntryDelete(this.props.colname)
  }

  render () {
    const { colname, isReadOnly } = this.props
    const { value } = this.state

    // The class names below are used in testing.
    // Changing them would require updating the tests accordingly.
    return (
      <div className='wf-parameter rename-entry' data-column-name={colname}>
        <div className='rename-column'>{colname}</div>
        <div className='rename-container'>
          <input
            className='rename-input'
            type='text'
            value={value}
            onChange={this.handleChange}
            onBlur={this.handleBlur}
            onKeyPress={this.handleKeyPress}
            readOnly={this.props.isReadOnly}
          />
          <button
            className='rename-delete icon-close'
            onClick={this.handleDelete}
            disabled={isReadOnly}
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
    if (!this.props.allColumns) {
      return {}
    } else if (!this.props.entriesJsonString || this.props.entriesJsonString === '{}') {
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

  onEntryRename = (prevName, nextName) => {
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

    this.props.onChange(JSON.stringify(newEntries))
  }

  renderEntries() {
    const entries = this.parsedEntries

    return (this.props.allColumns || [])
      .filter(({ name }) => name in entries)
      .map(({ name }) => (
        <RenameEntry
          key={`${name}_${entries[name]}`}
          colname={name}
          defaultValue={entries[name]}
          onEntryRename={this.onEntryRename}
          onEntryDelete={this.onEntryDelete}
          isReadOnly={this.props.isReadOnly}
        />
      ))
  }

  render() {
    const entries = this.renderEntries()
    return (
      <div className='RenameEntries--container'>{entries}</div>
    )
  }
}
