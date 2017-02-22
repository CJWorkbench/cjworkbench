'use strict';

var Range = require('./internal/Range'),
    rangeEvery = require('./internal/rangeEvery'),
    defineOnPrototype = require('../common/internal/defineOnPrototype');

defineOnPrototype(Range, {

  'toArray': function() {
    return rangeEvery(this);
  }

});

// This package does not export anything as it is
// simply defining "toArray" on Range.prototype.