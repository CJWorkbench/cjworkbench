// UI for a single module within a workflow

import React from 'react'



// ---- WfParameter - a single editable parameter ----

class WfParameter extends React.Component {

  constructor(props) {
    super(props)

    this.type = this.props.p.parameter_spec.type;
    this.name = this.props.p.parameter_spec.name;

    this.blur = this.blur.bind(this);
  }


  // Save value to server when we lose focus (like user changing fields or clicking on render)
  blur(e) {
    var _body = {};
    _body[this.type] = e.target.value;

    fetch('/api/parameters/' + this.props.p.id, {
      method: 'patch',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(_body)
    })
    .catch( (error) => { console.log('Parameter change failed', error); });
  }

  render() {
    switch (this.type) {
      case 'string':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleStringInput' rows='1' defaultValue={this.props.p.string} onBlur={this.blur}/>
          </div>
        );

      case 'number':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleNumberInput' rows='1' defaultValue={this.props.p.number} onBlur={this.blur}/>
          </div>
        );

      case 'text':
        return (
          <div>
            <div>{this.name}:</div>
            <textarea className='wfmoduleTextInput' rows='4' defaultValue={this.props.p.text} onBlur={this.blur}/>
          </div>
        );
    }
  }
}

// ---- WfModule ----

export default class WfModule extends React.Component {

  render() {
    var module = this.props['data-module'];
    var params= this.props['data-params'];
    var paramdivs = params.map((ps, i) => { return <WfParameter p={ps} key={i} /> } )
    return (
      <div {...this.props} className="module-li">
        <h1>{module.name}</h1>
        {paramdivs}
      </div>
    ); 
  } 
}
