/*
 * ESP32 + PN532: дубликатор пропуска «в одном устройстве».
 * Режимы: SCAN (UID), DUMP (секторы), WRITE (пустая magic-карта), EMULATE (target).
 * Только свой пропуск, с разрешения владельца. Без подбора ключей и взлома СКУД.
 */

#include <Arduino.h>
#include <Preferences.h>
#include <Adafruit_PN532.h>
#include "config.h"

Adafruit_PN532 nfc(PN532_CLK, PN532_MISO, PN532_MOSI, PN532_CS);
Preferences prefs;

uint8_t gUid[7] = {0};
uint8_t gUidLen = 0;
static uint8_t gDump[MF_BLOCKS_1K][MF_BLOCK_SIZE];
static bool    gValid[MF_BLOCKS_1K];

void printUid(const uint8_t *u, uint8_t len) {
  Serial.print(F("UID: "));
  for (uint8_t i = 0; i < len; i++) {
    if (u[i] < 0x10) Serial.print('0');
    Serial.print(u[i], HEX);
    Serial.print(' ');
  }
  Serial.printf("(%d байт)\n", len);
}

void saveState() {
  prefs.begin("nfcemu", false);
  prefs.putUInt("len", gUidLen);
  if (gUidLen) prefs.putBytes("uid", gUid, gUidLen);
  for (uint16_t i = 0; i < MF_BLOCKS_1K; i++) {
    char k[8];
    snprintf(k, sizeof(k), "b%u", i);
    if (gValid[i]) prefs.putBytes(k, gDump[i], MF_BLOCK_SIZE);
    snprintf(k, sizeof(k), "v%u", i);
    prefs.putBool(k, gValid[i]);
  }
  prefs.end();
  Serial.println(F("Сохранено в NVS"));
}

void loadState() {
  prefs.begin("nfcemu", true);
  gUidLen = prefs.getUInt("len", 0);
  if (gUidLen > 7) gUidLen = 7;
  if (gUidLen) prefs.getBytes("uid", gUid, gUidLen);
  memset(gDump, 0, sizeof(gDump));
  memset(gValid, 0, sizeof(gValid));
  for (uint16_t i = 0; i < MF_BLOCKS_1K; i++) {
    char k[8];
    snprintf(k, sizeof(k), "v%u", i);
    gValid[i] = prefs.getBool(k, false);
    snprintf(k, sizeof(k), "b%u", i);
    if (gValid[i]) prefs.getBytes(k, gDump[i], MF_BLOCK_SIZE);
  }
  prefs.end();
  if (gUidLen == 7) {
    Serial.print(F("Загружен UID: ")); printUid(gUid, gUidLen);
  }
}

bool waitCard(uint8_t *u, uint8_t *len, uint16_t timeoutMs) {
  unsigned long t0 = millis();
  while (millis() - t0 < timeoutMs) {
    if (nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, u, len, 400)) return true;
    delay(40);
  }
  return false;
}

void cmdScan() {
  uint8_t u[7] = {0}, len = 0;
  Serial.println(F("SCAN: приложите карту (10 с)..."));
  if (!waitCard(u, &len, 10000)) { Serial.println(F("Карта не найдена")); return; }
  printUid(u, len);
  if (len != 7) { Serial.println(F("Нужен 7-байтовый UID")); return; }
  memcpy(gUid, u, 7); gUidLen = 7;
  saveState();
}

// Собираем блок 0 для MIFARE Classic с 7-байтовым UID (CL1+CL2)
void buildBlock0(const uint8_t *u, uint8_t len, uint8_t out[MF_BLOCK_SIZE]) {
  memset(out, 0, MF_BLOCK_SIZE);
  if (len == 7) {
    out[0] = 0x88;                       // CT
    out[1] = u[0]; out[2] = u[1]; out[3] = u[2];
    out[4] = 0x88 ^ u[0] ^ u[1] ^ u[2];  // BCC0
    out[5] = u[3]; out[6] = u[4]; out[7] = u[5]; out[8] = u[6];
    out[9] = u[3] ^ u[4] ^ u[5] ^ u[6];  // BCC1
    out[10] = MF_SAK;
    out[11] = MF_ATQA_0; out[12] = MF_ATQA_1;
  } else if (len == 4) {
    out[0] = u[0]; out[1] = u[1]; out[2] = u[2]; out[3] = u[3];
    out[4] = u[0] ^ u[1] ^ u[2] ^ u[3];
    out[5] = MF_SAK;
    out[6] = MF_ATQA_0; out[7] = MF_ATQA_1;
  } else {
    Serial.println(F("Неподдерживаемая длина UID для блока 0"));
  }
}

