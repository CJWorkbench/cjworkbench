'use strict';

var Sugar = require('sugar-core'),
    dateFormat = require('./internal/dateFormat');

Sugar.Date.defineInstance({

  'format': function(date, f, localeCode) {
    return dateFormat(date, f, localeCode);
  }

});

module.exports = Sugar.Date.format;