'use strict';

var Range = require('./internal/Range'),
    defineOnPrototype = require('../common/internal/defineOnPrototype');

defineOnPrototype(Range, {

  'clone': function() {
    return new Range(this.start, this.end);
  }

});

// This package does not export anything as it is
// simply defining "clone" on Range.prototype.