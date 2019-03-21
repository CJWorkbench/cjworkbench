import React from 'react'
import PropTypes from 'prop-types'
import ColumnContextMenu from './ColumnContextMenu'
import { connect } from 'react-redux'
import { idxToLetter } from '../utils'
import { updateTableAction } from './UpdateTableAction'

const columnTypeDisplay = {
  'text': 'text',
  'number': 'number',
  'datetime': 'date & time'
}

class ReorderColumnDropZone extends React.PureComponent {
  static propTypes = {
    leftOrRight: PropTypes.oneOf([ 'left', 'right' ]).isRequired,
    fromIndex: PropTypes.number.isRequired,
    toIndex: PropTypes.number.isRequired,
    onDropColumnIndexAtIndex: PropTypes.func.isRequired, // func(fromIndex, toIndex) => undefined
  }

  constructor(props) {
    super(props)

    this.state = {
      isDragHover: false,
    }
  }

  onDragEnter = (ev) => {
    this.setState({
      isDragHover: true,
    })
  }

  onDragLeave = (ev) => {
    this.setState({
      isDragHover: false,
    })
  }

  onDragOver = (ev) => {
    ev.preventDefault() // allow drop by preventing the default, which is "no drop"
  }

  onDrop = (ev) => {
    const { fromIndex, toIndex, onDropColumnIndexAtIndex } = this.props
    onDropColumnIndexAtIndex(fromIndex, toIndex)
  }

  render() {
    let className = 'column-reorder-drop-zone'
    className += ' align-' + this.props.leftOrRight
    if (this.state.isDragHover) className += ' drag-hover'

    return (
      <div
        className={className}
        onDragEnter={this.onDragEnter}
        onDragLeave={this.onDragLeave}
        onDragOver={this.onDragOver}
        onDrop={this.onDrop}
        >
      </div>
    )
  }
}

export class EditableColumnName extends React.Component {
  static propTypes = {
    columnKey: PropTypes.string.isRequired,
    columnType: PropTypes.string.isRequired,
    onRename: PropTypes.func.isRequired,
    isReadOnly: PropTypes.bool.isRequired
  }

  constructor(props) {
    super(props);

    this.state = {
      newName: props.columnKey,
      editMode: false,
    }

    this.inputRef = React.createRef();

    this.enterEditMode = this.enterEditMode.bind(this);
    this.handleInputChange = this.handleInputChange.bind(this);
    this.handleInputBlur = this.handleInputBlur.bind(this);
    this.handleInputKeyDown = this.handleInputKeyDown.bind(this);
  }

  componentDidUpdate(_, prevState) {
    if (!prevState.editMode && this.state.editMode) {
      const input = this.inputRef.current;
      if (input) {
        input.focus();
        input.select();
      }
    }
  }

  enterEditMode() {
    if(!this.props.isReadOnly) {
      this.setState({editMode: true});
    }
  }

  exitEditMode() {
    this.setState({editMode: false});
  }

  handleInputChange(event) {
    this.setState({newName: event.target.value});
  }

  handleInputCommit() {
    this.setState({
        editMode: false
    })
    if(this.state.newName != this.props.columnKey) {
      this.props.onRename({
        prevName: this.props.columnKey,
        newName: this.state.newName
      })
    }
  }

  handleInputBlur() {
    this.handleInputCommit();
  }

  handleInputKeyDown(event) {
    // Changed to keyDown as esc does not fire keyPress
    if(event.key == 'Enter') {
      this.handleInputCommit();
    } else if (event.key == 'Escape') {
      this.setState({newName: this.props.columnKey});
      this.exitEditMode();
    }
  }

  render() {
    if(this.state.editMode) {
      // The class name 'column-key-input' is used in
      // the code to prevent dragging while editing,
      // please keep it as-is.
      return (
        <input
          name='new-column-key'
          type='text'
          ref={this.inputRef}
          value={this.state.newName}
          onChange={this.handleInputChange}
          onBlur={this.handleInputBlur}
          onKeyDown={this.handleInputKeyDown}
        />
      )
    } else {
      return (
        <span
          className={'column-key'}
          onClick={this.enterEditMode}
        >
          <div className='value'>
            {this.state.newName}
          </div>
          <div className={'column-type'}>
            {columnTypeDisplay[this.props.columnType]}
          </div>
        </span>
      )
    }
  }
}

