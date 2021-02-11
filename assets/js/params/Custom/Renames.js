import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import { generateFieldId } from '../util'

export class RenameEntry extends PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    colname: PropTypes.string.isRequired,
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired, // func(colname, newValue) => undefined
    onDelete: PropTypes.func.isRequired,
    isReadOnly: PropTypes.bool.isRequired
  }

  handleChange = ev => {
    const { onChange, colname } = this.props
    onChange(colname, ev.target.value)
  }

  handleBlur = () => {
    if (this.state.value !== this.props.defaultValue) {
      this.props.onEntryRename(this.props.colname, this.state.value)
    }
  }

  handleDelete = () => {
    this.props.onDelete(this.props.colname)
  }

  render () {
    const { stepId, name, colname, isReadOnly, value } = this.props

    const fieldId = generateFieldId(stepId, name)

    // The class names below are used in testing.
    // Changing them would require updating the tests accordingly.
    return (
      <div className='rename-entry' data-column-name={colname}>
        <label htmlFor={fieldId}>{colname}</label>
        <div className='rename-container'>
          <input
            className='rename-input'
            type='text'
            value={value}
            id={fieldId}
            onChange={this.handleChange}
            readOnly={isReadOnly}
          />
          <button
            type='button'
            className='rename-delete icon-close'
            onClick={this.handleDelete}
            disabled={isReadOnly}
          />
        </div>
      </div>
    )
  }
}

export default class RenameEntries extends PureComponent {
  static propTypes = {
    inputColumns: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired
      })
    ), // or null for unknown list (loading or stalled)
    value: PropTypes.object.isRequired,
    onChange: PropTypes.func.isRequired, // onChange({ old: new, ...}) => undefined
    isReadOnly: PropTypes.bool.isRequired
  }

  get saneValue () {
    const { inputColumns, value } = this.props

    if (!inputColumns || !value) {
      return {}
    } else if (Object.keys(value).length === 0) {
      // No renames? Then we probably just created the module manually. Its default
      // value should be _everything_.
      const ret = {}
      for (const column of inputColumns) {
        ret[column.name] = column.name
      }
      return ret
    } else {
      return value
    }
  }

  handleChangeEntry = (prevName, nextName) => {
    const oldEntries = this.saneValue
    if (oldEntries[prevName] === nextName) return // no-op

    const newEntries = {
      ...oldEntries,
      [prevName]: nextName
    }
    this.props.onChange(newEntries)
  }

  handleDeleteEntry = prevName => {
    const oldEntries = { ...this.saneValue }
    if (!(prevName in oldEntries)) return // no-op

    const newEntries = { ...oldEntries }
    delete newEntries[prevName]

    this.props.onChange(newEntries)
  }

  renderEntries () {
    const entries = this.saneValue
    const fieldName = this.props.name
    const { stepId, isReadOnly } = this.props

    return (this.props.inputColumns || [])
      .filter(({ name }) => name in entries)
      .map(({ name }) => (
        <RenameEntry
          stepId={stepId}
          key={name}
          name={`${fieldName}[${name}]`}
          colname={name}
          value={entries[name]}
          onChange={this.handleChangeEntry}
          onDelete={this.handleDeleteEntry}
          isReadOnly={isReadOnly}
        />
      ))
  }

  render () {
    const entries = this.renderEntries()
    return <>{entries}</>
  }
}
