describe("Homepage Behavior", () => {

    beforeEach(() => {
      cy.visit("/");
    });
  
    it("Loads the homepage.", () => {  
        cy.get('.splash-head').contains("ADL Learning Record Store")
    });
});