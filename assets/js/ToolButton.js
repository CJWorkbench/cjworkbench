// Simple toolbar button

import React from 'react';

// Props:
// text   -- what the button says
// click  -- onClick callback
export default class ToolButton extends React.Component {
   render() {
     return (
       <button className="toolbutton" onClick={this.props.click}>
         {this.props.text}
       </button>
     );
   }
 }
