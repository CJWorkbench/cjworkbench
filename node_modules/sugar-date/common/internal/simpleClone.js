'use strict';

var simpleMerge = require('./simpleMerge');

function simpleClone(obj) {
  return simpleMerge({}, obj);
}

module.exports = simpleClone;