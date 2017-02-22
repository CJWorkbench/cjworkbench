'use strict';

var Sugar = require('sugar-core'),
    getDaysInMonth = require('./internal/getDaysInMonth');

Sugar.Date.defineInstance({

  'daysInMonth': function(date) {
    return getDaysInMonth(date);
  }

});

module.exports = Sugar.Date.daysInMonth;