'use strict';

var DateUnitIndexes = require('../var/DateUnitIndexes'),
    isDefined = require('../../common/internal/isDefined'),
    walkUnitDown = require('./walkUnitDown');

var YEAR_INDEX = DateUnitIndexes.YEAR_INDEX;

function collectDateParamsFromArguments(args) {
  var params = {}, index = 0;
  walkUnitDown(YEAR_INDEX, function(unit) {
    var arg = args[index++];
    if (isDefined(arg)) {
      params[unit.name] = arg;
    }
  });
  return params;
}

module.exports = collectDateParamsFromArguments;