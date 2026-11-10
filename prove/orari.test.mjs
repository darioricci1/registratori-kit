// registratori-kit/prove/orari.test.mjs - version: 1.0.0 (10/11/2026): le ore di accensione lette dalle note vere degli ODM
import test from "node:test";
import assert from "node:assert/strict";
import { finestreAccese, dentro, noteOdm } from "../api/_orari.js";

test("le frasi su quando il kit c'e'", () => {
  assert.deepEqual(finestreAccese("04/11 il kit è rimasto acceso solo dalle 13 alle 16 il 2-3/11"), [[13, 16]]);
  assert.deepEqual(finestreAccese("09/11 non risp p2p/sms + 04/11 acceso solo dalle 10 alle 16 circa"), [[10, 16]]);
  assert.deepEqual(finestreAccese("05/06 Kit acceso solo dalle 07 alle 16,00"), [[7, 16]]);
  assert.deepEqual(finestreAccese("25/09 Risponde solo di sera; 21/09 il sistema si è ripreso"), [[18, 23]]);
  assert.deepEqual(finestreAccese("31/07 Risponde solo di sera alle 22 circa"), [[18, 23]]);
  assert.deepEqual(finestreAccese("20/8 non risp p2p, risp a sma alle 20:30 circa"), []);
  assert.deepEqual(finestreAccese("risponde a sms alle 20:30 circa"), [[19, 22]]);
});
test("le frasi su quando manca non contano", () => {
  assert.deepEqual(finestreAccese("24/10 ch3 salta dalle 12 alle 18,30. Poi risalta dalle 6,30 alle 17,30"), []);
  assert.deepEqual(finestreAccese("18/09 CH3 sat spento dalle 7:30 alle 19:15 circa"), []);
  assert.deepEqual(finestreAccese("10/11 CH1 video loss"), []);
  assert.deepEqual(finestreAccese(""), []);
});
test("dentro la finestra, anche a cavallo della mezzanotte", () => {
  assert.equal(dentro([[13, 16]], 14), true);
  assert.equal(dentro([[13, 16]], 16), false);
  assert.equal(dentro([[22, 6]], 23), true);
  assert.equal(dentro([[22, 6]], 3), true);
  assert.equal(dentro([[22, 6]], 12), false);
});
test("le note dal JSON del ponte e dal testo vecchio", () => {
  assert.equal(noteOdm('[{"n":"1","note":"a"},{"n":"2","note":"b"}]'), "a · b");
  assert.equal(noteOdm("n° 1686 del 03/11/2026, GUASTO: x"), "n° 1686 del 03/11/2026, GUASTO: x");
});