void cmdDump() {
  uint8_t u[7] = {0}, len = 0;
  Serial.println(F("DUMP: приложите ОРИГИНАЛЬНУЮ карту (10 с)..."));
  if (!waitCard(u, &len, 10000)) { Serial.println(F("Карта не найдена")); return; }
  if (len != 7) { Serial.println(F("Нужен 7-байтовый UID")); return; }
  memcpy(gUid, u, 7); gUidLen = 7;
  memset(gValid, 0, sizeof(gValid));

  uint16_t ok = 0;
  for (uint8_t sector = 0; sector < MF_SECTORS_1K; sector++) {
    uint8_t block = sector * 4;
    bool authed = false;
    for (uint8_t ki = 0; ki < MF_KEYS_COUNT && !authed; ki++) {
      if (nfc.mifareclassic_AuthenticateBlock(u, len, block, 0,
          const_cast<uint8_t *>(MF_KEYS[ki]))) authed = true;
      if (!authed && nfc.mifareclassic_AuthenticateBlock(u, len, block, 1,
          const_cast<uint8_t *>(MF_KEYS[ki]))) authed = true;
    }
    if (!authed) {
      Serial.printf("Сектор %d: ключ неизвестен — пропущен (подбор не делаем)\n", sector);
      continue;
    }
    for (uint8_t b = 0; b < 4; b++) {
      if (nfc.mifareclassic_ReadDataBlock(block + b, gDump[block + b])) {
        gValid[block + b] = true; ok++;
      }
    }
    Serial.printf("Сектор %d: прочитан\n", sector);
  }
  Serial.printf("Прочитано блоков: %d из %d\n", ok, MF_BLOCKS_1K);
  saveState();
}

bool confirmYes() {
  Serial.println(F("ВНИМАНИЕ: запись идёт только на ПУСТУЮ карту с меняемым UID."));
  Serial.println(F("Наберите YES и Enter для подтверждения (15 с):"));
  unsigned long t0 = millis();
  String in;
  while (millis() - t0 < 15000UL) {
    if (Serial.available()) {
      in = Serial.readStringUntil('\n');
      in.trim(); in.toUpperCase();
      break;
    }
    delay(20);
  }
  return in == "YES";
}

void cmdWrite() {
  if (gUidLen != 7) { Serial.println(F("Сначала SCAN или DUMP")); return; }
  if (!confirmYes()) { Serial.println(F("Отмена")); return; }

  uint8_t u[7] = {0}, len = 0;
  Serial.println(F("WRITE: приложите ПУСТУЮ magic-карту (10 с)..."));
  if (!waitCard(u, &len, 10000)) { Serial.println(F("Карта не найдена")); return; }
  if (len != 7) { Serial.println(F("Ожидался 7-байтовый UID")); return; }

  uint8_t block0[MF_BLOCK_SIZE];
  if (gValid[0]) {
    memcpy(block0, gDump[0], MF_BLOCK_SIZE);
  } else {
    buildBlock0(gUid, gUidLen, block0);   // UID + BCC + ATQA/SAK
  }

  uint16_t written = 0;
  for (uint16_t blk = 0; blk < MF_BLOCKS_1K; blk++) {
    uint8_t data[MF_BLOCK_SIZE];
    if (gValid[blk]) memcpy(data, gDump[blk], MF_BLOCK_SIZE);
    else if (blk == 0) memcpy(data, block0, MF_BLOCK_SIZE);
    else continue;                        // неизвестные блоки не трогаем

    bool authed = false;
    for (uint8_t ki = 0; ki < MF_KEYS_COUNT && !authed; ki++) {
      if (nfc.mifareclassic_AuthenticateBlock(u, len, blk, 0,
          const_cast<uint8_t *>(MF_KEYS[ki]))) authed = true;
    }
    if (!authed) { Serial.printf("Блок %u: нет ключа, пропущен\n", blk); continue; }
    if (nfc.mifareclassic_WriteDataBlock(blk, data)) {
      written++;
      if (blk == 0) Serial.println(F("Блок 0 (UID) записан"));
    } else {
      Serial.printf("Блок %u: ошибка записи\n", blk);
    }
  }
  Serial.printf("Записано блоков: %d\n", written);
  Serial.println(F("Проверьте копию режимом SCAN"));
}

