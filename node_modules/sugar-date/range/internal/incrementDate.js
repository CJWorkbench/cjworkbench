'use strict';

var MULTIPLIERS = require('../var/MULTIPLIERS'),
    callDateSet = require('../../common/internal/callDateSet'),
    callDateGet = require('../../common/internal/callDateGet');

function incrementDate(src, amount, unit) {
  var mult = MULTIPLIERS[unit], d;
  if (mult) {
    d = new Date(src.getTime() + (amount * mult));
  } else {
    d = new Date(src);
    callDateSet(d, unit, callDateGet(src, unit) + amount);
  }
  return d;
}

module.exports = incrementDate;