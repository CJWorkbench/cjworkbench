var TangleText = require('../'),
  React = require('react'),
  ReactDOM = require('react-dom');

var Example = React.createClass({
  getInitialState: function() {
    return { value: 0, valueTwo: 0 };
  },
  onChange: function(value) {
    console.log('onChange one', value);
    this.setState({ value: value });
  },
  onInput: function(value) {
    console.log('onInput one', value);
  },
  onChangeTwo: function(value) {
    this.setState({ valueTwo: value });
  },
  render: function() {
    /* jshint ignore:start */
    return (
      <div>
        <div className='clearfix pad1 keyline-bottom'>
          <div className='col4'>
            <TangleText value={this.state.valueTwo} onInput={this.onInput} onChange={this.onChangeTwo} />
            <TangleText value={this.state.value} onChange={this.onChange}
              min={0} max={1} step={0.02} />
          </div>
          <div className='col8'>
            Default settings, no minimum, maximum, or step.
          </div>
        </div>
      </div>
    );
    /* jshint ignore:end */
  }
});

ReactDOM.render(<Example />, document.getElementById('app'));
