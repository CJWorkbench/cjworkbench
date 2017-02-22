'use strict';

var forEach = require('./forEach'),
    spaceSplit = require('./spaceSplit'),
    classChecks = require('../var/classChecks');

var isString = classChecks.isString;

function collectSimilarMethods(set, fn) {
  var methods = {};
  if (isString(set)) {
    set = spaceSplit(set);
  }
  forEach(set, function(el, i) {
    fn(methods, el, i);
  });
  return methods;
}

module.exports = collectSimilarMethods;