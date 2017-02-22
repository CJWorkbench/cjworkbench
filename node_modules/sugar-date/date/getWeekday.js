'use strict';

var Sugar = require('sugar-core'),
    getWeekday = require('./internal/getWeekday');

Sugar.Date.defineInstance({

  'getWeekday': function(date) {
    return getWeekday(date);
  }

});

module.exports = Sugar.Date.getWeekday;