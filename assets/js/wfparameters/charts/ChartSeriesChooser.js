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
    this.handleTextChange = this.handleTextChange.bind(this);
  }

  componentWillMount() {
    this.state = {
      dropdownOpen: false,
      displayColorPicker: false,
      color: defaultColors[this.props.colorIndex],
      prevColor: null,
      label: this.props.label
    };
  }

  componentWillReceiveProps(nextProps) {
    var nextState = {
      color: defaultColors[nextProps.colorIndex]
    };

    if (this.state.label !== '') {
      nextState.label = nextProps.label;
    }

    this.setState(nextState);
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
    var colorIndex = defaultColors.indexOf(color.hex.toUpperCase());
    this.setState({ color: color.hex });
    this.props.onChange(this.props.index, {colorIndex:colorIndex});
  };

  handleTextChange(e) {
    this.setState({
      label: e.target.value
    });
    // If an empty string is saved Chartbuilder resets to the default value
    if (e.target.value !== '') {
      this.props.onChange(this.props.index, {label:e.target.value.replace(/^\s+/g, '')});
    } else {
      this.props.onChange(this.props.index, {label:' '});
    }
  }

  render() {
    var backgroundColor =  {
      background: this.state.color
    }
    return (
      <div className="color-picker d-flex parameter-margin">
        <div className="">
          <InputGroup size="lg">
            <InputGroupButton>
              <Button onClick={this.handleClick} className="color-picker button">
                <div className="color-picker color" style={backgroundColor}>
                  <div className="icon-sort-down-vl-gray button-icon color-picker" style={{position:'relative'}} />
                </div>
              </Button>
              { this.state.displayColorPicker ? <div className="color-picker pop-over">
                <div className="color-picker cover" onClick={this.handleClose}/>
                <BlockPicker color={ this.state.color } colors={ defaultColors } onChange={ this.handleChange } triangle="hide" />
              </div> : null }
            </InputGroupButton>
          </InputGroup>
        </div>

        <div className="chart-label">
          <Input size="lg" type="text" value={this.state.label} onChange={this.handleTextChange} />
        </div>
      </div>
    );
  }
}
