const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    specPattern: 'e2e/*.cy.{js,jsx,ts,tsx}',
    baseUrl: 'https://lrs.local.adlnet.gov',
    experimentalStudio: true
  },
  env: {
    LRS_ADMIN_NAME: "root",
    LRS_ADMIN_PASS: "1234"
  },
  defaultCommandTimeout: 9000,
});

