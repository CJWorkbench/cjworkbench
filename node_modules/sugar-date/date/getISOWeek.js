'use strict';

var Sugar = require('sugar-core'),
    getWeekNumber = require('./internal/getWeekNumber');

Sugar.Date.defineInstance({

  'getISOWeek': function(date) {
    return getWeekNumber(date, true);
  }

});

module.exports = Sugar.Date.getISOWeek;