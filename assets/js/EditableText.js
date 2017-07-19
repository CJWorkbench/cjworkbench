import React from 'react'

export default class EditableText extends React.Component {
  constructor(props) {
    super(props);
    this.toggleEditing = this.toggleEditing.bind(this);
    this.saveChanges = this.saveChanges.bind(this);
    this.onChange = this.onChange.bind(this);
    this.onBlur = this.onBlur.bind(this);
    this.onKeyDown = this.onKeyDown.bind(this);
    this.state = {
      editing: false,

      value: this.props.value,
      oldValue: this.props.value,
    }
  }

  toggleEditing() {
    this.setState({editing: !this.state.editing});
  }

  saveChanges() {
    return this.props.save(this.props.value);
  }

  cancelChanges() {
    this.setState({value:this.state.oldValue});
  }

  onChange(event) {
    this.setState({value:event.target.value});
  }

  onBlur(event) {
    this.saveChanges();
    this.toggleEditing();
  }

  onKeyDown(event) {
    if (event.keyCode == 13) {
      this.saveChanges();
      this.toggleEditing();
    }

    if (event.keyCode == 27) {
      this.cancelChanges();
      this.toggleEditing();
    }
  }

  componentDidUpdate() {
    if (this.state.editing == true) {
      document.addEventListener('keydown', this.onKeyDown);
      this.editInput.focus();
    }

    if (this.state.editing == false) {
      document.removeEventListener('keydown', this.onKeyDown);
      this.state.oldValue = this.state.value;
    }
  }

  render() {
    if (this.state.editing == true) {
      return <input
        className={this.props.editClass}
        onBlur={this.onBlur}
        type="text"
        ref={(input) => { this.editInput = input }}
        value={this.state.value}
        onChange={this.onChange}
      />
    }
    return <h4 onClick={this.toggleEditing}>{this.state.value}</h4>;
  }
}