// Sort arrows, A-Z letter identifiers
export class ColumnHeader extends React.PureComponent {
  static propTypes = {
    wfModuleId: PropTypes.number,
    columnKey: PropTypes.string.isRequired,
    columnType: PropTypes.string.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    index: PropTypes.number.isRequired,
    onDragStartColumnIndex: PropTypes.func.isRequired, // func(index) => undefined
    onDragEnd: PropTypes.func.isRequired, // func() => undefined
    onDropColumnIndexAtIndex: PropTypes.func.isRequired, // func(from, to) => undefined
    draggingColumnIndex: PropTypes.number, // if set, we are dragging
    dispatchTableAction: PropTypes.func.isRequired, // func(wfModuleId, moduleIdName, forceNewModule, params)
  }

  inputRef = React.createRef()

  state = {
    isHovered: false,
    newName: this.props.columnKey
  }

  onClickAction = (idName, forceNewModule, params) => {
    params = {
      ...params,
      columnKey: this.props.columnKey
    }

    this.props.dispatchTableAction(this.props.wfModuleId, idName, forceNewModule, params)
  }

  startRename = () => {
    this.inputRef.current.enterEditMode()
  }

  completeRename = ({ prevName, newName }) => {
    this.props.dispatchTableAction(this.props.wfModuleId, 'renamecolumns', false, { prevName, newName })
  }

  onMouseEnter = () => {
    this.setState({isHovered: true});
  }

  onMouseLeave = () => {
    this.setState({isHovered: false});
  }

  onDragStart = (ev) => {
    if(this.props.isReadOnly) {
      ev.preventDefault();
      return;
    }

    if(ev.target.classList.contains('column-key-input')) {
      ev.preventDefault();
      return;
    }

    this.props.onDragStartColumnIndex(this.props.index)

    ev.dataTransfer.effectAllowed = [ 'move' ]
    ev.dataTransfer.dropEffect = 'move'
    ev.dataTransfer.setData('text/plain', this.props.columnKey)
  }

  onDragEnd = () => {
    this.props.onDragEnd()
  }

  renderColumnMenu() {
    if(this.props.isReadOnly) {
      return null;
    }

    return (
      <ColumnContextMenu
        columnType={this.props.columnType}
        renameColumn={this.startRename}
        onClickAction={this.onClickAction}
      />
    )
  }

  renderLetter() {
    return (
      // The 'column-letter' class name is used in the test so please be careful with it
      <div className='column-letter'>
        {idxToLetter(this.props.index)}
      </div>
    );
  }

  render() {
    const {
      columnKey,
      columnType,
      index,
      onDropColumnIndexAtIndex,
      draggingColumnIndex,
    } = this.props

    const columnMenuSection = this.renderColumnMenu();
    const letterSection = this.renderLetter();

    function maybeDropZone(leftOrRight, toIndex) {
      if (draggingColumnIndex === null || draggingColumnIndex === undefined) return null
      if (draggingColumnIndex === toIndex) return null

      // Also, dragging to fromIndex+1 is a no-op
      if (draggingColumnIndex === toIndex - 1) return null

      return (
        <ReorderColumnDropZone
          leftOrRight={leftOrRight}
          fromIndex={draggingColumnIndex}
          toIndex={toIndex}
          onDropColumnIndexAtIndex={onDropColumnIndexAtIndex}
        />
      )
    }

    const draggingClass = (draggingColumnIndex === index) ? 'dragging' : ''

    return (
      <React.Fragment>
        {letterSection}
        <div
          className={`data-grid-column-header ${draggingClass}`}
          onMouseEnter={this.onMouseEnter}
          onMouseLeave={this.onMouseLeave}
          draggable={true}
          onDragStart={this.onDragStart}
          onDragEnd={this.onDragEnd}
          >
          {maybeDropZone('left', index)}
          <EditableColumnName
            columnKey={columnKey}
            columnType={columnType}
            onRename={this.completeRename}
            isReadOnly={this.props.isReadOnly}
            ref={this.inputRef}
          />
          {columnMenuSection}
          {maybeDropZone('right', index + 1)}
        </div>
      </React.Fragment>
    )
  }
}

function mapStateToProps () {
  return {}
}

function mapDispatchToProps (dispatch) {
  return {
    dispatchTableAction: (...args) => dispatch(updateTableAction(...args))
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(ColumnHeader)
