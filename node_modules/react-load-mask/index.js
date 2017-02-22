import './style/index.scss'

import React from 'react'
import { render } from 'react-dom'

import LoadMask from './src'

var VISIBLE = true

class App extends React.Component {

  render(){
    return <div style={{position: 'absolute', width: '100%', height: '100%', left: 0, top: 0}}>
      <LoadMask xsize={20} visible={VISIBLE} onMouseDown={this.handleMouseDown.bind(this)}/>
      </div>
  }

  handleMouseDown(){
    VISIBLE = !VISIBLE
    this.setState({})
  }
}

render(<App />, document.getElementById('content'))
