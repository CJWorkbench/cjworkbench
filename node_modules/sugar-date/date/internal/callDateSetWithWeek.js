'use strict';

var callDateSet = require('../../common/internal/callDateSet'),
    setISOWeekNumber = require('./setISOWeekNumber');

function callDateSetWithWeek(d, method, value, safe) {
  if (method === 'ISOWeek') {
    setISOWeekNumber(d, value);
  } else {
    callDateSet(d, method, value, safe);
  }
}

module.exports = callDateSetWithWeek;