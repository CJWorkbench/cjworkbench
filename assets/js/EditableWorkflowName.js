import { createRef, Component } from 'react'
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { setWorkflowNameAction } from './workflow-reducer'

export class EditableWorkflowName extends Component {
  static propTypes = {
    value: PropTypes.string,
    setWorkflowName: PropTypes.func.isRequired, // func(newName) => undefined
    isReadOnly: PropTypes.bool.isRequired
  }

  inputRef = createRef()

  state = {
    value: null // non-null only when editing
  }

  handleChange = (ev) => {
    this.setState({ value: ev.target.value })
  }

  handleKeyDown = (ev) => {
    if (ev.key === 'Enter') {
      ev.preventDefault() // [2018-12-13, adamhooper] why?
      this.inputRef.current.blur() // Blur event will trigger save
    } else if (ev.key === 'Escape') {
      this.setState({ value: null })
      this.inputRef.current.blur() // Blur event _won't_ trigger save
    }
  }

  handleBlur = () => {
    // If we got here by pressing Escape, we don't want to save the new value;
    // but the `value: null` we just wrote with this.setState() hasn't been
    // committed yet (because we're in the same event handler). So use the
    // callback type of setState() to pick up on the change.
    //
    // Other way value could be null: if we focused but didn't edit
    this.setState((state, props) => {
      if (state.value !== null) {
        props.setWorkflowName(state.value)
      }
      return { value: null } // stop editing
    })
  }

  render () {
    return (
      <div className='editable-title--container'>
        {this.props.isReadOnly
          ? (<span className='editable-title--field'>{this.props.value}</span>)
          : (
            <input
              type='text'
              name='name'
              ref={this.inputRef}
              className='editable-title--field'
              value={this.state.value === null ? this.props.value : this.state.value}
              onChange={this.handleChange}
              onBlur={this.handleBlur}
              onKeyDown={this.handleKeyDown}
            />
          )}
      </div>
    )
  }
}

const mapStateToProps = (state) => {
  return {
    value: state.workflow.name
  }
}

const mapDispatchToProps = {
  setWorkflowName: setWorkflowNameAction
}

export default connect(mapStateToProps, mapDispatchToProps)(EditableWorkflowName)
