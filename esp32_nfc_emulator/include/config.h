#pragma once
#include <Arduino.h>

// --- Пины (soft SPI) ---
#define PN532_CLK  18
#define PN532_MISO 19
#define PN532_MOSI 23
#define PN532_CS   5
#define BTN_PIN    4
#define LED_PIN    2

// MIFARE Classic 1K: 16 секторов x 4 блока x 16 байт
#define MF_BLOCK_SIZE   16
#define MF_BLOCKS_1K    64
#define MF_SECTORS_1K   16

// Атрибуты карты (для блока 0 и target-режима)
#define MF_ATQA_0 0x44
#define MF_ATQA_1 0x00
#define MF_SAK    0x08

// Известные штатные ключи. Это НЕ подбор: используются только
// стандартные заводские значения. Если сектор защищён своим ключом —
// он будет пропущен, дамп будет неполным.
static const uint8_t MF_KEYS[][6] = {
  {0xFF,0xFF,0xFF,0xFF,0xFF,0xFF},
  {0xA0,0xA1,0xA2,0xA3,0xA4,0xA5},
  {0xB0,0xB1,0xB2,0xB3,0xB4,0xB5},
};
#define MF_KEYS_COUNT (sizeof(MF_KEYS) / sizeof(MF_KEYS[0]))
