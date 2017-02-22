'use strict';

var Sugar = require('sugar-core');

Sugar.Date.defineInstance({

  'iso': function(date) {
    return date.toISOString();
  }

});

module.exports = Sugar.Date.iso;