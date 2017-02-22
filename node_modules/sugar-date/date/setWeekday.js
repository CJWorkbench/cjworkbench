'use strict';

var Sugar = require('sugar-core'),
    setWeekday = require('./internal/setWeekday');

Sugar.Date.defineInstance({

  'setWeekday': function(date, dow) {
    return setWeekday(date, dow);
  }

});

module.exports = Sugar.Date.setWeekday;