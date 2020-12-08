module.exports = {
  catalogs: [
    {
      path: '<rootDir>/assets/locale/{locale}/messages',
      include: ['<rootDir>/assets/js'],
      exclude: ['**/node_modules/**']
    }
  ],
  rootDir: '.',
  format: 'po',
  locales: ['en', 'el'],
  sourceLocale: 'en'
}
