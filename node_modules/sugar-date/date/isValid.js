'use strict';

var Sugar = require('sugar-core'),
    dateIsValid = require('./internal/dateIsValid');

Sugar.Date.defineInstance({

  'isValid': function(date) {
    return dateIsValid(date);
  }

});

module.exports = Sugar.Date.isValid;