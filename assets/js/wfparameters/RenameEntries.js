import React from 'react'
import PropTypes from 'prop-types'
import {store, deleteModuleAction} from "../workflow-reducer"

function parseJsonOrEmpty(s) {
  if (s) {
    return JSON.parse(s)
  } else {
    return {}
  }
}

function isEmptyJson(s) {
  return !s || s == '{}'
}

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
      disabled={this.props.isReadOnly}
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
    fetchInputColumns: PropTypes.func.isRequired, // func() => Promise[Array[String]]
    api: PropTypes.shape({
      onParamChanged: PropTypes.func.isRequired,
    }).isRequired,
    entriesJsonString: PropTypes.string.isRequired,
    wfModuleId: PropTypes.number.isRequired,
    inputLastRelevantDeltaId: PropTypes.number,
    paramId: PropTypes.number.isRequired,
    isReadOnly: PropTypes.bool.isRequired
  }

  constructor(props) {
    super(props)

    this.state = {
      entries: parseJsonOrEmpty(this.props.entriesJsonString),
    }
  }

  componentDidUpdate(prevProps) {
    if (prevProps.entriesJsonString !== this.props.entriesJsonString) {
      this.setState({ entries: parseJsonOrEmpty(this.props.entriesJsonString) })
    }
  }

  componentDidMount() {
    if (isEmptyJson(this.props.entriesJsonString)) {
      // This is a brand-new module. Load an initial state from the
      // server, renaming all columns.
      //
      // This `entries` will not be in the Redux store until we write it
      // that'll be the first onColRename/onEntryDelete.
      this.props.fetchInputColumns(this.props.wfModuleId)
        .then(columns => {
          // avoid race: if we've already renamed something, clearly
          // we don't want these values from the server.
          if (!isEmptyJson(this.props.entriesJsonString)) return

          const entries = {}
          for (const colname of columns) {
            entries[colname] = colname
          }
          this.setState({ entries })
        })
    }
  }

  onColRename = (prevName, nextName) => {
    var newEntries = Object.assign({}, this.state.entries)
    newEntries[prevName] = nextName
    this.props.api.onParamChanged(this.props.paramId, {value: JSON.stringify(newEntries)})
  }

  onEntryDelete = (prevName) => {
    var newEntries = Object.assign({}, this.state.entries)
    if (prevName in newEntries) {
      delete newEntries[prevName]
      if (Object.keys(newEntries).length == 0) {
        // I am intermixing actions and API calls here because somehow other combinations
        // of them do not work
        store.dispatch(deleteModuleAction(this.props.wfModuleId))
      } else {
        this.props.api.onParamChanged(this.props.paramId, {value: JSON.stringify(newEntries)})
      }
    }
  }

  renderEntries() {
    var entries = []
    for(let col in this.state.entries) {
      entries.push(
        <RenameEntry
        key={col}
        colname={col}
        newColname={this.state.entries[col]}
        onColRename={this.onColRename}
        onEntryDelete={this.onEntryDelete}
        isReadOnly={this.props.isReadOnly}
        />
      )
    }
    return entries
  }

  render() {
    const entries = this.renderEntries()
    return (
      <div className="RenameEntries--container">{entries}</div>
    )
  }
}
