import React from 'react'
import { InputGroup, InputGroupAddon, Input, Button } from 'reactstrap'
import BlockPicker from 'react-color/lib/Block'
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
    return (
      <React.Fragment>
        <InputGroup size="lg" className="color-picker d-flex align-items-center wf-parameter">
          <InputGroupAddon addonType="prepend">
            <Button onClick={this.handleClick} className="color-picker button color" style={{ background: this.state.color }}>
              <i className="icon-sort-down-vl-gray button-icon color-picker"/>
            </Button>
          </InputGroupAddon>
          <Input bsSize="lg" type="text" value={this.state.label} onChange={this.handleTextChange} />
        </InputGroup>
        { this.state.displayColorPicker ? <div className="color-picker pop-over">
          <div className="color-picker cover" onClick={this.handleClose}/>
          <BlockPicker color={ this.state.color } colors={ defaultColors } onChange={ this.handleChange } triangle="hide" />
        </div> : null }
      </React.Fragment>
    );
  }
}
