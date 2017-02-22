'use strict';

var DateUnitIndexes = require('../var/DateUnitIndexes'),
    iterateOverDateParams = require('./iterateOverDateParams');

var DAY_INDEX = DateUnitIndexes.DAY_INDEX,
    YEAR_INDEX = DateUnitIndexes.YEAR_INDEX;

function iterateOverHigherDateParams(params, fn) {
  iterateOverDateParams(params, fn, YEAR_INDEX, DAY_INDEX);
}

module.exports = iterateOverHigherDateParams;