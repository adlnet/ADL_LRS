// ***********************************************
// This example commands.js shows you how to
// create various custom commands and overwrite
// existing commands.
//
// For more comprehensive examples of custom
// commands please read more here:
// https://on.cypress.io/custom-commands
// ***********************************************
//
//
// -- This is a parent command --
// Cypress.Commands.add('login', (email, password) => { ... })
//
//
// -- This is a child command --
// Cypress.Commands.add('drag', { prevSubject: 'element'}, (subject, options) => { ... })
//
//
// -- This is a dual command --
// Cypress.Commands.add('dismiss', { prevSubject: 'optional'}, (subject, options) => { ... })
//
//
// -- This will overwrite an existing command --
// Cypress.Commands.overwrite('visit', (originalFn, url, options) => { ... })

Cypress.Commands.add('visitWithJWT', (url, jwtToken) => {
    cy.intercept('GET', '**/*', (req) => {
      req.headers['authorization'] = `Bearer ${jwtToken}`;
    });
    cy.intercept('POST', '**/*', (req) => {
      req.headers['authorization'] = `Bearer ${jwtToken}`;
    });
    cy.intercept('HEAD', '**/*', (req) => {
      req.headers['authorization'] = `Bearer ${jwtToken}`;
    });
    cy.intercept('DELETE', '**/*', (req) => {
      req.headers['authorization'] = `Bearer ${jwtToken}`;
    });
    cy.intercept('PUT', '**/*', (req) => {
      req.headers['authorization'] = `Bearer ${jwtToken}`;
    });
    cy.visit({
      url: url,
      auth: {
        bearer: jwtToken
      },
      failOnStatusCode: false,
    });
  });

  Cypress.Commands.add('HTTPScheck', () => {
    cy.url().then((url) => {
      if (url.includes('https')) {
        cy.log('HTTPS is enabled')
      } else {
        cy.log('HTTPS is not enabled')
        throw new Error('HTTPS is not enabled')
      }
    })
})

//  Cypress.Commands.add('userlogin', (testID) => {
//     /* ==== Generated with Cypress Studio ==== */
//       cy.visit('/#/');
//       cy.get('span').contains('login').click();
//       cy.get(':nth-child(1) > .control > .input').clear();
//       cy.get(':nth-child(1) > .control > .input').type(testID.testusername);
//       cy.get(':nth-child(2) > .control > .input').clear();
//       cy.get(':nth-child(2) > .control > .input').type(testID.testuserpassword);
//       cy.wait(1000)
//       cy.get('.is-primary').click();
//     /* ==== End Cypress Studio ==== */
//   })
// Cypress.Commands.add('createaccount', (testID) => {
//       cy.visit('/#/');
//       cy.get('span').contains('login').click();
//       cy.get('.button').contains('span','create account').click()
//       cy.get(':nth-child(1) > .control > .input').clear().type(testID.testname);
//       cy.get(':nth-child(2) > .control > .input').clear().type(testID.testemail);
//       cy.get(':nth-child(3) > .control > .input').clear().type(testID.testusername);
//       cy.get('.is-grouped > :nth-child(1) > .input').clear().type(testID.testuserpassword);
//       cy.get(':nth-child(2) > .input').clear().type(testID.testuserpassword);
//       cy.get('.buttons > .is-expanded').click();
//       cy.wait(waittime)
// })