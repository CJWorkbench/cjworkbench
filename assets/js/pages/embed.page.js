import ReactDOM from "react-dom";
import React from 'react'
import Embed from "../Embed"

require('bootstrap/dist/css/bootstrap.css');
require('../../css/style.scss');

ReactDOM.render(
    <Embed
      workflow={window.initState.workflow}
      wf_module={window.initState.wf_module}
    />,
    document.getElementById('root')
);