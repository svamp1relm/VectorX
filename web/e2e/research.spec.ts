import { expect, test, type APIRequestContext } from '@playwright/test'

const apiBase = process.env.E2E_API_BASE ?? 'http://127.0.0.1:8001'

async function firstHistoricalExperimentId(request: APIRequestContext): Promise<number> {
  const response = await request.get(`${apiBase}/experiments`)
  expect(response.ok()).toBeTruthy()
  const items = (await response.json()) as Array<{
    id: number
    spec_type: string
  }>
  const historical = items.find((item) => item.spec_type === 'historical_backtest')
  expect(historical).toBeDefined()
  return historical!.id
}

test('opens an experiment from the real PostgreSQL-backed list', async ({ page, request }) => {
  const id = await firstHistoricalExperimentId(request)
  await page.goto('/')
  await page.getByTestId(`experiment-row-${id}`).click()

  await expect(page.getByRole('heading', { name: 'Parameters' })).toBeVisible()
  await expect(page.getByTestId('total-trades-value')).toBeVisible()
})

test('shows a valid historical run with zero trades', async ({ page, request }) => {
  const response = await request.post(`${apiBase}/experiments`, {
    data: {
      type: 'historical_backtest',
      name: `e2e_flat_${Date.now()}`,
      data: {
        source: 'csv',
        path: 'configs/experiments/data/e2e_flat.csv',
        symbol: 'BTCUSDT',
        timeframe: '1h',
      },
      strategy: {
        type: 'moving_average_crossover',
        fast_period: 2,
        slow_period: 4,
        stop_loss_pct: 0.01,
      },
      portfolio: { initial_capital: 10000, risk_per_trade: 0.01 },
      storage: { store_trades: true },
    },
  })
  expect(response.status()).toBe(201)
  const created = (await response.json()) as { id: number }

  await page.goto('/')
  await page.getByTestId(`experiment-row-${created.id}`).click()
  await expect(page.getByTestId('total-trades-value')).toHaveText('0')
  await expect(page.getByText('Run 0 final capital')).toBeVisible()
})

test('runs parameter sensitivity through the real robustness API', async ({ page, request }) => {
  const id = await firstHistoricalExperimentId(request)
  await page.goto('/')
  await page.getByRole('button', { name: 'Robustness', exact: true }).click()
  await page.getByTestId('robustness-base-id').fill(String(id))
  await page.getByTestId('sensitivity-grid').fill('{"strategy.fast_period":[8,10]}')
  await page.getByTestId('sensitivity-run').click()

  await expect(page.getByTestId('sensitivity-row')).toHaveCount(2, { timeout: 60_000 })
})

test('runs OOS and renders a train/test delta', async ({ page, request }) => {
  const id = await firstHistoricalExperimentId(request)
  await page.goto('/')
  await page.getByRole('button', { name: 'Out-of-Sample', exact: true }).click()
  await page.getByTestId('oos-base-id').fill(String(id))
  await page.getByTestId('oos-train-start').fill('2024-09-27T00:00:00+00:00')
  await page.getByTestId('oos-train-end').fill('2025-09-26T23:00:00+00:00')
  await page.getByTestId('oos-test-start').fill('2025-09-27T00:00:00+00:00')
  await page.getByTestId('oos-test-end').fill('2026-09-27T19:00:00+00:00')
  await page.getByTestId('oos-run-button').click()

  await expect(page.getByTestId('oos-delta')).toBeVisible({ timeout: 60_000 })
})

test('does not present failed result loading as zero trades', async ({ page, request }) => {
  const id = await firstHistoricalExperimentId(request)
  await page.route(`**/experiments/${id}/results`, (route) => route.abort())
  await page.goto('/')
  await page.getByTestId(`experiment-row-${id}`).click()

  await expect(page.getByTestId('results-error')).toBeVisible()
  await expect(page.getByTestId('total-trades-value')).toHaveText('—')
})

test('supports keyboard navigation, Russian locale, and dark theme', async ({ page }) => {
  await page.goto('/')
  const robustness = page.getByRole('button', { name: 'Robustness', exact: true })
  await robustness.focus()
  await robustness.press('Enter')
  await expect(page.getByRole('heading', { name: 'Robustness', exact: true })).toBeVisible()

  await page.getByRole('button', { name: 'RU', exact: true }).click()
  await expect(page.getByRole('heading', { name: 'Устойчивость', exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Тёмная', exact: true }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
})
