'use strict';

var Sugar = require('sugar-core'),
    getYear = require('./internal/getYear');

Sugar.Date.defineInstance({

  'isLeapYear': function(date) {
    var year = getYear(date);
    return (year % 4 === 0 && year % 100 !== 0) || (year % 400 === 0);
  }

});

module.exports = Sugar.Date.isLeapYear;