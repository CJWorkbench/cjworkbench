
import React from 'react';
import { InputGroup, InputGroupButton, Input, Button, ButtonDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap';
import { SketchPicker } from 'react-color';

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
      color: {
        r: '241',
        g: '112',
        b: '19',
        a: '1',
      },
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
    this.setState({ color: color.rgb });
  };

  render() {
    var backgroundColor =  {
      background: `rgba(${ this.state.color.r }, ${ this.state.color.g }, ${ this.state.color.b }, ${ this.state.color.a })`
    }
    console.log(backgroundColor);
    return (
      <div>
        <InputGroup size="lg">
          <InputGroupButton>
            <Button onClick={this.handleClick}>
              <div className="color-picker color" style={backgroundColor} />
            </Button>
            { this.state.displayColorPicker ? <div className="color-picker cover">
              <div className="color-picker popover">
                <SketchPicker color={ this.state.color } onChange={ this.handleChange } />
                <button onClick={ this.handleClose }>OK</button>
                <button onClick={ this.handleCancel } >Cancel</button>
              </div>
            </div> : null }
          </InputGroupButton>
          <InputGroupButton>
            <ButtonDropdown isOpen={this.state.dropdownOpen} toggle={this.toggle} color="primary">
              <DropdownToggle caret>
                Button Dropdown
              </DropdownToggle>
              <DropdownMenu>
                <DropdownItem header>Header</DropdownItem>
                <DropdownItem disabled>Action</DropdownItem>
                <DropdownItem>Another Action</DropdownItem>
                <DropdownItem divider />
                <DropdownItem>Another Action</DropdownItem>
              </DropdownMenu>
            </ButtonDropdown>
          </InputGroupButton>
        </InputGroup>
      </div>
    );
  }
}
