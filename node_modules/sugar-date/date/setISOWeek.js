'use strict';

var Sugar = require('sugar-core'),
    setISOWeekNumber = require('./internal/setISOWeekNumber');

Sugar.Date.defineInstance({

  'setISOWeek': function(date, num) {
    return setISOWeekNumber(date, num);
  }

});

module.exports = Sugar.Date.setISOWeek;