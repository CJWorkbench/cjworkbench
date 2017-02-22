module.exports = function(markup) {
	markup = markup || '<html><body></body></html>'
  if (typeof document !== 'undefined') return;
  var jsdom = require('jsdom').jsdom;
  global.document = jsdom(markup || '');
  global.window = document.defaultView;
  global.fetch = function(){}
  global.navigator = {
    userAgent: 'node.js'
  }
};