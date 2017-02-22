'use strict';

var React   = require('react')
var Toolbar = require('./src')

var Region  = Toolbar.Region

var App = React.createClass({

    render: function() {

        return <div className="App">
                <Toolbar theme={null}>
                    <Region>
                        Export
                    </Region>

                    <Region flex={2}>
                        <Toolbar>
                            <Region align="center">Import from CSV</Region>
                            <Region align="center">Import from Excel</Region>
                        </Toolbar>
                    </Region>

                    <Region>
                        Save
                    </Region>
                </Toolbar>

            </div>
    }
})

React.render(<App />, document.getElementById('content'))