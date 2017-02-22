'use strict';

var Sugar = require('sugar-core'),
    isUTC = require('./internal/isUTC');

Sugar.Date.defineInstance({

  'isUTC': function(date) {
    return isUTC(date);
  }

});

module.exports = Sugar.Date.isUTC;