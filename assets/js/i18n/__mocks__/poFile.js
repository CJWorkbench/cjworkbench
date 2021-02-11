// Force Jest to emulate @lingui/loader.
// (Like ... shouldn't this be the default? Shouldn't it take effort to
// make Jest _not_ invoke the loader? Instead, this turns out to be rather
// tricky.)
// inspiration: https://jestjs.io/docs/en/webpack#mocking-css-modules
const path = require('path')
const { getConfig } = require('@lingui/conf')
const {
  createCompiledCatalog,
  getCatalogs,
  getCatalogForFile
} = require('@lingui/cli/api')

module.exports = {
  process (src, filename) {
    // https://github.com/lingui/js-lingui/blob/main/packages/loader/src/index.js
    const config = getConfig()
    const catalogRelativePath = path.relative(config.rootDir, filename)
    const { locale, catalog } = getCatalogForFile(
      catalogRelativePath,
      getCatalogs(config)
    )
    const catalogs = catalog.readAll()
    const messages = Object.fromEntries(
      Object.entries(catalogs[locale]).map(([k, v]) => [
        k,
        catalog.getTranslation(catalogs, locale, k, {
          fallbackLocales: config.fallbackLocales,
          sourceLocale: config.sourceLocale
        })
      ])
    )
    return createCompiledCatalog(locale, messages, {
      strict: false,
      namespace: config.compileNamespace,
      pseudoLocale: config.pseudoLocale
    })
  }
}
