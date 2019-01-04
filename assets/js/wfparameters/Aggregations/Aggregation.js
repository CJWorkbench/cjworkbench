import React from 'react'
import PropTypes from 'prop-types'
import Operation from './Operation'
import ColumnParam from '../ColumnParam'

export default class Aggregation extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired, // for <input name=...>
    index: PropTypes.number.isRequired,
    allColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if unknown
    onChange: PropTypes.func.isRequired, // func(index, value) => undefined
    onDelete: PropTypes.func, // func(index) => undefined, or null if delete not allowed
    operation: PropTypes.oneOf(['size', 'nunique', 'sum', 'mean', 'min', 'max', 'first']).isRequired,
    colname: PropTypes.string.isRequired,
    outname: PropTypes.string.isRequired // may be empty
  }

  outnameRef = React.createRef()

  onChangeOperation = (ev) => {
    const { colname, index, outname, onChange } = this.props
    onChange(index, { colname, outname, operation: ev.target.value })
  }

  onChangeColname = (colnameOrNull) => {
    const { outname, operation, index, onChange } = this.props
    onChange(index, { outname, operation, colname: (colnameOrNull || '') })
  }

  onChangeOutname = (ev) => {
    // Wow, it's hard to just grab a 'onChange' event.
    //
    // This is a hack. TODO make <WfModule> behave like a <form>, with One
    // Submit Button To Rule Them All. At that point, we can turn `outname`
    // into a controlled component. (In the meantime, every `onChange`
    // triggers an HTTP request: _not_ an option.)
    if (ev.nativeEvent) {
      // This is a React SyntheticEvent which is fired on HTML 'input' event.
      // Ignore it.
      return
    }

    // Okay, this is an HTML 'change' event.
    const { colname, operation, index, onChange } = this.props
    onChange(index, { colname, operation, outname: ev.target.value })
  }

  onClickDelete = (ev) => {
    const { index, onDelete } = this.props
    onDelete(index)
  }

  componentDidMount () {
    this.outnameRef.current.addEventListener('change', this.onChangeOutname)
  }

  componentWillUnmount () {
    this.outnameRef.current.removeEventListener('change', this.onChangeOutname)
  }

  render () {
    const { name, index, onDelete, operation, colname, outname, allColumns, isReadOnly } = this.props

    return (
      <li className='aggregation'>
        <Operation
          isReadOnly={isReadOnly}
          name={`${name}[${index}][operation]`}
          value={operation}
          onChange={this.onChangeOperation}
        />
        {operation === 'size' ? null : (
          <ColumnParam
            name={`${name}[${index}[colname]`}
            value={colname}
            prompt='Select a column'
            isReadOnly={isReadOnly}
            allColumns={allColumns}
            onChange={this.onChangeColname}
          />
        )}
        <label className='outname'>
          <span className='name'>Name</span>
          <input
            className='outname' 
            ref={this.outnameRef}
            name={`${name}[${index}[outname]`}
            defaultValue={outname}
            onChange={this.onChangeOutname}
            placeholder='(default)'
          />
        </label>
        {(onDelete && !isReadOnly) ? (
          <div className='delete'>
            <button
              className='delete'
              onClick={this.onClickDelete}
            >
              <i className='icon-close' /> Remove
            </button>
          </div>
        ) : null}
      </li>
    )
  }
}
