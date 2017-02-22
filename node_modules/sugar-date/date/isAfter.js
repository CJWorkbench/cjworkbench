'use strict';

var Sugar = require('sugar-core'),
    createDate = require('./internal/createDate');

Sugar.Date.defineInstance({

  'isAfter': function(date, d, margin) {
    return date.getTime() > createDate(d).getTime() - (margin || 0);
  }

});

module.exports = Sugar.Date.isAfter;