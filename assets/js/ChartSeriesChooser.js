import React from 'react'
import { InputGroup, InputGroupButton, Input, Button, ButtonDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap'
import { BlockPicker } from 'react-color'
import { defaultColors } from './ChartColors'

export default class ChartSeriesChooser extends React.Component {
  constructor(props) {
    super(props);
    this.toggle = this.toggle.bind(this);
    this.handleClick = this.handleClick.bind(this);
    this.handleClose = this.handleClose.bind(this);
    this.handleChange = this.handleChange.bind(this);
    this.handleCancel = this.handleCancel.bind(this);
    this.state = {
      dropdownOpen: false,
      displayColorPicker: false,
      color: this.props.color || null,
      prevColor: null,
    };
  }

  toggle() {
    this.setState({
      dropdownOpen: !this.state.dropdownOpen
    });
  }

  handleClick() {
    var newState = { displayColorPicker: !this.state.displayColorPicker };
    if (!this.state.displayColorPicker) {
      newState.prevColor = this.state.color;
    }
    this.setState(newState);
  };

  handleClose() {
    this.setState({ displayColorPicker: false })
  };

  handleCancel() {
    this.setState({ color: this.state.prevColor, prevColor: null, displayColorPicker: false });
  };

  handleChange(color) {
    this.setState({ color: color.hex });
    this.props.onChange({value:this.props.value, color:color.hex});
  };

  render() {
    var backgroundColor =  {
      background: this.state.color
    }
    return (
      <div>
        <InputGroup size="lg">
          <InputGroupButton>
            <Button onClick={this.handleClick}>
              <div className="color-picker color" style={backgroundColor} />
            </Button>
            { this.state.displayColorPicker ? <div className="color-picker pop-over">
              <div className="color-picker cover" onClick={this.handleClose}/>
              <BlockPicker color={ this.state.color } colors={ this.defaultColors } onChange={ this.handleChange } />
            </div> : null }
          </InputGroupButton>
          <Input type="text" value={this.props.value} readOnly />
          <InputGroupButton onClick={() => this.props.deleteColumn(this.props.value)}>X</InputGroupButton>
        </InputGroup>
      </div>
    );
  }
}
