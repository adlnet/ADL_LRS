describe("Logged-In Behavior", () => {

    beforeEach(() => {
      cy.visit("/");
    });
  
    it("Allows Admin to Log In.", () => {
      
      let adminName = Cypress.env("LRS_ADMIN_NAME");
      let adminPass = Cypress.env("LRS_ADMIN_PASS");
      
      cy.get('#menuLink1').click();

      cy.get('#id_username').type(adminName);
      cy.get('#id_password').type(adminPass);

      cy.get('.pure-button').click();

      cy.get('#myaccount > div > :nth-child(1)').contains(`Welcome to the ADL LRS, ${adminName}!`);
    });
});