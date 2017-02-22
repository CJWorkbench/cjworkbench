'use strict';

//ensure DOM environment
require('./testdom')()

var React = require('react')
// to make setState work as per http://stackoverflow.com/a/26872245/2861269
//require('react/lib/ExecutionEnvironment').canUseDOM = true

module.exports = React.createFactory(require('../lib'))
