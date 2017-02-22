'use strict';

var Sugar = require('sugar-core'),
    fullCompareDate = require('./internal/fullCompareDate');

Sugar.Date.defineInstance({

  'is': function(date, d, margin) {
    return fullCompareDate(date, d, margin);
  }

});

module.exports = Sugar.Date.is;