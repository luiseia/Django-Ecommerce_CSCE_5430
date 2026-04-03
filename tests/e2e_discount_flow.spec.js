const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8000';
const MERCHANT_SESSION = process.env.MERCHANT_SESSION;
const SHOPPER_SESSION = process.env.SHOPPER_SESSION;

function nowLocalDatetimeInput() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

async function addSessionCookie(context, sessionKey) {
  await context.addCookies([
    {
      name: 'sessionid',
      value: sessionKey,
      domain: 'localhost',
      path: '/',
      httpOnly: true,
      secure: false,
      sameSite: 'Lax',
    },
  ]);
}

test('merchant creates WELCOME10 and shopper places discounted order', async ({ browser }) => {
  test.skip(!MERCHANT_SESSION || !SHOPPER_SESSION, 'Missing MERCHANT_SESSION/SHOPPER_SESSION env vars');

  // Merchant: create discount
  const merchantContext = await browser.newContext();
  await addSessionCookie(merchantContext, MERCHANT_SESSION);
  const merchantPage = await merchantContext.newPage();

  await merchantPage.goto(`${BASE_URL}/discounts/merchant/discounts/create/`, { waitUntil: 'domcontentloaded' });
  await expect(merchantPage.locator('h3')).toContainText(/Create New Discount|Edit Discount/i);

  await merchantPage.fill('input[name="code"]', 'WELCOME10');
  await merchantPage.check('input[name="discount_type"][value="FIXED"]');
  await merchantPage.fill('input[name="discount_value"]', '10');
  await merchantPage.fill('input[name="min_purchase_amount"]', '50');
  await merchantPage.fill('input[name="min_product_price"]', '0');
  await merchantPage.fill('textarea[name="description"]', 'Welcome discount: save $10 on orders over $50');

  const validFrom = merchantPage.locator('input[name="valid_from"]');
  if (await validFrom.count()) {
    await validFrom.fill(nowLocalDatetimeInput());
  }

  await merchantPage.click('button:has-text("Save Discount")');
  await merchantPage.waitForURL('**/discounts/merchant/discounts/**');
  await expect(merchantPage.locator('body')).toContainText('WELCOME10');
  await merchantContext.close();

  // Shopper: buy product and apply discount
  const shopperContext = await browser.newContext();
  await addSessionCookie(shopperContext, SHOPPER_SESSION);
  const shopperPage = await shopperContext.newPage();

  await shopperPage.goto(`${BASE_URL}/products/shop/`, { waitUntil: 'domcontentloaded' });
  await shopperPage.locator('a:has-text("View")').first().click();

  const addButton = shopperPage.locator('button:has-text("Add to Cart")');
  await expect(addButton).toBeVisible();
  await addButton.click();

  await shopperPage.goto(`${BASE_URL}/cart/checkout/`, { waitUntil: 'domcontentloaded' });
  await shopperPage.fill('#discount-code-input', 'WELCOME10');
  await shopperPage.click('#discount-form button:has-text("Apply")');

  await expect(shopperPage.locator('#applied-discount')).toBeVisible();
  await expect(shopperPage.locator('#discount-message')).toContainText(/Discount applied/i);

  await shopperPage.fill('textarea[name="shipping_address"]', 'Playwright Test Address');
  await shopperPage.click('#checkout-form button:has-text("Place Order")');

  await expect(shopperPage.locator('h2')).toContainText('Order Details');

  const subtotalText = await shopperPage.locator('tfoot tr:has(td:text("Subtotal")) td').last().innerText();
  const totalText = await shopperPage.locator('tfoot tr.fw-bold td').last().innerText();
  await expect(shopperPage.locator('tfoot tr:has(td:text("Discount"))')).toBeVisible();

  const parseMoney = (s) => Number(String(s).replace(/[^0-9.-]/g, ''));
  const subtotal = parseMoney(subtotalText);
  const total = parseMoney(totalText);

  expect(total).toBeLessThan(subtotal);

  await shopperContext.close();
});
