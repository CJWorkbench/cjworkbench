'use strict';

var setWeekday = require('./setWeekday'),
    getWeekday = require('./getWeekday'),
    mathAliases = require('../../common/var/mathAliases');

var ceil = mathAliases.ceil;

function moveToEndOfWeek(d, firstDayOfWeek) {
  var target = firstDayOfWeek - 1;
  setWeekday(d, ceil((getWeekday(d) - target) / 7) * 7 + target);
  return d;
}

module.exports = moveToEndOfWeek;