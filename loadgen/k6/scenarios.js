// k6 load scenarios for the food delivery platform: browse a menu, place an order, pay.
//
// Every scenario follows the same lunch peak profile over LOAD_DURATION:
//   quiet morning -> ramp up -> lunch peak -> ramp down -> quiet afternoon
// PEAK_VUS is the number of virtual users browsing at the peak. Fewer users order and pay.
// Do not name these K6_VUS or K6_DURATION in the environment: k6 reads those itself and
// they replace the scenarios below.
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const PEAK_VUS = parseInt(__ENV.PEAK_VUS || '5', 10);
const DURATION = __ENV.LOAD_DURATION || '2m';
const JSON_HEADERS = { headers: { 'Content-Type': 'application/json' } };

// "90s", "2m", "1h" -> seconds.
function seconds(d) {
  const m = /^(\d+)(s|m|h)$/.exec(d);
  if (!m) throw new Error(`LOAD_DURATION must look like 90s, 2m or 1h, got ${d}`);
  return parseInt(m[1], 10) * { s: 1, m: 60, h: 3600 }[m[2]];
}

// Share of the total duration and share of the peak load for each stage.
const SHAPE = [
  { part: 0.15, load: 0.2 }, // quiet morning
  { part: 0.2, load: 1.0 }, // ramp up to lunch
  { part: 0.3, load: 1.0 }, // lunch peak
  { part: 0.2, load: 0.2 }, // ramp down
  { part: 0.15, load: 0.2 }, // quiet afternoon
];

function lunchPeak(peak) {
  const total = seconds(DURATION);
  return SHAPE.map((s) => ({
    duration: `${Math.max(1, Math.round(total * s.part))}s`,
    target: Math.max(1, Math.round(peak * s.load)),
  }));
}

function scenario(exec, peak) {
  return {
    executor: 'ramping-vus',
    exec,
    startVUs: 1,
    stages: lunchPeak(peak),
    gracefulRampDown: '10s',
  };
}

export const options = {
  scenarios: {
    browse_menu: scenario('browseMenu', PEAK_VUS),
    place_order: scenario('placeOrder', Math.max(1, Math.round(PEAK_VUS * 0.6))),
    pay: scenario('pay', Math.max(1, Math.round(PEAK_VUS * 0.2))),
  },
  thresholds: {
    http_req_failed: ['rate<0.10'],
    http_req_duration: ['p(95)<1500'],
    'http_req_duration{scenario:place_order}': ['p(95)<2000'],
  },
};

const RESTAURANTS = ['1', '2', '3', '4'];
const ADDRESSES = ['12 Rue de la Paix', '4 Avenue Mohammed V', '88 Baker Street', '1 Main Square'];

http.setResponseCallback(http.expectedStatuses({ min: 200, max: 299 }, 402, 409));

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

function menu(restaurantId) {
  const res = http.get(`${BASE_URL}/api/menu/${restaurantId}`, {
    tags: { name: 'GET /api/menu/{id}' },
  });
  check(res, { 'menu 200': (r) => r.status === 200 });
  return res.status === 200 ? res.json('menu') : [];
}

export function browseMenu() {
  menu(pick(RESTAURANTS));
  sleep(1 + Math.random() * 2);
}

export function placeOrder() {
  const restaurantId = pick(RESTAURANTS);
  const dishes = menu(restaurantId);
  if (dishes.length === 0) return;
  sleep(0.5 + Math.random());

  // Mostly available dishes, sometimes a sold out one, which restaurants rejects with 409.
  const count = 1 + Math.floor(Math.random() * 3);
  const items = [];
  for (let i = 0; i < count; i++) {
    const pool = Math.random() < 0.9 ? dishes.filter((d) => d.available) : dishes;
    items.push({ dish_id: pick(pool).id, quantity: 1 + Math.floor(Math.random() * 2) });
  }
  const body = JSON.stringify({ restaurant_id: restaurantId, items, address: pick(ADDRESSES) });
  const res = http.post(`${BASE_URL}/api/orders`, body, JSON_HEADERS);
  check(res, {
    'order handled': (r) => [201, 202, 402, 409].includes(r.status),
    'order confirmed': (r) => r.status === 201,
  });
  sleep(1 + Math.random() * 2);
}

// Direct charge, for example a tip added after the delivery.
export function pay() {
  const body = JSON.stringify({
    order_id: 1 + Math.floor(Math.random() * 1000),
    amount: Math.round(Math.random() * 500) / 100 + 1,
  });
  const res = http.post(`${BASE_URL}/api/payments`, body, JSON_HEADERS);
  check(res, { 'payment handled': (r) => r.status === 201 || r.status === 502 });
  sleep(2 + Math.random() * 3);
}
