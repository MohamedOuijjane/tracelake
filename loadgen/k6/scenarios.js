// k6 load scenarios: browse the catalog, place an order, pay for it.
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const VUS = parseInt(__ENV.K6_VUS || '5', 10);
const DURATION = __ENV.K6_DURATION || '2m';
const JSON_HEADERS = { headers: { 'Content-Type': 'application/json' } };

export const options = {
  scenarios: {
    browse: {
      executor: 'constant-vus',
      exec: 'browse',
      vus: VUS,
      duration: DURATION,
    },
    place_order: {
      executor: 'constant-vus',
      exec: 'placeOrder',
      vus: Math.max(1, Math.floor(VUS / 2)),
      duration: DURATION,
    },
    pay: {
      executor: 'constant-vus',
      exec: 'pay',
      vus: Math.max(1, Math.floor(VUS / 2)),
      duration: DURATION,
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.10'],
    http_req_duration: ['p(95)<1000'],
  },
};

const SKUS = ['SKU-001', 'SKU-002', 'SKU-003', 'SKU-004'];

function pick(list) {
  return list[Math.floor(Math.random() * list.length)];
}

export function browse() {
  const res = http.get(`${BASE_URL}/api/catalog`);
  check(res, { 'catalog 200': (r) => r.status === 200 });
  const sku = pick(SKUS);
  http.get(`${BASE_URL}/api/inventory/${sku}`);
  sleep(1);
}

export function placeOrder() {
  const body = JSON.stringify({ sku: pick(SKUS), quantity: 1 + Math.floor(Math.random() * 3) });
  const res = http.post(`${BASE_URL}/api/orders`, body, JSON_HEADERS);
  check(res, { 'order accepted': (r) => r.status === 201 || r.status === 409 });
  sleep(1);
}

export function pay() {
  const body = JSON.stringify({
    order_id: 1 + Math.floor(Math.random() * 1000),
    amount: Math.round(Math.random() * 20000) / 100 + 1,
  });
  const res = http.post(`${BASE_URL}/api/payments`, body, JSON_HEADERS);
  check(res, { 'payment handled': (r) => r.status === 201 || r.status === 502 });
  sleep(1);
}
