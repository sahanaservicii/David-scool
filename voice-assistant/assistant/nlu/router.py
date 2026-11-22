from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from .intents import IntentResult


@dataclass
class Rule:
    intent: str
    skill: str
    patterns: List[re.Pattern]
    confidence: float = 0.9
    extractor: Optional[Callable[[str, re.Match], dict]] = None


def _c(patterns):
    return [re.compile(p, re.IGNORECASE | re.UNICODE) for p in patterns]


class IntentRouter:
    def __init__(self):
        self.rules: List[Rule] = []
        self._build()

    def add(self, intent: str, skill: str, patterns, confidence=0.9, extractor=None):
        self.rules.append(Rule(intent, skill, _c(patterns), confidence, extractor))

    def _build(self):
        add = self.add
        add('greeting', 'smalltalk', [r'\b(привет|здравствуй|доброе утро|добрый день|добрый вечер|хай|hello|hi)\b'])
        add('how_are_you', 'smalltalk', [r'как (дела|ты|настроение)', r'how are you'])
        add('who_are_you', 'smalltalk', [r'кто ты', r'как тебя зовут', r'who are you', r'what is your name'])
        add('thanks', 'smalltalk', [r'\b(спасибо|благодар|thanks|thank you)\b'])
        add('goodbye', 'smalltalk', [r'\b(пока|до свидан|выход|стоп разговор|bye|goodbye)\b'])
        add('help', 'help', [r'\b(помощь|что ты умеешь|команды|help|capabilities)\b', r'что можешь'])

        add('time_now', 'time', [r'\b(который час|сколько времени|время сейчас|текущее время|what time)\b'])
        add('date_today', 'time', [r'\b(какое сегодня число|какая сегодня дата|какой сегодня день|today\'?s date|what day)\b'])

        add('timer_set', 'timer', [
            r'\b(таймер|поставь таймер|засеки|напомни через|timer)\b',
            r'через\s+\d+',
        ], extractor=self._extract_timer)
        add('timer_list', 'timer', [r'(какие таймеры|список таймеров|мои таймеры|active timers)'])
        add('timer_cancel', 'timer', [r'(отмени таймер|удали таймер|cancel timer)'])

        add('note_add', 'notes', [r'\b(запиши|заметка|сохрани заметку|добавь заметку|note|remember that)\b'], extractor=self._extract_note)
        add('note_list', 'notes', [r'\b(мои заметки|список заметок|покажи заметки|list notes)\b'])
        add('note_find', 'notes', [r'\b(найди заметк|поиск заметк|find note)\b'], extractor=self._extract_note_query)

        add('calc', 'calc', [r'\b(посчитай|сколько будет|вычисли|калькулятор|calculate)\b', r'^[\d\s\+\-\*\/\(\)\.\,\^%]+$'])
        add('weather', 'weather', [r'\b(погод\w*|какой погод\w*|прогноз\w*|weather|forecast)\b'], extractor=self._extract_place)
        add('search', 'search', [r'\b(найди в интернете|поиск в интернете|загугли|поищи в интернете|search for|google)\b', r'^(найди|поищи)\s+'], extractor=self._extract_search)

        add('system_info', 'system', [r'\b(статус системы|состояние системы|диск|память|cpu|нагрузка|system status)\b'])

        # Home Assistant / smart home / multi-room media (priority before generic homelab)
        add('ha_status', 'ha', [r'\b(статус\s+(ha|home assistant|умн(ого|ый)\s+дом)|home assistant\s+статус|ha\s+status)\b'])
        add('media_control', 'ha', [
            r'\b(включи|выключи|запусти|поставь|играй|воспроизведи|останови|пауза|продолжи)\b.*\b(музык\w*|песн\w*|трек\w*|плейлист\w*|радио|альбом\w*|spotify|youtube music)\b',
            r'\b(музык\w*|песн\w*|трек\w*|плейлист\w*|радио)\b.*\b(в этой комнате|в комнате|здесь|тут)\b',
            r'\b(громче|тише|следующ\w*\s+трек|предыдущ\w*\s+трек|громкость)\b',
            r'\b(пауза|продолжи)\b.*\b(музык\w*|плеер\w*|колонк\w*|динамик\w*)\b',
        ])
        add('ha_query', 'ha', [
            r'\b(какая температура|температур\w*|влажност\w*|датчик\w*)\b',
            r'\b(что включено|какие устройства|статус устройств|состояние устройств)\b',
            r'\b(покажи|скажи|узнай)\b.*\b(температур\w*|влажност\w*|датчик\w*|состояние)\b',
        ])
        add('ha_control', 'ha', [
            r'\b(включи|выключи|вруби|отключи|зажги|погаси|переключи|открой|закрой)\b.*\b(свет\w*|ламп\w*|люстр\w*|розетк\w*|выключател\w*|штор\w*|жалюзи\w*|кондиционер\w*|климат\w*|сцен\w*|скрипт\w*|устройств\w*)\b',
            r'\b(свет\w*|ламп\w*|люстр\w*)\b.*\b(в этой комнате|в комнате|здесь|тут|в кухне|в спальне|в гостиной|в ванной|в коридоре)\b',
            r'\b(home assistant|умный дом)\b.*\b(включи|выключи|статус|состояние)\b',
        ])

        add('homelab', 'homelab', [r'\b(homelab|инвентар\w*|роутер|openwrt|приставк\w*|телевизор\w*|камер\w*|сеть|doctor)\b'])

        add('open_url', 'web', [r'\b(открой сайт|открой ссылку|open url|open website)\b'], extractor=self._extract_url)
        add('app_open', 'app_control', [r'\b(открой приложение|запусти приложение|open app|launch app)\b'], extractor=self._extract_app)

        # free-form chat intent hint (will be routed to fallback/LLM)
        add('chat', 'fallback', [r'^(расскажи|объясни|помоги|предложи|напиши|сгенерируй|сочини|придумай|как (мне|лучше)|что такое|почему|зачем|кто такой|переведи|сделай обзор|сравни)\b'], confidence=0.6)

    def route(self, text: str) -> IntentResult:
        t = (text or '').strip()
        for rule in self.rules:
            for pat in rule.patterns:
                m = pat.search(t)
                if m:
                    entities = {}
                    if rule.extractor:
                        try:
                            entities = rule.extractor(t, m) or {}
                        except Exception:
                            entities = {}
                    return IntentResult(intent=rule.intent, skill=rule.skill,
                                        confidence=rule.confidence, entities=entities, raw=t)
        # fallback: if question-like, treat as search/llm candidate
        if len(t) > 0:
            return IntentResult(intent='fallback', skill='fallback', confidence=0.3, entities={'text': t}, raw=t)
        return IntentResult(intent='empty', skill='smalltalk', confidence=0.0, entities={}, raw=t)

    @staticmethod
    def _extract_search(text, m):
        q = text[m.end():].strip(' :,-"\'' )
        if not q:
            # remove leading keyword
            q = re.sub(r'^(найди|поиск|загугли|поищи( в интернете)?|search for|google)\s*', '', text, flags=re.I).strip()
        return {'query': q}

    @staticmethod
    def _extract_note(text, m):
        body = re.sub(r'^(запиши|заметка|сохрани заметку|добавь заметку|note:?|remember that)\s*', '', text, flags=re.I).strip()
        return {'text': body}

    @staticmethod
    def _extract_note_query(text, m):
        q = re.sub(r'^(найди заметк[уи]?|поиск замет(ок|ки)|find note)\s*', '', text, flags=re.I).strip()
        return {'query': q}

    @staticmethod
    def _extract_timer(text, m):
        # simple extraction: seconds/minutes/hours
        total = 0
        for val, unit in re.findall(r'(\d+)\s*(час|ч|hour|h|минут|мин|minute|min|m|секунд|сек|second|sec|s)\w*', text, re.I):
            v = int(val)
            u = unit.lower()
            if u.startswith(('час', 'ч', 'h')): total += v * 3600
            elif u.startswith(('мин', 'm')): total += v * 60
            else: total += v
        if total == 0:
            nums = re.findall(r'\b(\d+)\b', text)
            if nums:
                total = int(nums[0]) * 60  # default minutes
        label_m = re.search(r'(?:на|под названием|label)\s+(.+)$', text, re.I)
        label = label_m.group(1).strip() if label_m else 'Таймер'
        return {'seconds': total, 'label': label}

    @staticmethod
    def _extract_place(text, m):
        q = re.sub(r'^.*?(погода|прогноз|weather|forecast)\s*(в|in)?\s*', '', text, flags=re.I).strip()
        return {'place': q}

    @staticmethod
    def _extract_url(text, m):
        url = re.search(r'https?://\S+|\b[\w.-]+\.[a-z]{2,}\S*', text, re.I)
        return {'url': url.group(0) if url else text[m.end():].strip()}

    @staticmethod
    def _extract_app(text, m):
        name = re.sub(r'^(открой приложение|запусти|open app|launch)\s*', '', text, flags=re.I).strip()
        return {'app': name}
