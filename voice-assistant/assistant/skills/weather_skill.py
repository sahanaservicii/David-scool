from __future__ import annotations
import json
import urllib.parse
import urllib.request
from .base import Skill
from ..nlu.intents import IntentResult, SkillResponse
from ..core.context import DialogContext


class WeatherSkill(Skill):
    name = "weather"
    description = "Погода (через открытые источники без ключа, если доступно)"
    intents = ["weather"]

    def handle(self, intent: IntentResult, ctx: DialogContext) -> SkillResponse:
        place = (intent.entities.get('place') or '').strip() or 'Moscow'
        if not self.cfg.get('search', {}).get('allow_online', True):
            return SkillResponse(text="Онлайн-доступ отключён в настройках, погоду получить нельзя.")
        # Try wttr.in (no key, public service) - best effort
        try:
            q = urllib.parse.quote(place)
            url = f"https://wttr.in/{q}?format=j1"
            req = urllib.request.Request(url, headers={'User-Agent': 'FreeVoice/0.1'})
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode('utf-8', errors='replace'))
            cur = (data.get('current_condition') or [{}])[0]
            desc = (cur.get('lang_ru') or cur.get('weatherDesc') or [{}])[0].get('value', '')
            temp = cur.get('temp_C', '?')
            feels = cur.get('FeelsLikeC', '?')
            hum = cur.get('humidity', '?')
            wind = cur.get('windspeedKmph', '?')
            area = (data.get('nearest_area') or [{}])[0]
            name = (area.get('areaName') or [{}])[0].get('value', place)
            country = (area.get('country') or [{}])[0].get('value', '')
            loc = f"{name}, {country}".strip(', ')
            text = (f"Погода: {loc}\n"
                    f"• {desc}\n• Температура: {temp}°C, ощущается как {feels}°C\n"
                    f"• Влажность: {hum}%\n• Ветер: {wind} км/ч")
            return SkillResponse(text=text, data={"place": loc, "current": cur})
        except Exception as e:
            return SkillResponse(text=(
                f"Не удалось получить погоду для «{place}». "
                "Нужен доступ в интернет к открытому сервису (wttr.in) или локальный провайдер. "
                "Проверьте сеть или укажите другой источник в конфигурации."), data={"error": str(e)})
