const { chromium } = require("playwright");

const PAGE_URL =
  "https://api.betheltradingtechnologies.com/investor-frontend/onboarding.html?v=" +
  Date.now();

const timestamp = Date.now();

const testUser = {
  name: "Automated Registration Test",
  email: `registration-test-${timestamp}@example.com`,
  password: "SecurePass123!"
};

(async () => {
  const browser = await chromium.launch({
    headless: true
  });

  const page = await browser.newPage();

  page.on("pageerror", error => {
    console.error("JAVASCRIPT ERROR:", error.message);
  });

  page.on("console", message => {
    if (message.type() === "error") {
      console.error("BROWSER ERROR:", message.text());
    }
  });

  try {
    console.log("====================================");
    console.log("BETHEL REGISTRATION AUTOMATED TEST");
    console.log("====================================");
    console.log("Testing:", PAGE_URL);
    console.log("Email:", testUser.email);

    await page.goto(PAGE_URL, {
      waitUntil: "networkidle",
      timeout: 30000
    });

    await page.locator("#registration-panel").waitFor({
      state: "visible",
      timeout: 15000
    });

    console.log("✓ Registration page opened");

    await page.fill("#registration-name", testUser.name);
    await page.fill("#registration-email", testUser.email);
    await page.fill("#registration-password", testUser.password);
    await page.fill("#registration-confirm-password", testUser.password);
    await page.check("#registration-consent");

    const registerResponsePromise = page.waitForResponse(
      response =>
        response.url().includes("/copytrading/auth/register") &&
        response.request().method() === "POST",
      { timeout: 20000 }
    );

    await page.click("#subscriber-registration-form button[type='submit']");

    const registerResponse = await registerResponsePromise;

    console.log("Registration API:", registerResponse.status());

    if (!registerResponse.ok()) {
      throw new Error(
        "Registration failed: " + (await registerResponse.text())
      );
    }

    console.log("✓ Account created");

    await page.locator("#login-panel").waitFor({
      state: "visible",
      timeout: 15000
    });

    console.log("✓ Login page displayed");

    const emailValue = await page.inputValue("#subscriber-email");

    if (emailValue !== testUser.email) {
      throw new Error("Email not copied to login page.");
    }

    console.log("✓ Email copied");

    await page.fill("#subscriber-password", testUser.password);

    const loginResponsePromise = page.waitForResponse(
      response =>
        response.url().includes("/copytrading/auth/login") &&
        response.request().method() === "POST",
      { timeout: 20000 }
    );

    await page.click("#subscriber-login-form button[type='submit']");

    const loginResponse = await loginResponsePromise;

    console.log("Login API:", loginResponse.status());

    if (!loginResponse.ok()) {
      throw new Error(
        "Login failed: " + (await loginResponse.text())
      );
    }

    console.log("✓ Login successful");

    await page.locator("#workflow").waitFor({
      state: "visible",
      timeout: 15000
    });

    console.log("✓ Workflow loaded");

    await page.screenshot({
      path: "registration-test-success.png",
      fullPage: true
    });

    console.log("");
    console.log("====================================");
    console.log("ALL TESTS PASSED");
    console.log("====================================");
  }
  catch (error) {

    console.error("");
    console.error("TEST FAILED");
    console.error(error.message);

    await page.screenshot({
      path: "registration-test-failure.png",
      fullPage: true
    });

    process.exitCode = 1;
  }
  finally {

    await browser.close();

  }

})();