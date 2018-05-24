import React from 'react'
import ReactDOM from 'react-dom'
import SimpleChartParameter from './SimpleChart'

import 'bootstrap/dist/css/bootstrap.css'
import '../css/chartbuilder_fonts_colors.css'
import '../css/chartbuilder.css'


ReactDOM.render(
    <div>
      <SimpleChartParameter
        chartType='column'
        renderedSVGClassName='columnchart-svg'
      ></SimpleChartParameter>
    </div>,
    document.getElementById('root')
);
