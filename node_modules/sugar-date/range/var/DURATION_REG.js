'use strict';

var DURATION_UNITS = require('./DURATION_UNITS');

module.exports = RegExp('(\\d+)?\\s*('+ DURATION_UNITS +')s?', 'i');