'use strict';

var parseKeys = require('parse-keys');
var assign = require('object-assign');

module.exports = assign({
  PORT: 9090
}, parseKeys(process.env, ['HOT', 'NODE_ENV']))