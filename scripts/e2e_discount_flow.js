const { chromium } = require('playwright');

const BASE_URL = 'http://localhost:8000';
const MERCHANT_SESSION = process.env.MERCHANT_SESSION;
const SHOPPER_SESSION = process.env.SHOPPER_SESSION;

if (!MERCHANT_SESSION || !SHOPPER_SESSION) {
  console.error('Missing MERCHANT_SESSION or SHOPPER_SESSION env vars.');
  process.exit(1);
}

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

async function merchantCreateWelcome10(browser) {
  const context = await browser.newContext();
  await addSessionCookie(context, MERCHANT_SESSION);
  const page = await context.newPage();

  await page.goto(`${BASE_URL}/discounts/merchant/discounts/create/`, { waitUntil: 'domcontentloaded' });

  await page.fill('input[name="code"]', 'WELCOME10');
  await page.check('input[name="discount_type"][value="FIXED"]');
  await page.fill('input[name="discount_value"]', '10');
  await page.fill('input[name="min_purchase_amount"]', '50');
  await page.fill('input[name="min_product_price"]', '0');
  await page.fill('textarea[name="description"]', 'Welcome discount: save $10 on orders over $50');

  const validFrom = page.locator('input[name="valid_from"]');
  if (await validFrom.count()) {
    await validFrom.fill(nowLocalDatetimeInput());
  }

  await page.click('button:has-text("Save Discount")');
  await page.waitForURL('**/discounts/merchant/discounts/**', { timeout: 15000 });

  const listHasWelcome10 = await page.locator('text=WELCOME10').count();
  await context.close();

  if (!listHasWelcome10) {
    throw new Error('Merchant flow failed: WELCOME10 not found in discount list after save.');
  }

  return { created: true };
}

async function shopperBuyWithWelcome10(browser) {
  const context = await browser.newContext();
  await addSessionCookie(context, SHOPPER_SESSION);
  const page = await context.newPage();

  await page.goto(`${BASE_URL}/products/shop/`, { waitUntil: 'domcontentloaded' });
  await page.locator('a:has-text("View")').first().click();

  const addButton = page.locator('button:has-text("Add to Cart")');
  if (!(await addButton.count())) {
    throw new Error('Shopper flow failed: no in-stock product with Add to Cart found.');
  }
  await addButton.click();

  await page.goto(`${BASE_URL}/cart/checkout/`, { waitUntil: 'domcontentloaded' });

  await page.fill('#discount-code-input', 'WELCOME10');
  await page.click('#discount-form button:has-text("Apply")');

  await page.waitForSelector('#applied-discount', { state: 'visible', timeout: 15000 });
  const applyMessage = (await page.locator('#discount-message').innerText()).trim();

  const totalBeforeOrder = (await page.locator('#total').innerText()).trim();

  await page.fill('textarea[name="shipping_address"]', 'Playwright Test Address');
  await page.click('#checkout-form button:has-text("Place Order")');

  await page.waitForSelector('h2:has-text("Order Details")', { timeout: 15000 });

  const subtotalText = (await page.locator('tfoot tr:has(td:text("Subtotal")) td').last().innerText()).trim();
  const totalText = (await page.locator('tfoot tr.fw-bold td').last().innerText()).trim();
  const discountRow = page.locator('tfoot tr:has(td:text("Discount")) td').last();
  const hasDiscountRow = await discountRow.count();
  const discountText = hasDiscountRow ? (await discountRow.innerText()).trim() : null;

  await context.close();

  return {
    appliedMessage: applyMessage,
    totalBeforeOrder,
    subtotalText,
    totalText,
    discountText,
    hasDiscountRow: Boolean(hasDiscountRow),
  };
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  try {
    const merchantResult = await merchantCreateWelcome10(browser);
    const shopperResult = await shopperBuyWithWelcome10(browser);

    const parseMoney = (s) => Number(String(s).replace(/[^0-9.-]/g, ''));
    const subtotal = parseMoney(shopperResult.subtotalText);
    const total = parseMoney(shopperResult.totalText);

    const ok = shopperResult.hasDiscountRow && total < subtotal;

    console.log(JSON.stringify({
      ok,
      merchantResult,
      shopperResult,
      assertion: {
        total_less_than_subtotal: total < subtotal,
        discount_row_present: shopperResult.hasDiscountRow,
      },
    }, null, 2));

    if (!ok) process.exit(2);
  } catch (err) {
    console.error('E2E failed:', err.message);
    process.exit(1);
  } finally {
    await browser.close();
  }
})();
