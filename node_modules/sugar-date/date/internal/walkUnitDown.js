'use strict';

var DateUnits = require('../var/DateUnits'),
    getLowerUnitIndex = require('./getLowerUnitIndex');

function walkUnitDown(unitIndex, fn) {
  while (unitIndex >= 0) {
    if (fn(DateUnits[unitIndex], unitIndex) === false) {
      break;
    }
    unitIndex = getLowerUnitIndex(unitIndex);
  }
}

module.exports = walkUnitDown;