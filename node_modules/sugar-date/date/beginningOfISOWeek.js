'use strict';

var Sugar = require('sugar-core'),
    resetTime = require('./internal/resetTime'),
    getWeekday = require('./internal/getWeekday'),
    setWeekday = require('./internal/setWeekday');

Sugar.Date.defineInstance({

  'beginningOfISOWeek': function(date) {
    var day = getWeekday(date);
    if (day === 0) {
      day = -6;
    } else if (day !== 1) {
      day = 1;
    }
    setWeekday(date, day);
    return resetTime(date);
  }

});

module.exports = Sugar.Date.beginningOfISOWeek;