void cmdEmulate() {
  if (gUidLen != 7) { Serial.println(F("Сначала SCAN")); return; }
  bool ok = nfc.tgInitAsTarget(MF_ATQA_0, MF_SAK, gUid, gUidLen, 1000);
  if (!ok) {
    Serial.println(F("Не удалось перевести PN532 в target-режим (проверьте версию библиотеки)"));
    return;
  }
  Serial.println(F("EMULATE: поднесите к считывателю. Кнопка или 'q' — выход."));
  digitalWrite(LED_PIN, HIGH);
  uint8_t buf[64]; uint8_t blen = 0;
  while (digitalRead(BTN_PIN) != LOW) {
    if (Serial.available()) {
      String c = Serial.readStringUntil('\n'); c.trim(); c.toUpperCase();
      if (c == "Q") break;
    }
    if (nfc.tgGetData(buf, &blen) && blen) {
      Serial.print(F("От считывателя: "));
      for (uint8_t i = 0; i < blen && i < sizeof(buf); i++) {
        if (buf[i] < 0x10) Serial.print('0');
        Serial.print(buf[i], HEX); Serial.print(' ');
      }
      Serial.println();
      // Полная эмуляция MIFARE Classic (Crypto1/секторы) здесь не реализована.
    }
    delay(10);
  }
  digitalWrite(LED_PIN, LOW);
  while (digitalRead(BTN_PIN) == LOW) delay(20);
  nfc.SAMConfig();
  Serial.println(F("EMULATE: выход"));
}

void help() {
  Serial.println(F("=== ESP32+PN532 дубликатор (только свой пропуск) ==="));
  Serial.println(F("S  SCAN   - прочитать UID (7 байт) и сохранить"));
  Serial.println(F("D  DUMP   - прочитать доступные секторы (штатные ключи)"));
  Serial.println(F("W  WRITE  - записать копию на ПУСТУЮ magic-карту (нужен YES)"));
  Serial.println(F("E  EMULATE- подставить UID как карту"));
  Serial.println(F("P  PRINT  - показать сохранённое состояние"));
  Serial.println(F("H  HELP   - эта справка"));
}

void setup() {
  Serial.begin(115200);
  pinMode(BTN_PIN, INPUT_PULLUP);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.println();
  if (!nfc.begin()) { Serial.println(F("PN532 не найден — проверьте SPI/питание")); while (1) delay(1000); }
  uint32_t v = nfc.getFirmwareVersion();
  if (!v) { Serial.println(F("Нет версии прошивки PN532")); while (1) delay(1000); }
  Serial.printf("PN532 firmware: 0x%08X\n", v);
  nfc.SAMConfig();
  loadState();
  help();
}

void loop() {
  if (Serial.available()) {
    String c = Serial.readStringUntil('\n'); c.trim(); c.toUpperCase();
    if (c == "S" || c == "SCAN") cmdScan();
    else if (c == "D" || c == "DUMP") cmdDump();
    else if (c == "W" || c == "WRITE") cmdWrite();
    else if (c == "E" || c == "EMULATE") cmdEmulate();
    else if (c == "P" || c == "PRINT") {
      Serial.print(F("Сохранённый UID: "));
      if (gUidLen) printUid(gUid, gUidLen); else Serial.println(F("нет"));
      uint16_t n = 0; for (auto b : gValid) if (b) n++;
      Serial.printf("Блоков в дампе: %d\n", n);
    }
    else if (c == "H" || c == "HELP") help();
    else Serial.println(F("Неизвестная команда. H — справка"));
  }
  delay(10);
}
