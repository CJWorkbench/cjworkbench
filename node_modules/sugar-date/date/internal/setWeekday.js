'use strict';

var setDate = require('./setDate'),
    getDate = require('./getDate'),
    getWeekday = require('./getWeekday'),
    classChecks = require('../../common/var/classChecks'),
    mathAliases = require('../../common/var/mathAliases');

var isNumber = classChecks.isNumber,
    abs = mathAliases.abs;

function setWeekday(d, dow, dir) {
  if (!isNumber(dow)) return;
  var currentWeekday = getWeekday(d);
  if (dir) {
    // Allow a "direction" parameter to determine whether a weekday can
    // be set beyond the current weekday in either direction.
    var ndir = dir > 0 ? 1 : -1;
    var offset = dow % 7 - currentWeekday;
    if (offset && offset / abs(offset) !== ndir) {
      dow += 7 * ndir;
    }
  }
  setDate(d, getDate(d) + dow - currentWeekday);
  return d.getTime();
}

module.exports = setWeekday;