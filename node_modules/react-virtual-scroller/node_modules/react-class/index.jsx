'use strict';

var React = require('react');
var Component = require('./src');

class App extends Component {

  onClick(event){
    console.log(this.p);
  }

  render(){
    var props = this.p = this.prepareProps(this.props)

    return <div {...props} onClick={this.onClick}>
      Hello, please click me
    </div>
  }
}

App.defaultProps = {
  defaultStyle: {
    border: '1px solid red'
  },
  defaultClassName: 'app'
}

React.render(<App className="xxx" style={{color: 'blue'}} />, document.getElementById('content'))