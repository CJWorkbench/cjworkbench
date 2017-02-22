'use strict';

var Sugar = require('sugar-core'),
    cloneDate = require('./internal/cloneDate');

Sugar.Date.defineInstance({

  'clone': function(date) {
    return cloneDate(date);
  }

});

module.exports = Sugar.Date.clone;