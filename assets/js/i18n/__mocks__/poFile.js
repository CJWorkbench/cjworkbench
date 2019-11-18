// Force Jest to emulate @lingui/loader.
// (Like ... shouldn't this be the default? Shouldn't it take effort to
// make Jest _not_ invoke the loader? Instead, this turns out to be rather
// tricky.)
// inspiration: https://jestjs.io/docs/en/webpack#mocking-css-modules
const linguiApi = require('@lingui/cli/api')

module.exports = {
  process (src, filename, config, options) {
    const localeId = /locale\/(\w+)\/messages/.exec(filename)[1]
    const messages = linguiApi.formats.po.parse(src)
    const translations = Object.fromEntries(Object.entries(messages).map(([k, v]) => [k, v.translation]))
    return linguiApi.createCompiledCatalog(localeId, translations)
  }
}
