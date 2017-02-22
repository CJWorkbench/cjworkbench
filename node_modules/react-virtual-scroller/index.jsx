'use strict';

import React from 'react';
import { render } from 'react-dom'
import Scroller from './src'

require('./index.styl')
require('react-load-mask/index.styl')

const App = class extends React.Component {

	render(){
		return <div>
			<Scroller
				style={{border: '1px solid red', width: 400}}
				height={500}
				xsloading={true}
				scrollHeight={10000}
				scrollWidth={1200}
				onVerticalScroll={this.onVerticalScroll}
			>
			</Scroller>
		</div>
	}

	onVerticalScroll(scrollTop) {
		console.log(scrollTop)
	}
}

render(<App />, document.getElementById('content'))