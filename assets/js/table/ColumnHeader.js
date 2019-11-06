import React from 'react'
import PropTypes from 'prop-types'
import ColumnContextMenu from './ColumnContextMenu'
import { connect } from 'react-redux'
import { idxToLetter } from '../utils'
import { updateTableAction } from './UpdateTableAction'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const columnTypeDisplay = {
  text: t('js.table.ColumnHeader.types.text')`text`,
  number: t('js.table.ColumnHeader.types.number')`number`,
  datetime: t('js.table.ColumnHeader.types.dateAndtime')`date & time`
}

class ReorderColumnDropZone extends React.PureComponent {
  static propTypes = {
    leftOrRight: PropTypes.oneOf(['left', 'right']).isRequired,
    fromIndex: PropTypes.number.isRequired,
    toIndex: PropTypes.number.isRequired,
    onDropColumnIndexAtIndex: PropTypes.func.isRequired // func(fromIndex, toIndex) => undefined
  }

  constructor (props) {
    super(props)

    this.state = {
      isDragHover: false
    }
  }

  handleDragEnter = (ev) => {
    this.setState({
      isDragHover: true
    })
  }

  handleDragLeave = (ev) => {
    this.setState({
      isDragHover: false
    })
  }

  handleDragOver = (ev) => {
    ev.preventDefault() // allow drop by preventing the default, which is "no drop"
  }

  handleDrop = (ev) => {
    const { fromIndex, toIndex, onDropColumnIndexAtIndex } = this.props
    onDropColumnIndexAtIndex(fromIndex, toIndex)
  }

  render () {
    let className = 'column-reorder-drop-zone'
    className += ' align-' + this.props.leftOrRight
    if (this.state.isDragHover) className += ' drag-hover'

    return (
      <div
        className={className}
        onDragEnter={this.handleDragEnter}
        onDragLeave={this.handleDragLeave}
        onDragOver={this.handleDragOver}
        onDrop={this.handleDrop}
      />
    )
  }
}

export const EditableColumnName = withI18n()(class EditableColumnName extends React.Component {
  static propTypes = {
    columnKey: PropTypes.string.isRequired,
    columnType: PropTypes.string.isRequired,
    onRename: PropTypes.func.isRequired,
    isReadOnly: PropTypes.bool.isRequired
  }

  state = {
    newName: this.props.columnKey,
    editMode: false
  }

  inputRef = React.createRef()

  componentDidUpdate (_, prevState) {
    if (!prevState.editMode && this.state.editMode) {
      const input = this.inputRef.current
      if (input) {
        input.focus()
        input.select()
      }
    }
  }

  handleEnterEditMode = () => {
    if (!this.props.isReadOnly) {
      this.setState({ editMode: true })
    }
  }

  exitEditMode () {
    this.setState({ editMode: false })
  }

  handleInputChange = (ev) => {
    this.setState({ newName: ev.target.value })
  }

  handleInputCommit = () => {
    this.setState({
      editMode: false
    })
    if (this.state.newName !== this.props.columnKey) {
      this.props.onRename({
        prevName: this.props.columnKey,
        newName: this.state.newName
      })
    }
  }

  handleInputBlur = () => {
    this.handleInputCommit()
  }

  handleInputKeyDown = (ev) => {
    // Changed to keyDown as esc does not fire keyPress
    if (ev.key === 'Enter') {
      this.handleInputCommit()
    } else if (ev.key === 'Escape') {
      this.setState({ newName: this.props.columnKey })
      this.exitEditMode()
    }
  }

  render () {
    if (this.state.editMode) {
      // The class name 'column-key-input' is used in
      // the code to prevent dragging while editing,
      // please keep it as-is.
      return (
        <input
          name='new-column-key'
          type='prout'
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
          className='column-key'
          onClick={this.handleEnterEditMode}
        >
          <div className='value'>
            {this.state.newName}
          </div>
          <div className='column-type'>
            {this.props.i18n._(columnTypeDisplay[this.props.columnType])}
          </div>
        </span>
      )
    }
  }
})

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
    dispatchTableAction: PropTypes.func.isRequired // func(wfModuleId, moduleIdName, forceNewModule, params)
  }

  inputRef = React.createRef()

  state = {
    isHovered: false,
    newName: this.props.columnKey
  }

  handleClickAction = (idName, forceNewModule, params) => {
    params = {
      ...params,
      columnKey: this.props.columnKey
    }

    this.props.dispatchTableAction(this.props.wfModuleId, idName, forceNewModule, params)
  }

  startRename = () => {
    this.inputRef.current.handleEnterEditMode()
  }

  handleRename = ({ prevName, newName }) => {
    this.props.dispatchTableAction(this.props.wfModuleId, 'renamecolumns', false, { prevName, newName })
  }

  handleMouseEnter = () => {
    this.setState({ isHovered: true })
  }

  handleMouseLeave = () => {
    this.setState({ isHovered: false })
  }

  handleDragStart = (ev) => {
    if (this.props.isReadOnly) {
      ev.preventDefault()
      return
    }

    if (ev.target.classList.contains('column-key-input')) {
      ev.preventDefault()
      return
    }

    this.props.onDragStartColumnIndex(this.props.index)

    ev.dataTransfer.effectAllowed = ['move']
    ev.dataTransfer.dropEffect = 'move'
    ev.dataTransfer.setData('text/plain', this.props.columnKey)
  }

  renderColumnMenu () {
    if (this.props.isReadOnly) {
      return null
    }

    return (
      <ColumnContextMenu
        columnType={this.props.columnType}
        renameColumn={this.startRename}
        onClickAction={this.handleClickAction}
      />
    )
  }

  render () {
    const {
      columnKey,
      columnType,
      index,
      draggingColumnIndex
    } = this.props

    const columnMenuSection = this.renderColumnMenu()

    const maybeDropZone = (leftOrRight, toIndex) => {
      if (draggingColumnIndex === null || draggingColumnIndex === undefined) return null
      if (draggingColumnIndex === toIndex) return null

      // Also, dragging to fromIndex+1 is a no-op
      if (draggingColumnIndex === toIndex - 1) return null

      return (
        <ReorderColumnDropZone
          leftOrRight={leftOrRight}
          fromIndex={draggingColumnIndex}
          toIndex={toIndex}
          onDropColumnIndexAtIndex={this.props.onDropColumnIndexAtIndex}
        />
      )
    }

    const draggingClass = (draggingColumnIndex === index) ? 'dragging' : ''

    return (
      <>
        <div
          className='column-letter'
          draggable
          onDragStart={this.handleDragStart}
          onDragEnd={this.props.onDragEnd}
        >
          {idxToLetter(this.props.index)}
        </div>
        <div
          className={`data-grid-column-header ${draggingClass}`}
          onMouseEnter={this.handleMouseEnter}
          onMouseLeave={this.handleMouseLeave}
        >
          {maybeDropZone('left', index)}
          <EditableColumnName
            columnKey={columnKey}
            columnType={columnType}
            onRename={this.handleRename}
            isReadOnly={this.props.isReadOnly}
            ref={this.inputRef}
          />
          {columnMenuSection}
          {maybeDropZone('right', index + 1)}
        </div>
      </>
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
