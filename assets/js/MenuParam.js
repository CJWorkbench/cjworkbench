// Simple wrapper over HTML <select>
import React from 'react';

export default class MenuParam extends React.Component {
  constructor(props) {
    super(props);
    this.onChange = this.onChange.bind(this);
    this.state = {
      selectedIdx: this.props.selectedIdx
    };
  }
/*
  componentWillReceiveProps(newProps) {
    if (this.state.selectedIdx != newProps.selectedIdx)
      this.setState({selectedIdx :  newProps.selectedIdx})
  }
*/
  onChange(evt) {
    var idx =  evt.target.value;
    this.setState({selectedIdx: idx });
    this.props.onChange(idx);
  }

  render() {
    var items = this.props.items.split('|');
    var itemDivs = items.map( (name, idx) => {
        return <option key={idx} value={idx}>{name}</option>;
    });

    return (
      <div>
        <label className='mr-1'>{this.props.name}:</label>
        <select className="custom-select" value={this.state.selectedIdx} onChange={this.onChange}>
          {itemDivs}
        </select>
      </div>
    );
  }
}

MenuParam.propTypes = {
  name:         React.PropTypes.string,
  items:        React.PropTypes.string,  // like 'Apple|Banana|Kitten'
  selectedIdx:  React.PropTypes.number,
  onChange:     React.PropTypes.func     // called with index of selected item
};
