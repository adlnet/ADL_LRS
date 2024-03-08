const { defineConfig } = require('cypress');

module.exports = defineConfig({
  e2e: {
    specPattern: 'e2e/*.cy.{js,jsx,ts,tsx}',
    baseUrl: process.env.LRS_HOSTNAME,
    experimentalStudio: true
  },
  env: {
    LRS_USERNAME: process.env.LRS_USERNAME,
    LRS_PASSWORD: process.env.LRS_PASSWORD
  },
  defaultCommandTimeout: 9000,
});

