'use strict';

var Sugar = require('sugar-core'),
    createDateWithContext = require('./internal/createDateWithContext');

Sugar.Date.defineInstance({

  'get': function(date, d, options) {
    return createDateWithContext(date, d, options);
  }

});

module.exports = Sugar.Date.get;