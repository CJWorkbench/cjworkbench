'use strict';

var setDate = require('./setDate'),
    getDate = require('./getDate'),
    getYear = require('./getYear'),
    getMonth = require('./getMonth'),
    getNewDate = require('./getNewDate');

function compareDay(d, shift) {
  var comp = getNewDate();
  if (shift) {
    setDate(comp, getDate(comp) + shift);
  }
  return getYear(d) === getYear(comp) &&
         getMonth(d) === getMonth(comp) &&
         getDate(d) === getDate(comp);
}

module.exports = compareDay;