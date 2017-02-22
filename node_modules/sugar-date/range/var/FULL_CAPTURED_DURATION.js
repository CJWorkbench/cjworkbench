'use strict';

var DURATION_UNITS = require('./DURATION_UNITS');

module.exports = '((?:\\d+)?\\s*(?:' + DURATION_UNITS + '))s?';