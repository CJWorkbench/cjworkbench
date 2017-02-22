'use strict';

var setWeekday = require('./setWeekday'),
    getWeekday = require('./getWeekday'),
    mathAliases = require('../../common/var/mathAliases');

var floor = mathAliases.floor;

function moveToBeginningOfWeek(d, firstDayOfWeek) {
  setWeekday(d, floor((getWeekday(d) - firstDayOfWeek) / 7) * 7 + firstDayOfWeek);
  return d;
}

module.exports = moveToBeginningOfWeek;