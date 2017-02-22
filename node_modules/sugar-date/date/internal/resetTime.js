'use strict';

var DateUnitIndexes = require('../var/DateUnitIndexes'),
    setUnitAndLowerToEdge = require('./setUnitAndLowerToEdge');

var HOURS_INDEX = DateUnitIndexes.HOURS_INDEX;

function resetTime(d) {
  return setUnitAndLowerToEdge(d, HOURS_INDEX);
}

module.exports = resetTime;