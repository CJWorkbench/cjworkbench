'use strict';

var DURATION_REG = require('../var/DURATION_REG'),
    classChecks = require('../../common/var/classChecks'),
    simpleCapitalize = require('../../common/internal/simpleCapitalize');

var isNumber = classChecks.isNumber;

function getDateIncrementObject(amt) {
  var match, val, unit;
  if (isNumber(amt)) {
    return [amt, 'Milliseconds'];
  }
  match = amt.match(DURATION_REG);
  val = +match[1] || 1;
  unit = simpleCapitalize(match[2].toLowerCase());
  if (unit.match(/hour|minute|second/i)) {
    unit += 's';
  } else if (unit === 'Year') {
    unit = 'FullYear';
  } else if (unit === 'Week') {
    unit = 'Date';
    val *= 7;
  } else if (unit === 'Day') {
    unit = 'Date';
  }
  return [val, unit];
}

module.exports = getDateIncrementObject;