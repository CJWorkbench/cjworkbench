'use strict';

var Sugar = require('sugar-core'),
    createDate = require('./internal/createDate'),
    dateRelative = require('./internal/dateRelative');

Sugar.Date.defineInstance({

  'relativeTo': function(date, d, localeCode) {
    return dateRelative(date, createDate(d), localeCode);
  }

});

module.exports = Sugar.Date.relativeTo;